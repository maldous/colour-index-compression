#!/usr/bin/env python3
"""Prepare, but never dispatch, the two pending CIXG2 scaling jobs.

Root runs this only after S-M6 has a terminal receipt, then submits each JSON
job through the existing WaveScheduler one at a time. This program neither
starts a process nor imports a scheduler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/user/src/colour-index-compression")
WORK = ROOT / "benchmark-work/release-performance-01"
RUNNER = ROOT / "docs/research/2026-10-04-release-0.1/performance_run.py"
PLAN = ROOT / "docs/research/2026-10-04-release-0.1/performance-plan-v2/plan.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def protocol() -> dict:
    selected = WORK / "selected/cix"
    decoder = WORK / "selected/uncix"
    input_path = ROOT / "benchmark-work/canterbury/kennedy.xls"
    m6 = ROOT / "docs/research/2026-10-04-release-0.1/raw/perf-s-m6-v1/result.json"
    if not (selected.is_file() and decoder.is_file() and input_path.is_file()):
        raise SystemExit("selected B0 binaries or frozen Kennedy input are missing")
    if not m6.is_file() or json.loads(m6.read_text()).get("exit_code") is None:
        raise SystemExit("S-M6 must have a terminal receipt before preparing G2 jobs")
    common = [str(selected), "--format", "cixg2", "--block-size", "16KiB", "--memory", "256MiB", "-f"]
    cells = []
    for workers, cpus in ((1, [8]), (4, [8, 10, 12, 14])):
        ident = f"S-G2-AUTO-{workers}"
        out = WORK / "evidence" / ident
        archive = out / "artifacts" / f"{ident}.cix"
        cells.append({
            "id": ident,
            "status": "PREPARED_NOT_DISPATCHED",
            "argv": [*common, "--threads", str(workers), "-o", str(archive), str(input_path)],
            "fresh_decode": [str(decoder), "-f", "-o", str(out / "verification/restored"), str(archive)],
            "resources": {"cpus": cpus, "memory_bytes": 2_000_000_000, "temp_bytes": 256_000_000, "swap_bytes": 0, "wall_seconds": 300},
            "acceptance": [
                "one observation only; existing WaveScheduler lease only",
                "capture stdout, stderr, /usr/bin/time -v, cgroup and affinity receipts",
                "fresh decoder SHA-256 equals frozen input",
                "one- and four-worker complete archive SHA-256 values equal",
                "report wall, user CPU, system CPU, peak RSS and cgroup high-water",
            ],
        })
    return {
        "schema": "cix-v0.1-g2-extension-v1",
        "status": "PREPARED_NOT_DISPATCHED",
        "preconditions": {"s_m6": json.loads(m6.read_text()), "plan": str(PLAN), "runner": str(RUNNER), "selected_cix_sha256": sha256(selected), "selected_uncix_sha256": sha256(decoder), "input_sha256": sha256(input_path)},
        "dispatch": "root-owned WaveScheduler; run serially under one lease; do not alter the frozen v2 plan",
        "cells": cells,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the prepared protocol; omitted prints it")
    args = parser.parse_args()
    value = protocol()
    encoded = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit("refusing to overwrite a protocol receipt")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
