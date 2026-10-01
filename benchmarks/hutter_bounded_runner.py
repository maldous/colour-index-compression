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
MAX_MODERATE_CONTIGUOUS_SECONDS = 1200
MAX_MODERATE_CONTIGUOUS_INPUT_BYTES = 16 * 1024 * 1024
REQUIRED = ("hypothesis", "matched_control", "input", "configuration", "mechanism",
            "budget", "promotion_criteria", "encode_command", "decode_command", "artifacts", "build_paths")


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
    for key in ("offset", "length", "sha256"):
        if key not in inp:
            raise ValueError("manifest input missing: " + key)
    budget = manifest["budget"]
    for key in ("wall_seconds", "max_rss_bytes", "max_temp_bytes", "cpu"):
        if key not in budget:
            raise ValueError("manifest budget missing: " + key)
    wall_seconds = int(budget["wall_seconds"])
    if not 0 < wall_seconds <= MAX_SCREENING_SECONDS:
        if not (MAX_SCREENING_SECONDS < wall_seconds <= MAX_MODERATE_CONTIGUOUS_SECONDS
                and manifest.get("stage") == "moderate_contiguous"
                and isinstance(manifest.get("longer_budget_justification"), str)
                and manifest["longer_budget_justification"].strip()
                and int(inp["length"]) <= MAX_MODERATE_CONTIGUOUS_INPUT_BYTES):
            raise ValueError("screening wall_seconds must be 1..300; 301..1200 requires moderate_contiguous stage, justification, and input <=16MiB")
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
    if int(spec["offset"]) < 0 or int(spec["length"]) <= 0:
        raise ValueError("input offset must be nonnegative and length positive")
    if int(spec["offset"]) + int(spec["length"]) > path.stat().st_size:
        raise ValueError("input range exceeds source file")
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


def validate_decode_size_gate(manifest: dict, source: dict) -> dict | None:
    """Validate a completed matched control before any candidate encode starts."""
    gate = manifest.get("decode_size_gate")
    if gate is None:
        return None
    required = ("control_receipt", "archive_sha256", "control_bytes", "matching_configuration_keys")
    if not isinstance(gate, dict) or any(key not in gate for key in required):
        raise ValueError("decode_size_gate missing required fields")
    receipt_path = Path(gate["control_receipt"])
    if not receipt_path.is_absolute() or not receipt_path.is_file():
        raise ValueError("decode_size_gate control_receipt must be an existing absolute path")
    try:
        control = json.loads(receipt_path.read_text())
        identity, verification, artifacts = control["identity"], control["verification"], control["artifacts"]
        control_input, control_configuration = identity["input"], identity["configuration"]
    except (KeyError, json.JSONDecodeError) as error:
        raise ValueError("decode_size_gate invalid control receipt") from error
    if control.get("status") != "VERIFIED_SCREENING" or not verification.get("matched"):
        raise ValueError("decode_size_gate control receipt is not verified")
    for key in ("path", "offset", "length", "sha256"):
        if control_input.get(key) != source.get(key):
            raise ValueError("decode_size_gate control input mismatch")
    keys = gate["matching_configuration_keys"]
    if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
        raise ValueError("decode_size_gate matching_configuration_keys must be a string list")
    candidate_configuration = manifest["configuration"]
    for key in keys:
        if control_configuration.get(key) != candidate_configuration.get(key):
            raise ValueError(f"decode_size_gate configuration mismatch: {key}")
    archive, restored = Path(artifacts["archive"]), Path(artifacts["restored"])
    if not archive.is_file() or not restored.is_file():
        raise ValueError("decode_size_gate control artifacts missing")
    archive_sha = sha256(archive)
    if (archive.stat().st_size != gate["control_bytes"] or archive.stat().st_size != control.get("archive_bytes")
            or archive_sha != gate["archive_sha256"] or archive_sha != control.get("archive_sha256")):
        raise ValueError("decode_size_gate control archive mismatch")
    restored_sha = sha256(restored)
    if restored_sha != source["sha256"] or restored_sha != verification.get("restored_sha256"):
        raise ValueError("decode_size_gate control restored hash mismatch")
    return {"control_receipt": str(receipt_path), "control_archive_bytes": archive.stat().st_size,
            "control_archive_sha256": archive_sha, "matching_configuration_keys": keys,
            "preflight_verified": True}


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


