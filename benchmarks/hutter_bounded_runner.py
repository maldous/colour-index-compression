#!/usr/bin/env python3
"""Run a small, immutable, lossless-compression experiment safely.

This deliberately knows nothing about a particular codec.  A manifest binds the
question, matched control, input range, build files, command, resources and
promotion rule before a process starts.  The runner then records the physical
artifacts and independently checks the restored range.  It is a screening
harness: it refuses full-enwik9 inputs unless explicitly changed in code.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

PROGRESS_SECONDS = 30.0
MAX_SCREENING_SECONDS = 300
REQUIRED = ("hypothesis", "matched_control", "input", "configuration", "mechanism",
            "budget", "promotion_criteria", "command", "artifacts", "build_paths")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path, offset: int = 0, length: int | None = None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        stream.seek(offset)
        remaining = length
        while remaining is None or remaining:
            block = stream.read(min(1024 * 1024, remaining) if remaining is not None else 1024 * 1024)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    return digest.hexdigest()


def tree_pids(root: int) -> set[int]:
    pending, found = [root], set()
    while pending:
        pid = pending.pop()
        if pid in found or not Path(f"/proc/{pid}").exists():
            continue
        found.add(pid)
        try:
            pending.extend(int(p) for p in Path(f"/proc/{pid}/task/{pid}/children").read_text().split())
        except (OSError, ValueError):
            pass
    return found


def tree_rss(root: int) -> int:
    total = 0
    for pid in tree_pids(root):
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, IndexError):
            pass
    return total


def directory_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def load_manifest(path: Path) -> tuple[dict, str]:
    manifest = json.loads(path.read_text())
    missing = [key for key in REQUIRED if key not in manifest]
    if missing:
        raise ValueError("manifest missing: " + ", ".join(missing))
    inp = manifest["input"]
    for key in ("path", "offset", "length", "sha256"):
        if key not in inp:
            raise ValueError("manifest input missing: " + key)
    budget = manifest["budget"]
    for key in ("wall_seconds", "max_rss_bytes", "max_temp_bytes", "cpu"):
        if key not in budget:
            raise ValueError("manifest budget missing: " + key)
    if not 0 < int(budget["wall_seconds"]) <= MAX_SCREENING_SECONDS:
        raise ValueError("screening wall_seconds must be 1..300")
    if int(inp["length"]) >= 1_000_000_000:
        raise ValueError("full enwik9 runs are forbidden by the screening runner")
    return manifest, hashlib.sha256(canonical(manifest)).hexdigest()


def build_identity(manifest: dict, root: Path) -> dict:
    identity = {}
    for name in manifest["build_paths"]:
        path = (root / name).resolve()
        if not path.is_file() or root.resolve() not in path.parents:
            raise ValueError(f"invalid build path: {name}")
        identity[name] = sha256(path)
    return identity


def input_identity(manifest: dict) -> dict:
    spec = manifest["input"]
    path = Path(spec["path"]).resolve()
    actual = sha256(path, int(spec["offset"]), int(spec["length"]))
    if actual != spec["sha256"]:
        raise ValueError("input range hash mismatch")
    return {"path": str(path), "offset": int(spec["offset"]), "length": int(spec["length"]), "sha256": actual}


def replace_tokens(command: list[str], values: dict[str, str]) -> list[str]:
    return [part.format(**values) for part in command]


def kill_tree(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass


def valid_receipt(receipt: Path, expected: dict) -> bool:
    try:
        row = json.loads(receipt.read_text())
        artifacts = row["artifacts"]
        archive, restored = Path(artifacts["archive"]), Path(artifacts["restored"])
        return (row["identity"] == expected and row["status"] == "VERIFIED_SCREENING"
                and row["verification"]["matched"] and archive.is_file() and restored.is_file()
                and archive.stat().st_size == row["archive_bytes"]
                and sha256(archive) == row["archive_sha256"]
                and sha256(restored) == row["verification"]["restored_sha256"])
    except (OSError, KeyError, json.JSONDecodeError):
        return False


def systemd_properties(unit: str) -> dict[str, str]:
    command = ["sudo", "-n", "systemctl", "show", unit, "--property=ActiveState", "--property=MainPID",
               "--property=MemoryCurrent", "--property=MemoryPeak", "--property=CPUUsageNSec",
               "--property=ControlGroup", "--property=Result", "--property=ExecMainStatus"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        return {}
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def stop_unit(unit: str) -> None:
    subprocess.run(["sudo", "-n", "systemctl", "stop", unit], capture_output=True, check=False)
    subprocess.run(["sudo", "-n", "systemctl", "kill", "--kill-who=all", unit], capture_output=True, check=False)


def unit_int(properties: dict[str, str], key: str) -> int:
    try:
        return int(properties.get(key, "0"))
    except ValueError:
        return 0


def run(manifest_path: Path, results: Path, root: Path) -> dict:
    manifest, manifest_sha = load_manifest(manifest_path)
    build = build_identity(manifest, root)
    source = input_identity(manifest)
    identity = {"manifest_sha256": manifest_sha, "build_sha256": build, "input": source,
                "configuration": manifest["configuration"], "initial_state": manifest.get("initial_state", "empty")}
    experiment_id = hashlib.sha256(canonical(identity)).hexdigest()
    destination = results / experiment_id
    receipt = destination / "receipt.json"
    if receipt.exists():
        if valid_receipt(receipt, identity):
            return {"status": "REUSED_VERIFIED", "experiment_id": experiment_id, "receipt": str(receipt)}
        raise ValueError("existing receipt is not a matching verified result; use a new manifest")
    if (destination / "cancelled.json").exists():
        raise ValueError("cancelled experiment is never resumed; use a new manifest")
    destination.mkdir(parents=True, exist_ok=False)
    work = destination / "work"
    work.mkdir()
    (destination / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    (destination / "identity.json").write_bytes(canonical(identity) + b"\n")
    snapshot = destination / "build"
    for name in manifest["build_paths"]:
        original = (root / name).resolve()
        copied = snapshot / name
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, copied)
    budget = manifest["budget"]
    cpu = int(budget["cpu"])
    if cpu not in os.sched_getaffinity(0):
        raise ValueError(f"requested CPU {cpu} is unavailable")
    # The non-blocking lease prevents two independently launched runner
    # processes from silently oversubscribing the same declared experiment CPU.
    lease = Path(f"/tmp/cix-bounded-cpu-{cpu}.lock").open("w")
    try:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        lease.close()
        raise RuntimeError(f"CPU {cpu} already leased by another bounded experiment") from error
    max_rss, max_temp, wall = (int(budget[k]) for k in ("max_rss_bytes", "max_temp_bytes", "wall_seconds"))
    values = {"workdir": str(work), "source": source["path"], "offset": str(source["offset"]),
              "length": str(source["length"]), "receipt": str(receipt)}
    command = replace_tokens(manifest["command"], values)
    # Directly invoked declared builds always run from their immutable copy.
    command = [str(snapshot / name) if part == str((root / name).resolve()) else part
               for part in command for name in [None]]
    archive = Path(replace_tokens([manifest["artifacts"]["archive"]], values)[0])
    restored = Path(replace_tokens([manifest["artifacts"]["restored"]], values)[0])
    progress = destination / "progress.jsonl"

    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
           "CIX_EXPERIMENT_MANIFEST": str(destination / "manifest.json"), "CIX_EXPERIMENT_RECEIPT": str(receipt)}
    # Do not fall back silently: this scope supplies process-tree MemoryMax,
    # MemorySwapMax=0 and cgroup kill semantics rather than a best-effort rlimit.
    unit = "cix-bounded-" + experiment_id[:16]
    launcher = ["sudo", "-n", "systemd-run", "--quiet", "--collect", "--unit=" + unit,
                "--property=MemoryMax=" + str(max_rss), "--property=MemorySwapMax=0",
                "--property=KillMode=control-group", "--property=AllowedCPUs=" + str(cpu),
                "--property=CPUAffinity=" + str(cpu), "--property=Environment=OMP_NUM_THREADS=1",
                "--property=Environment=OPENBLAS_NUM_THREADS=1", "--property=Environment=MKL_NUM_THREADS=1",
                "--property=WorkingDirectory=" + str(work),
                "--property=StandardOutput=file:" + str(destination / "stdout.log"),
                "--property=StandardError=file:" + str(destination / "stderr.log"), "--"] + command
    started = time.monotonic()
    launched = subprocess.run(launcher, cwd=work, env=env, capture_output=True, text=True, check=False)
    if launched.returncode:
        raise RuntimeError("systemd cgroup launch failed: " + launched.stderr.strip())
    peak_rss = peak_temp = 0
    reason = None
    next_progress = started
    exit_code = None
    while True:
        elapsed = time.monotonic() - started
        props = systemd_properties(unit)
        current_rss = unit_int(props, "MemoryCurrent")
        peak_rss = max(peak_rss, current_rss, unit_int(props, "MemoryPeak"))
        peak_temp = max(peak_temp, directory_bytes(work))
        if time.monotonic() >= next_progress:
            with progress.open("a") as log:
                log.write(json.dumps({"at": utcnow(), "phase": "running", "processed_bytes": None,
                                      "elapsed_seconds": elapsed, "rss_bytes": peak_rss,
                                      "temp_bytes": peak_temp, "cpu": cpu, "cgroup": unit}) + "\n")
            next_progress += PROGRESS_SECONDS
        if not props or props.get("ActiveState") in ("inactive", "failed"):
            exit_code = 0 if props.get("ActiveState") == "inactive" else 1
            break
        if elapsed >= wall:
            reason = "wall_budget_exhausted"; stop_unit(unit); exit_code = 1; break
        if peak_rss > max_rss:
            reason = "rss_budget_exhausted"; stop_unit(unit); exit_code = 1; break
        if peak_temp > max_temp:
            reason = "temp_budget_exhausted"; stop_unit(unit); exit_code = 1; break
        time.sleep(min(0.05, max(0.01, wall - elapsed)))
    elapsed = time.monotonic() - started
    peak_temp = max(peak_temp, directory_bytes(work))
    verification = {"matched": False, "source_sha256": source["sha256"], "restored_sha256": None}
    if reason is None and exit_code == 0 and archive.is_file() and restored.is_file():
        restored_hash = sha256(restored)
        verification = {"matched": restored_hash == source["sha256"] and restored.stat().st_size == source["length"],
                        "source_sha256": source["sha256"], "restored_sha256": restored_hash}
    status = "VERIFIED" if verification["matched"] else "FAILED"
    row = {"status": status, "experiment_id": experiment_id, "identity": identity, "hypothesis": manifest["hypothesis"],
           "matched_control": manifest["matched_control"], "mechanism": manifest["mechanism"],
           "promotion_criteria": manifest["promotion_criteria"], "command": command, "budget": budget,
           "resource_enforcement": "systemd cgroup MemoryMax + MemorySwapMax=0 + KillMode=control-group + CPU affinity; RSS/temp sampled",
           "cgroup_unit": unit, "exit_code": exit_code, "stop_reason": reason, "elapsed_seconds": elapsed,
           "peak_rss_bytes": peak_rss, "peak_temp_bytes": peak_temp,
           "archive_bytes": archive.stat().st_size if archive.is_file() else None,
           "archive_sha256": sha256(archive) if archive.is_file() else None, "verification": verification,
           "completed_at": utcnow()}
    if status == "VERIFIED":
        receipt.write_bytes(canonical(row) + b"\n")
        row["receipt"] = str(receipt)
    else:
        (destination / "failed.json").write_bytes(canonical(row) + b"\n")
    lease.close()
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.results, args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
