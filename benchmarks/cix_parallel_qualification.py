#!/usr/bin/env python3
"""Prepared, opt-in qualification of CIX candidate versus block parallelism.

This runner is deliberately inert without ``--run``.  When explicitly run it
creates eight immutable WaveScheduler cells: two fresh repetitions of each
``threads={1,4} x parallelism={candidates,blocks}`` combination.  Every cell
uses the same frozen 1 MiB development range from the already verified Silesia
Dickens member and the same two release binaries.
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
RANGE_OFFSET = 0
RANGE_LENGTH = 1 << 20
RANGE_SHA256 = "afd479dd0e0339643530bf4ee3d10423265c515a06e7994bbe26ccba39aea9ab"
WALL_SECONDS = 300
MEMORY_BYTES = 2 * 1024**3
TEMP_BYTES = 512 * 1024**2
REPETITIONS = 2
RESERVED_CPUS = [16, 17, 18, 19]


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


def reserved_physical_cpus() -> list[int]:
    unavailable = set(RESERVED_CPUS) - os.sched_getaffinity(0)
    if unavailable:
        raise RuntimeError(f"required qualification CPUs are unavailable: {sorted(unavailable)}")
    cores: set[tuple[int, int]] = set()
    for cpu in RESERVED_CPUS:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            key = (int((base / "physical_package_id").read_text()), int((base / "core_id").read_text()))
        except (OSError, ValueError):
            key = (0, cpu)
        if key in cores:
            raise RuntimeError("qualification CPU reservation includes sibling logical CPUs")
        cores.add(key)
    return list(RESERVED_CPUS)


def relative_build_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError as error:
        raise ValueError(f"declared binary must be inside integration root: {resolved}") from error


def require_inputs(cix: Path, uncix: Path) -> None:
    if SOURCE.stat().st_size != SOURCE_BYTES or sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("verified Dickens source identity changed")
    if sha256(SOURCE, RANGE_OFFSET, RANGE_LENGTH) != RANGE_SHA256:
        raise RuntimeError("declared Dickens development range hash changed")
    for binary in (cix, uncix):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise RuntimeError(f"required release binary is not executable: {binary}")
        relative_build_path(binary)


def gnu_time_metrics(path: Path) -> dict:
    values: dict[str, object] = {"time_file": str(path), "available": path.is_file()}
    if not path.is_file():
        return values
    text = path.read_text(errors="replace")
    for line in text.splitlines():
        if line.startswith("\tUser time (seconds):"):
            values["user_seconds"] = float(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tSystem time (seconds):"):
            values["system_seconds"] = float(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tMaximum resident set size (kbytes):"):
            values["max_rss_kib"] = int(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tElapsed (wall clock) time"):
            elapsed = line.split("):", 1)[1].strip()
            values["wall"] = elapsed
            parts = [float(part) for part in elapsed.split(":")]
            values["wall_seconds"] = sum(value * 60 ** power for power, value in enumerate(reversed(parts)))
    return values


def build_paths(cix: Path, uncix: Path) -> list[str]:
    paths = [
        relative_build_path(cix), relative_build_path(uncix),
        "benchmarks/cix_parallel_qualification.py",
        "benchmarks/hutter_bounded_runner.py",
        "benchmarks/hutter_experiment_scheduler.py",
        "rust/cix-native/Cargo.toml", "rust/cix-native/Cargo.lock",
    ]
    paths.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "rust/cix-native/src").rglob("*.rs")))
    return paths


def exact_flags(threads: int, parallelism: str) -> list[str]:
    return [
        "--best", "--route", "ppm", "--format", "cixg2", "--block-size", "64KiB",
        "--memory", "2GiB", "--threads", str(threads), "--parallelism", parallelism, "--verbose",
    ]


def manifest_for(cix: Path, uncix: Path, cpus: list[int], threads: int, parallelism: str, repetition: int) -> dict:
    flags = exact_flags(threads, parallelism)
    # Every cell leases the same four physical cores. This prevents other scheduled CIX trials
    # from sharing its leased cores even when the tested mode uses one thread.
    # Other Codex sessions and OS background load remain uncontrolled. Cells are dispatched in serial waves.
    leased = cpus
    return {
        "hypothesis": "On the declared native PPM CIXG2 configuration, candidate and block parallelism can improve encode throughput without changing the complete archive or exact restoration.",
        "matched_control": "All cells use identical release binaries, source range, final-format flags, block size, memory limit, PPM route, and fresh decoder process; only --threads and --parallelism vary.",
        "input": {"path": str(SOURCE), "offset": RANGE_OFFSET, "length": RANGE_LENGTH, "sha256": RANGE_SHA256,
                  "full_asset_sha256": SOURCE_SHA256, "dataset": "existing verified Silesia Dickens", "development_only": True},
        "configuration": {"codec": "native-rust-cix", "effort": "best", "route": "ppm", "format": "cixg2",
                          "block_size": "64KiB", "memory": "2GiB", "threads": threads, "parallelism": parallelism,
                          "repetition": repetition, "flags": flags, "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "toolchain": subprocess.check_output(["rustc", "--version"], text=True).strip(), "hardware": subprocess.check_output(["lscpu"], text=True), "release_binary_identity": {"cix": sha256(cix), "uncix": sha256(uncix)}},
        "initial_state": "fresh encoder and fresh archive-only decoder processes; no warmed model, input cache state uncontrolled",
        "mechanism": "Bounded native CIX PPM candidate selection under explicit CIXG2 framing. Complete archive bytes, GNU time wall/CPU/max-RSS files, and independent decode are retained for each cell.",
        "budget": {"cpu": leased, "max_rss_bytes": MEMORY_BYTES, "max_temp_bytes": TEMP_BYTES, "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "stage": "method_development",
        "promotion_criteria": "Each fresh decoder must restore the declared range exactly. Compare only matched local GNU time measurements and complete archive bytes across the two repetitions; this does not rank Silesia or constitute qualification timing.",
        "exposure": "Existing verified 1 MiB development range only; no acquisition, no held-out or full-corpus claim. Canterbury/Calgary/Artificial gate remains required before renewed full Silesia qualification.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(cix.resolve()), *flags, "-o", "{workdir}/candidate.cix", "{source}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(uncix.resolve()), "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": build_paths(cix, uncix),
        "resource_accounting": "WaveScheduler aggregate cap is four physical cores, 12 GB RAM, 4 GB temporary storage, no swap. Every cell leases CPUs 16,17,18,19 and all CIX cells are dispatched serially; unrelated host background load is uncontrolled.",
    }


def prepare(area: Path, cix: Path, uncix: Path) -> list[dict]:
    require_inputs(cix, uncix)
    if area.exists():
        raise RuntimeError(f"qualification area already exists; preserve immutable evidence: {area}")
    cpus = reserved_physical_cpus()
    manifests = area / "manifests"
    manifests.mkdir(parents=True)
    cells = []
    for threads in (1, 4):
        for parallelism in ("candidates", "blocks"):
            for repetition in range(1, REPETITIONS + 1):
                cell_id = f"cix-parallel-ppm-t{threads}-{parallelism}-r{repetition}"
                manifest = manifest_for(cix, uncix, cpus, threads, parallelism, repetition)
                path = manifests / f"{cell_id}.json"
                path.write_bytes(canonical(manifest) + b"\n")
                frozen, manifest_sha = load_manifest(path)
                cells.append({"cell_id": cell_id, "owner": "/root", "manifest_path": str(path.relative_to(ROOT)),
                              "output_dir": str((area / "runs" / cell_id).relative_to(ROOT)), "cpu": frozen["budget"]["cpu"],
                              "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_identity(frozen, ROOT),
                              "fresh_justification": "Two predeclared fresh-process repetitions are required for local timing variability."})
    (area / "cells.json").write_text(json.dumps(cells, indent=2) + "\n")
    return cells


def summarize(area: Path, scheduler_rows: list[dict]) -> list[dict]:
    rows = []
    for row in scheduler_rows:
        receipt = row.get("runner_result", {}).get("receipt")
        if not receipt:
            rows.append({"cell_id": row["cell_id"], "runner_status": row.get("runner_status")})
            continue
        work = Path(receipt).parent / "work"
        record = json.loads(Path(receipt).read_text())
        encode_metrics, decode_metrics = gnu_time_metrics(work / "encode.gnu-time.txt"), gnu_time_metrics(work / "decode.gnu-time.txt")
        required = {"wall_seconds", "user_seconds", "system_seconds", "max_rss_kib"}
        missing = {"encode": sorted(required - set(encode_metrics)), "decode": sorted(required - set(decode_metrics))}
        rows.append({"cell_id": row["cell_id"], "runner_status": row.get("runner_status"),
                     "archive_bytes": record.get("archive_bytes"), "archive_sha256": record.get("archive_sha256"),
                     "verification": record.get("verification"), "encode_gnu_time": gnu_time_metrics(work / "encode.gnu-time.txt"),
                     "decode_gnu_time": decode_metrics, "gnu_time_complete": not any(missing.values()), "missing_gnu_time_fields": missing})
    (area / "qualification-summary.json").write_bytes(canonical({"rows": rows}) + b"\n")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="create immutable manifests and dispatch the local serial WaveScheduler cells")
    parser.add_argument("--cix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/cix")
    parser.add_argument("--uncix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/uncix")
    parser.add_argument("--area", type=Path, default=ROOT / "docs/research/2026-10-01-cix-optimization/cix-parallel-qualification")
    args = parser.parse_args()
    plan = {"source": str(SOURCE), "source_sha256": SOURCE_SHA256, "range": {"offset": RANGE_OFFSET, "length": RANGE_LENGTH, "sha256": RANGE_SHA256},
            "cells": REPETITIONS * 4, "repetitions": REPETITIONS, "budget_seconds_per_cell": WALL_SECONDS,
            "matrix": [{"threads": threads, "parallelism": parallelism, "flags": exact_flags(threads, parallelism)} for threads in (1, 4) for parallelism in ("candidates", "blocks")],
            "reserved_cpus": RESERVED_CPUS,
            "execution": "blocked until --run; no acquisition and no benchmark execution occurred"}
    if not args.run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    cells = prepare(args.area.resolve(), args.cix.resolve(), args.uncix.resolve())
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    rows = []
    for cell in cells:  # serial wave: parallel cells lease all four physical cores alone
        rows.extend(scheduler.run_wave([cell]))
    summary = summarize(args.area.resolve(), rows)
    print(json.dumps(rows, indent=2, sort_keys=True))
    if any(row.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for row in rows):
        raise RuntimeError("qualification stopped on a non-verified cell; do not retry its immutable identity")
    if any(not row.get("gnu_time_complete", False) for row in summary):
        raise RuntimeError("GNU time wall/CPU/max-RSS evidence is incomplete; do not claim timing results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