def execute_phase(*, unit: str, command: list[str], work: Path, destination: Path, budget: dict,
                  cpu: int | list[int], inaccessible: list[Path], input_bytes: int) -> dict:
    """Execute one phase in a transient cgroup and retain only measured facts."""
    wall, max_memory, max_temp = (int(budget[k]) for k in ("wall_seconds", "max_rss_bytes", "max_temp_bytes"))
    cpu_list = cpu if isinstance(cpu, list) else [cpu]
    cpu_set = ",".join(map(str, cpu_list))
    properties = ["--property=MemoryMax=" + str(max_memory), "--property=MemorySwapMax=0",
                  "--property=KillMode=control-group", "--property=AllowedCPUs=" + cpu_set,
                  "--property=CPUAffinity=" + cpu_set, "--property=User=user", "--property=Group=user",
                  "--property=NoNewPrivileges=yes", "--property=PrivateNetwork=yes", "--property=RemainAfterExit=yes",
                  "--property=Environment=OMP_NUM_THREADS=1", "--property=Environment=OPENBLAS_NUM_THREADS=1",
                  "--property=Environment=MKL_NUM_THREADS=1",
                  "--property=RuntimeMaxSec=" + str(wall), "--property=WorkingDirectory=" + str(work),
                  "--property=StandardOutput=file:" + str(destination / (unit + ".stdout.log")),
                  "--property=StandardError=file:" + str(destination / (unit + ".stderr.log"))]
    properties.extend("--property=InaccessiblePaths=" + str(path) for path in inaccessible)
    launcher = ["sudo", "-n", "systemd-run", "--quiet", "--collect", "--unit=" + unit] + properties + ["--"] + command
    started, peak_memory, peak_temp, cpu_usage, reason, exit_code = time.monotonic(), 0, 0, 0, None, None
    launched = subprocess.run(launcher, cwd=work, capture_output=True, text=True, check=False)
    if launched.returncode:
        raise RuntimeError("systemd cgroup launch failed: " + launched.stderr.strip())
    progress = destination / "progress.jsonl"; next_progress = started
    try:
        while True:
            elapsed, props = time.monotonic() - started, systemd_properties(unit)
            peak_memory = max(peak_memory, unit_int(props, "MemoryCurrent"), unit_int(props, "MemoryPeak"))
            peak_temp = max(peak_temp, directory_bytes(work)); cpu_usage = max(cpu_usage, unit_int(props, "CPUUsageNSec"))
            if time.monotonic() >= next_progress:
                with progress.open("a") as log:
                    log.write(json.dumps({"at": utcnow(), "phase": unit, "processed_bytes": None,
                        "elapsed_seconds": elapsed, "cgroup_memory_bytes": peak_memory,
                        "temp_bytes": peak_temp, "cpu": cpu}) + "\n")
                next_progress += PROGRESS_SECONDS
            if not props or props.get("ActiveState") in ("inactive", "failed") or (props.get("ActiveState") == "active" and props.get("MainPID") == "0"):
                exit_code = unit_int(props, "ExecMainStatus") if props else 1
                if props.get("Result", "success") != "success": exit_code = exit_code or 1
                if props.get("Result") == "timeout": reason = "wall_budget_exhausted"
                # RuntimeMaxSec is the same declared wall budget; if systemd
                # has already ended the unit at that exact boundary, preserve
                # the supervisor cause without guessing from an early failure.
                if reason is None and exit_code and elapsed >= wall: reason = "wall_budget_exhausted"
                break
            if elapsed >= wall or peak_temp > max_temp or peak_memory > max_memory:
                reason = "wall_budget_exhausted" if elapsed >= wall else ("temp_budget_exhausted" if peak_temp > max_temp else "memory_budget_exhausted")
                stop_unit(unit); exit_code = 1; break
            time.sleep(0.05)
    finally:
        stop_unit(unit)
    elapsed = time.monotonic() - started
    # A transient unit can report success after RuntimeMaxSec killed its control
    # group, so retain the declared wall boundary as the authoritative outcome.
    if reason is None and elapsed >= wall:
        reason = "wall_budget_exhausted"
    completed = exit_code == 0 and reason is None
    processed = input_bytes if completed else None
    with progress.open("a") as log:
        log.write(json.dumps({"at": utcnow(), "phase": unit, "processed_bytes": processed,
            "elapsed_seconds": elapsed, "throughput_bytes_per_second": processed / elapsed if processed and elapsed else None,
            "cgroup_memory_high_water_bytes": peak_memory, "temp_bytes": peak_temp, "cpu": cpu,
            "cpu_usage_seconds": cpu_usage / 1_000_000_000,
            "cpu_utilization": (cpu_usage / 1_000_000_000) / elapsed if elapsed else None,
            "completed": completed, "phase_ended": True}) + "\n")
    return {"phase": unit, "command": command, "exit_code": exit_code, "stop_reason": reason,
            "elapsed_seconds": elapsed, "sampled_cgroup_memory_high_water_bytes": peak_memory,
            "memory_measurement_note": "sampled cgroup high-water lower bound; true process peak unavailable",
            "peak_temp_bytes": peak_temp, "cpu_usage_seconds": cpu_usage / 1_000_000_000}


