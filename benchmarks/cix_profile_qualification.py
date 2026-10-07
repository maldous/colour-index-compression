#!/usr/bin/env python3
"""Prepared-only local CIX automatic-profile development measurement.

Without ``--run`` this only prints its immutable six-cell plan.  An explicit
run compares CIX's normal public effort interface: ``--fast``, no effort flag
(DEFAULT), and ``--best``.  It intentionally supplies no route, backend,
format, block, history, memory, or thread override.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

SOURCE = Path("/home/user/src/colour-index-compression/benchmark-work/silesia/dickens")
SOURCE_BYTES = 10_192_446
SOURCE_SHA256 = "b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a"
RANGE_OFFSET, RANGE_LENGTH = 0, 1 << 20
RANGE_SHA256 = "afd479dd0e0339643530bf4ee3d10423265c515a06e7994bbe26ccba39aea9ab"
EXPECTED_COMMIT = "90e457277dcb80b1ff713413b07a8c904bb660df"
RESERVED_CPUS = [16, 17, 18, 19]
REPETITIONS, WALL_SECONDS = 2, 300
MEMORY_BYTES, TEMP_BYTES = 2 * 1024**3, 512 * 1024**2

PROFILES = (
    ("fast", ["--fast"], {"memory": "512MiB", "block_size": "32KiB", "threads": 4}),
    ("default", [], {"memory": "512MiB", "block_size": "32KiB", "threads": 4}),
    ("best", ["--best"], {"memory": "512MiB", "block_size": "64KiB", "threads": 4}),
)


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


def require_environment(cix: Path, uncix: Path) -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != EXPECTED_COMMIT:
        raise RuntimeError(f"profile manifests are frozen for commit {EXPECTED_COMMIT}")
    if SOURCE.stat().st_size != SOURCE_BYTES or sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("verified Dickens source identity changed")
    if sha256(SOURCE, RANGE_OFFSET, RANGE_LENGTH) != RANGE_SHA256:
        raise RuntimeError("declared Dickens development range hash changed")
    unavailable = set(RESERVED_CPUS) - os.sched_getaffinity(0)
    if unavailable:
        raise RuntimeError(f"required profile CPUs are unavailable: {sorted(unavailable)}")
    cores: set[tuple[int, int]] = set()
    for cpu in RESERVED_CPUS:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            core = (int((base / "physical_package_id").read_text()), int((base / "core_id").read_text()))
        except (OSError, ValueError):
            core = (0, cpu)
        if core in cores:
            raise RuntimeError("reserved CPUs include sibling logical cores")
        cores.add(core)
    for binary in (cix, uncix):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise RuntimeError(f"required release-lto binary is not executable: {binary}")
        try:
            binary.resolve().relative_to(ROOT)
        except ValueError as error:
            raise ValueError(f"declared binary must be inside integration root: {binary}") from error


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def build_paths(cix: Path, uncix: Path) -> list[str]:
    paths = [rel(cix), rel(uncix), "benchmarks/cix_profile_qualification.py", "benchmarks/hutter_bounded_runner.py",
             "benchmarks/hutter_experiment_scheduler.py", "rust/cix-native/Cargo.toml", "rust/cix-native/Cargo.lock"]
    paths.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "rust/cix-native/src").rglob("*.rs")))
    return paths


def gnu_time(path: Path) -> dict:
    row: dict[str, object] = {"path": str(path), "available": path.is_file()}
    if not path.is_file():
        return row
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("\tUser time (seconds):"):
            row["user_seconds"] = float(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tSystem time (seconds):"):
            row["system_seconds"] = float(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tMaximum resident set size (kbytes):"):
            row["max_rss_kib"] = int(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tElapsed (wall clock) time"):
            elapsed = line.split("):", 1)[1].strip()
            values = [float(value) for value in elapsed.split(":")]
            row["wall"] = elapsed
            row["wall_seconds"] = sum(value * 60 ** power for power, value in enumerate(reversed(values)))
    return row


def manifest(cix: Path, uncix: Path, profile: str, effort_flags: list[str], expected: dict, repetition: int) -> dict:
    flags = [*effort_flags, "--verbose"]
    return {
        "hypothesis": "CIX automatic effort policy chooses different bounded search behavior for FAST, DEFAULT, and BEST while preserving exact restoration without user-selected representations.",
        "matched_control": "Identical release-lto binaries, input range, CPU reservation, fresh processes, and output framing conditions. The only intended CLI selection is FAST, no flag DEFAULT, or BEST.",
        "input": {"path": str(SOURCE), "offset": RANGE_OFFSET, "length": RANGE_LENGTH, "sha256": RANGE_SHA256,
                  "full_asset_sha256": SOURCE_SHA256, "dataset": "existing verified Silesia Dickens", "development_only": True},
        "configuration": {"profile": profile, "effort_flags": effort_flags, "verbose": True, "repetition": repetition,
                          "automatic_dimensions": ["route", "backend", "format", "block", "history", "memory", "threads"],
                          "explicit_strategy_overrides": [], "expected_selector_defaults": expected,
                          "release_binary_identity": {"cix": sha256(cix), "uncix": sha256(uncix)}, "source_commit": EXPECTED_COMMIT},
        "initial_state": "fresh encoder and fresh archive-only decoder processes; host background and cache state are uncontrolled",
        "mechanism": "Normal public CIX effort policy with verbose selector diagnostics. No format, route, backend, block, history, memory, or thread option is passed; four CPUs are made available through affinity so the normal default worker policy is observed.",
        "budget": {"cpu": RESERVED_CPUS, "max_rss_bytes": MEMORY_BYTES, "max_temp_bytes": TEMP_BYTES, "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "stage": "method_development",
        "promotion_criteria": "Fresh decoder exact restoration plus retained complete archive bytes, GNU time wall/CPU/max-RSS, and selector stderr. This is not a ranking or qualification timing result; Canterbury/Calgary/Artificial gate remains before renewed full Silesia qualification.",
        "exposure": "Existing verified 1 MiB development range only; no acquisition, held-out corpus, or full Silesia claim.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(cix.resolve()), *flags,
                           "-o", "{workdir}/candidate.cix", "{source}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(uncix.resolve()),
                           "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": build_paths(cix, uncix),
        "resource_accounting": "Every cell leases physical CPUs 16,17,18,19 and is dispatched serially. WaveScheduler aggregate cap: four physical cores, 12 GB RAM, 4 GB temporary storage, no swap.",
    }


def prepare(area: Path, cix: Path, uncix: Path) -> list[dict]:
    require_environment(cix, uncix)
    if area.exists():
        raise RuntimeError(f"profile evidence area exists; preserve immutable records: {area}")
    manifests = area / "manifests"
    manifests.mkdir(parents=True)
    cells = []
    for profile, flags, expected in PROFILES:
        for repetition in range(1, REPETITIONS + 1):
            cell_id = f"cix-auto-{profile}-r{repetition}"
            path = manifests / f"{cell_id}.json"
            path.write_bytes(canonical(manifest(cix, uncix, profile, flags, expected, repetition)) + b"\n")
            frozen, manifest_sha = load_manifest(path)
            cells.append({"cell_id": cell_id, "owner": "/root", "manifest_path": str(path.relative_to(ROOT)),
                          "output_dir": str((area / "runs" / cell_id).relative_to(ROOT)), "cpu": RESERVED_CPUS,
                          "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_identity(frozen, ROOT),
                          "fresh_justification": "Predeclared paired fresh-process repetitions capture local variation without changing the automatic policy."})
    (area / "cells.json").write_text(json.dumps(cells, indent=2) + "\n")
    return cells


def selector_stderr(receipt: Path) -> dict:
    experiment_id = json.loads(receipt.read_text())["experiment_id"][:12]
    path = receipt.parent / f"cix-bounded-{experiment_id}-encode.stderr.log"
    return {"path": str(path), "available": path.is_file(), "sha256": sha256(path) if path.is_file() else None,
            "text": path.read_text(errors="replace") if path.is_file() else None}


def summarize(area: Path, scheduler_rows: list[dict]) -> list[dict]:
    summary = []
    required = {"wall_seconds", "user_seconds", "system_seconds", "max_rss_kib"}
    for dispatched in scheduler_rows:
        receipt_path = dispatched.get("runner_result", {}).get("receipt")
        if not receipt_path:
            summary.append({"cell_id": dispatched["cell_id"], "runner_status": dispatched.get("runner_status")})
            continue
        receipt = Path(receipt_path)
        work = receipt.parent / "work"
        encoded, decoded = gnu_time(work / "encode.gnu-time.txt"), gnu_time(work / "decode.gnu-time.txt")
        result = json.loads(receipt.read_text())
        summary.append({"cell_id": dispatched["cell_id"], "runner_status": dispatched.get("runner_status"),
                        "archive_bytes": result.get("archive_bytes"), "archive_sha256": result.get("archive_sha256"),
                        "verification": result.get("verification"), "encode_gnu_time": encoded, "decode_gnu_time": decoded,
                        "selector_stderr": selector_stderr(receipt),
                        "gnu_time_complete": required <= set(encoded) and required <= set(decoded)})
    (area / "profile-summary.json").write_bytes(canonical({"rows": summary}) + b"\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="create immutable manifests and run the serial local WaveScheduler plan")
    parser.add_argument("--cix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/cix")
    parser.add_argument("--uncix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/uncix")
    parser.add_argument("--area", type=Path, default=ROOT / "docs/research/2026-10-01-cix-optimization/cix-profile-qualification")
    args = parser.parse_args()
    plan = {"source": str(SOURCE), "range_sha256": RANGE_SHA256, "commit": EXPECTED_COMMIT, "reserved_cpus": RESERVED_CPUS,
            "cells": REPETITIONS * len(PROFILES), "profiles": [{"profile": name, "effort_flags": flags, "selector_defaults": expected} for name, flags, expected in PROFILES],
            "execution": "blocked until --run; no benchmark execution occurred"}
    if not args.run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    cells = prepare(args.area.resolve(), args.cix.resolve(), args.uncix.resolve())
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    rows = []
    for cell in cells:
        rows.extend(scheduler.run_wave([cell]))
    summary = summarize(args.area.resolve(), rows)
    print(json.dumps(rows, indent=2, sort_keys=True))
    if any(row.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for row in rows):
        raise RuntimeError("profile run stopped on a non-verified cell; do not retry its immutable identity")
    if any(not row.get("gnu_time_complete", False) or not row["selector_stderr"]["available"] for row in summary):
        raise RuntimeError("profile evidence lacks GNU time or selector stderr; do not claim measurements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
