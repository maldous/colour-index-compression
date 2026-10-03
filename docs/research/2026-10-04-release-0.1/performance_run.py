#!/usr/bin/env python3
"""Execute one already-amended v0.1 performance cell under root's scheduler.

This runner is deliberately not a scheduler.  Root's ``schedule.py`` gives it
the WaveScheduler lease/cgroup.  It refuses the original v1 CPU/PGO plan so an
amendment must be frozen before any execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
STABLE_BIN = Path("/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin")
LLVM_PROFDATA = Path("/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/bin/llvm-profdata")
TIMING_CPUS = [8]
SCALING_CPUS = [8, 10, 12, 14]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical(value) + b"\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def source_ok(binding: dict) -> None:
    source = Path(binding["path"])
    for relative, expected in binding["files"].items():
        path = source / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"source export changed: {relative}")


def plan_hash(plan_path: Path) -> str:
    return digest(plan_path)


def expected_cpus(cell_id: str) -> list[int]:
    if cell_id.startswith("S-BLOCKS-") or cell_id.startswith("S-CANDIDATES-"):
        workers = int(cell_id.rsplit("-", 1)[1])
        return SCALING_CPUS[:workers]
    return TIMING_CPUS


def require_amended_plan(plan: dict, cell: dict) -> None:
    cpus = cell["resources"]["cpus"]
    if cpus != expected_cpus(cell["id"]):
        raise RuntimeError("plan must be amended to v2 CPU placement before execution")
    if cell["id"].startswith("G-"):
        b0 = next(item for item in plan["cells"] if item["id"] == "B0")
        baseline = b0["steps"][0]["environment"]
        for name in ("G-BUILD-GENERATE", "G-BUILD-USE"):
            candidate = next((item for item in plan["cells"] if item["id"] == name), None)
            if candidate is None:
                continue
            env = candidate["steps"][0]["environment"]
            for key in ("CARGO_PROFILE_RELEASE_OPT_LEVEL", "CARGO_PROFILE_RELEASE_LTO", "CARGO_PROFILE_RELEASE_CODEGEN_UNITS"):
                if env.get(key) != baseline.get(key):
                    raise RuntimeError("plan must amend PGO builds to the B0 fat-LTO configuration")


def stable_env(extra: dict[str, str]) -> dict[str, str]:
    if not STABLE_BIN.is_dir() or not LLVM_PROFDATA.is_file():
        raise RuntimeError("stable Rust toolchain or llvm-profdata path is unavailable")
    env = os.environ.copy()
    env["PATH"] = f"{STABLE_BIN}:{env.get('PATH', '/usr/bin:/bin')}"
    env["CARGO_NET_OFFLINE"] = "true"
    env.update(extra)
    return env


def materialize_dirs(argv: list[str], env: dict[str, str], root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index, value in enumerate(argv[:-1]):
        if value == "-o":
            Path(argv[index + 1]).parent.mkdir(parents=True, exist_ok=True)
    target = env.get("CARGO_TARGET_DIR")
    if target:
        Path(target).mkdir(parents=True, exist_ok=True)


def rewrite_outputs(argv: list[str], cell_root: Path, mapping: dict[str, str]) -> list[str]:
    rewritten = list(argv)
    for index, value in enumerate(rewritten[:-1]):
        if value == "-o":
            original = rewritten[index + 1]
            destination = cell_root / "artifacts" / Path(original).name
            mapping[original] = str(destination)
            rewritten[index + 1] = str(destination)
    return [mapping.get(value, value) for value in rewritten]


def offline_command(argv: list[str]) -> list[str]:
    value = list(argv)
    if value and Path(value[0]).name == "cargo" and "build" in value and "--offline" not in value:
        value.insert(value.index("build") + 1, "--offline")
    if value and value[0] == "llvm-profdata":
        value[0] = str(LLVM_PROFDATA)
    return value


def execute_step(step_value: dict, cell_root: Path, mapping: dict[str, str]) -> dict:
    argv = offline_command(rewrite_outputs(step_value["argv"], cell_root, mapping))
    env = stable_env(step_value.get("environment", {}))
    materialize_dirs(argv, env, cell_root)
    name = step_value["name"]
    stdout, stderr = cell_root / f"{name}.stdout.log", cell_root / f"{name}.stderr.log"
    started = now()
    completed = subprocess.run(argv, cwd=cell_root, env=env, text=True, capture_output=True, check=False)
    stdout.write_text(completed.stdout)
    stderr.write_text(completed.stderr)
    return {"name": name, "started_at": started, "finished_at": now(), "argv": argv,
            "environment": {key: env[key] for key in sorted(step_value.get("environment", {}))},
            "exit_code": completed.returncode, "stdout": str(stdout), "stderr": str(stderr),
            "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr)}


def cix_outputs(step_results: list[dict]) -> list[Path]:
    outputs = []
    for result in step_results:
        argv = result["argv"]
        for index, value in enumerate(argv[:-1]):
            if value == "-o" and any(Path(part).name == "cix" for part in argv[:index]):
                candidate = Path(argv[index + 1])
                if candidate.suffix == ".cix":
                    outputs.append(candidate)
    return outputs


def fresh_verify(archive: Path, source: dict, decoder: Path, cell_root: Path, name: str) -> dict:
    restored = cell_root / "verification" / f"{name}.restored"
    restored.parent.mkdir(parents=True, exist_ok=True)
    stdout, stderr = cell_root / "verification" / f"{name}.stdout.log", cell_root / "verification" / f"{name}.stderr.log"
    completed = subprocess.run([str(decoder), "-f", "-o", str(restored), str(archive)], cwd=cell_root,
                               env=stable_env({}), text=True, capture_output=True, check=False)
    stdout.write_text(completed.stdout)
    stderr.write_text(completed.stderr)
    status = "VERIFIED" if completed.returncode == 0 and restored.is_file() and digest(restored) == source["sha256"] else "DECODE_OR_HASH_FAILURE"
    return {"archive": str(archive), "archive_bytes": archive.stat().st_size if archive.is_file() else None,
            "archive_sha256": digest(archive) if archive.is_file() else None, "restored": str(restored),
            "restored_sha256": digest(restored) if restored.is_file() else None, "exit_code": completed.returncode,
            "status": status, "stdout": str(stdout), "stderr": str(stderr)}


def planned_decode_results(step_results: list[dict], source: dict) -> dict[str, dict]:
    """Use the declared fresh decoder once; only encode-only cells need a new decode."""
    values = {}
    for result in step_results:
        argv = result["argv"]
        if not any(Path(part).name == "uncix" for part in argv):
            continue
        archive = next((Path(part) for part in argv if part.endswith(".cix")), None)
        if archive is None:
            continue
        restored = None
        for index, value in enumerate(argv[:-1]):
            if value == "-o":
                restored = Path(argv[index + 1])
        values[str(archive)] = {"archive": str(archive), "archive_bytes": archive.stat().st_size if archive.is_file() else None,
                                "archive_sha256": digest(archive) if archive.is_file() else None, "restored": str(restored) if restored else None,
                                "restored_sha256": digest(restored) if restored and restored.is_file() else None,
                                "exit_code": result["exit_code"],
                                "status": "VERIFIED" if restored and restored.is_file() and digest(restored) == source["sha256"] else "DECODE_OR_HASH_FAILURE",
                                "stdout": result["stdout"], "stderr": result["stderr"]}
    return values


def selected_decoder(plan: dict, cell: dict) -> Path:
    artifact = Path(plan["artifact_root"])
    if cell["id"].startswith("B"):
        build = next(step_value for step_value in cell["steps"] if step_value["name"] == "build")
        return Path(build["environment"]["CARGO_TARGET_DIR"]) / "release" / "uncix"
    if cell["id"].startswith("G-"):
        return artifact / "builds" / ("G-use" if cell["id"] == "G-HELDOUT" else "G-generate") / "release" / "uncix"
    return artifact / "selected" / "uncix"


def baseline_compare(plan: dict, cell: dict, verifications: list[dict]) -> list[dict]:
    if cell["id"] == "B0" or not cell["id"].startswith("B"):
        return []
    baseline = Path(plan["artifact_root"]) / "evidence" / "B0" / "result.json"
    if not baseline.is_file():
        raise RuntimeError("B0 result is required before a nonbaseline build arm")
    expected = {Path(item["archive"]).name: item["archive_sha256"] for item in load_json(baseline)["verifications"]}
    comparisons = []
    for item in verifications:
        name = Path(item["archive"]).name
        comparisons.append({"archive": name, "baseline_sha256": expected.get(name), "candidate_sha256": item["archive_sha256"], "equal": expected.get(name) == item["archive_sha256"]})
    if not all(item["equal"] for item in comparisons):
        raise RuntimeError("build arm changed a complete archive relative to B0")
    return comparisons


def copy_selected(plan: dict, cell: dict) -> dict | None:
    if cell["id"] != "B0":
        return None
    build = next(step_value for step_value in cell["steps"] if step_value["name"] == "build")
    origin = Path(build["environment"]["CARGO_TARGET_DIR"]) / "release"
    selected = Path(plan["artifact_root"]) / "selected"
    selected.mkdir(parents=True, exist_ok=True)
    result = {}
    for name in ("cix", "uncix", "cixcat"):
        source, destination = origin / name, selected / name
        if not source.is_file():
            raise RuntimeError(f"B0 did not produce {name}")
        shutil.copy2(source, destination)
        result[name] = {"path": str(destination), "sha256": digest(destination)}
    return result


def execute(plan_path: Path, cell_id: str, output: Path) -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("execution requires root schedule.py and CIX_RELEASE_LEASE=1")
    plan = load_json(plan_path)
    cell = next((item for item in plan["cells"] if item["id"] == cell_id), None)
    if cell is None:
        raise RuntimeError("unknown cell")
    source_ok(plan["source_export"])
    require_amended_plan(plan, cell)
    if output.exists():
        raise RuntimeError("immutable cell output already exists")
    output.mkdir(parents=True)
    manifest = {"schema": "cix-v0.1-performance-cell-v1", "created_at": now(), "plan": str(plan_path),
                "plan_sha256": plan_hash(plan_path), "cell": cell, "source_export": plan["source_export"],
                "stable_bin": str(STABLE_BIN), "llvm_profdata": str(LLVM_PROFDATA)}
    write_json(output / "manifest.json", manifest)
    if cell_id == "A1":
        write_json(output / "result.json", {"status": "BLOCKED_AWAITING_PRIVATE_AUX_MANIFEST", "manifest": str(output / "manifest.json")})
        return
    mapping: dict[str, str] = {}
    results = []
    for item in cell["steps"]:
        result = execute_step(item, output, mapping)
        results.append(result)
        if result["exit_code"] != 0:
            write_json(output / "result.json", {"status": "STEP_FAILURE", "steps": results, "manifest": str(output / "manifest.json")})
            raise RuntimeError(f"step failed: {item['name']}")
    copied = copy_selected(plan, cell)
    decoder = selected_decoder(plan, cell)
    verifications = []
    if cell["inputs"]:
        source = cell["inputs"][0]
        planned = planned_decode_results(results, source)
        for index, archive in enumerate(cix_outputs(results)):
            if str(archive) in planned:
                verifications.append(planned[str(archive)])
            else:
                verifications.append(fresh_verify(archive, source, decoder, output, f"archive-{index}"))
        if not all(item["status"] == "VERIFIED" for item in verifications):
            write_json(output / "result.json", {"status": "DECODE_OR_HASH_FAILURE", "steps": results, "verifications": verifications})
            raise RuntimeError("fresh archive verification failed")
    comparisons = baseline_compare(plan, cell, verifications)
    write_json(output / "result.json", {"status": "VERIFIED", "steps": results, "verifications": verifications,
                                          "baseline_comparisons": comparisons, "selected_copy": copied,
                                          "manifest": str(output / "manifest.json")})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        raise SystemExit("refusing execution without --run")
    execute(args.plan.resolve(), args.cell, args.output.resolve())


if __name__ == "__main__":
    main()