def run(manifest_path: Path, results: Path, root: Path) -> dict:
    manifest_path, results, root = manifest_path.resolve(), results.resolve(), root.resolve()
    manifest, manifest_sha = load_manifest(manifest_path)
    build = build_identity(manifest, root)
    source = input_identity(manifest)
    size_gate = validate_decode_size_gate(manifest, source)
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
    if (destination / "size-rejected.json").exists():
        raise ValueError("size-rejected experiment is never reused or promoted; use a new manifest")
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
        if sha256(copied) != build[name]:
            raise RuntimeError("immutable build snapshot hash mismatch")
        # Freeze snapshots while preserving the executable bit for declared
        # native binaries; read-only non-executables stay non-executable.
        copied.chmod(0o555 if original.stat().st_mode & 0o111 else 0o444)
    budget = manifest["budget"]
    cpu = budget["cpu"] if isinstance(budget["cpu"], list) else [budget["cpu"]]
    cpu = [int(item) for item in cpu]
    unavailable = set(cpu) - os.sched_getaffinity(0)
    if not cpu or len(set(cpu)) != len(cpu) or unavailable:
        raise ValueError(f"requested CPU set is invalid or unavailable: {cpu}")
    # The non-blocking lease prevents two independently launched runner
    # processes from silently oversubscribing the same declared experiment CPU.
    leases = []
    try:
        for item in cpu:
            lease = Path(f"/tmp/cix-bounded-cpu-{item}.lock").open("w")
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lease.close()
                raise
            leases.append(lease)
    except BlockingIOError as error:
        for lease in leases: lease.close()
        raise RuntimeError(f"one of CPUs {cpu} is already leased by another bounded experiment") from error
    # A stable decoder-reproducible filename avoids a representation-specific
    # source-name signal; all candidates receive the same `source.bin` path.
    materialized = work / "source.bin"
    with Path(source["path"]).open("rb") as incoming, materialized.open("wb") as outgoing:
        incoming.seek(source["offset"]); copied_bytes = outgoing.write(incoming.read(source["length"]))
    if copied_bytes != source["length"] or sha256(materialized) != source["sha256"]:
        raise RuntimeError("materialized input range mismatch")
    values = {"workdir": str(work), "source": str(materialized), "offset": "0",
              "length": str(source["length"]), "receipt": str(receipt)}
    encode_command = replace_tokens(manifest["encode_command"], values)
    decode_command = replace_tokens(manifest["decode_command"], values)
    # Directly invoked declared builds always run from their immutable copy.
    replacements = {str((root / name).resolve()): str(snapshot / name) for name in manifest["build_paths"]}
    encode_command = [replacements.get(part, part) for part in encode_command]
    decode_command = [replacements.get(part, part) for part in decode_command]
    archive = Path(replace_tokens([manifest["artifacts"]["archive"]], values)[0])
    restored = Path(replace_tokens([manifest["artifacts"]["restored"]], values)[0])
    units = ["cix-bounded-" + experiment_id[:12] + "-encode", "cix-bounded-" + experiment_id[:12] + "-decode"]
    old_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda _signum, _frame: (_ for _ in ()).throw(KeyboardInterrupt()))
    started = time.monotonic()
    try:
        encoded = execute_phase(unit=units[0], command=encode_command, work=work, destination=destination,
                                budget=budget, cpu=cpu, inaccessible=[], input_bytes=source["length"])
        remaining = int(budget["wall_seconds"] - (time.monotonic() - started))
        decode_budget = {**budget, "wall_seconds": max(1, remaining)}
        candidate_archive_bytes = archive.stat().st_size if archive.is_file() else None
        candidate_archive_sha256 = sha256(archive) if archive.is_file() else None
        size_rejected = bool(size_gate and encoded["exit_code"] == 0 and archive.is_file()
                             and candidate_archive_bytes >= size_gate["control_archive_bytes"])
        decoded = execute_phase(unit=units[1], command=decode_command, work=work, destination=destination,
                                budget=decode_budget, cpu=cpu, inaccessible=[Path(source["path"]), materialized], input_bytes=source["length"]) if encoded["exit_code"] == 0 and remaining > 0 and not size_rejected else None
    except BaseException:
        for unit in units: stop_unit(unit)
        (destination / "cancelled.json").write_text(json.dumps({"status": "CANCELLED", "at": utcnow()}) + "\n")
        raise
    finally:
        signal.signal(signal.SIGTERM, old_sigterm)
        for lease in leases: lease.close()
    verification = {"matched": False, "source_sha256": source["sha256"], "restored_sha256": None}
    if encoded["exit_code"] == 0 and decoded and decoded["exit_code"] == 0 and archive.is_file() and restored.is_file():
        restored_hash = sha256(restored)
        verification = {"matched": restored_hash == source["sha256"] and restored.stat().st_size == source["length"],
                        "source_sha256": source["sha256"], "restored_sha256": restored_hash}
    status = "VERIFIED_SCREENING" if verification["matched"] else ("SIZE_REJECTED_UNVERIFIED" if size_rejected else "FAILED")
    row = {"status": status, "experiment_id": experiment_id, "identity": identity, "hypothesis": manifest["hypothesis"],
           "matched_control": manifest["matched_control"], "mechanism": manifest["mechanism"],
           "promotion_criteria": manifest["promotion_criteria"], "phases": [encoded, decoded], "budget": budget,
           "resource_enforcement": "systemd cgroup MemoryMax + MemorySwapMax=0 + KillMode=control-group + CPU affinity",
           "cgroup_memory_note": "sampled cgroup high-water is a lower bound, not true process peak RSS",
           "archive_bytes": archive.stat().st_size if archive.is_file() else None,
           "archive_sha256": sha256(archive) if archive.is_file() else None, "verification": verification,
           "artifacts": {"archive": str(archive), "restored": str(restored)},
           "independent_decode": "separate decode command received archive only; source and materialized range inaccessible",
           "completed_at": utcnow()}
    if size_gate:
        row["decode_size_gate"] = {**size_gate, "candidate_archive_bytes": candidate_archive_bytes,
                                    "candidate_archive_sha256": candidate_archive_sha256,
                                    "comparison": "candidate >= completed verified control; decode skipped only after completed archive"}
    if status == "VERIFIED_SCREENING":
        receipt.write_bytes(canonical(row) + b"\n")
        row["receipt"] = str(receipt)
    elif status == "SIZE_REJECTED_UNVERIFIED":
        (destination / "size-rejected.json").write_bytes(canonical(row) + b"\n")
    else:
        (destination / "failed.json").write_bytes(canonical(row) + b"\n")
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    row = run(args.manifest, args.results, args.root)
    print(json.dumps(row, sort_keys=True))
    return 0 if row["status"] in ("VERIFIED_SCREENING", "REUSED_VERIFIED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
