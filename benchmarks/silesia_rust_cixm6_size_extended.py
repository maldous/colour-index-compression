#!/usr/bin/env python3
"""One-cell, extended-budget Silesia CIXM6 size-profile diagnostic."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.silesia_rust_native_matrix import INPUT_PLAN, ROOT, physical_cpus, sha

AREA = ROOT / "docs/research/2026-10-01-rust-native/silesia-rust-cixm6-size-extended-v2"
MANIFEST = AREA / "manifest.json"
CELL_ID = "silesia-rust-cixm6-size-dickens-1200s-300m-v2"


def prepare():
    if AREA.exists():
        raise RuntimeError(f"experiment already exists; preserve it: {AREA}")
    plan = json.loads(INPUT_PLAN.read_text())
    item = next(x for x in plan["inputs"] if x["name"] == "dickens")
    source = Path(item["path"])
    if source.stat().st_size != item["bytes"] or sha(source) != item["sha256"]:
        raise RuntimeError("frozen Dickens Silesia identity changed")
    AREA.mkdir(parents=True)
    cpu = physical_cpus()[0]
    adapter = str(ROOT / "benchmarks/silesia_rust_client.py")
    archive, restored = "{workdir}/candidate.cix", "{workdir}/restored.bin"
    config = {
        "method": "cix-rust-native", "format": "cixm6", "profile": "size",
        "level": 9, "block_bytes": 65536, "memory_mib": 512,
        "route_policy": "native Rust bounded selector; not Python timing-dependent selector parity",
        "repetitions": 1, "warmups": 0,
        "native_commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "reason_for_new_identity": "Prior CIXM6 size cell reached the inherited 300-second ceiling; this cell grants up to 1200 seconds and 300 MB temporary space, retaining the same codec settings.",
    }
    build = ["dist/cix", "dist/uncix", "benchmarks/silesia_rust_client.py",
             "benchmarks/silesia_rust_native_matrix.py", "benchmarks/silesia_rust_cixm6_size_extended.py",
             "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py",
             "rust/cix-native/Cargo.toml", "rust/cix-native/Cargo.lock"]
    build.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT / "rust/cix-native/src").rglob("*.rs")))
    manifest = {
        "hypothesis": "The native Rust CIXM6 size profile can complete a previously time-limited Silesia encode when given a 20-minute phase ceiling and enough temporary space for the input, archive, and restored output.",
        "matched_control": "Same full Dickens bytes and CIXM6 size settings as the prior frozen 300-second cell; new identity is solely for the declared resource ceiling change.",
        "input": {"path": item["path"], "offset": 0, "length": item["bytes"], "sha256": item["sha256"], "full_asset_sha256": item["sha256"], "dataset": "official Silesia"},
        "configuration": config,
        "initial_state": "empty native model state per complete Silesia member; stream-internal history follows the format definition",
        "mechanism": "Packaged native Rust cix/uncix binaries; entire archive framing/checksum/footer counted; separate archive-only decode and exact hash verification.",
        "budget": {"cpu": cpu, "max_rss_bytes": 2_000_000_000, "max_temp_bytes": 300_000_000, "wall_seconds": 1200, "swap_bytes": 0},
        "stage": "moderate_contiguous",
        "longer_budget_justification": "The prior identical Dickens CIXM6 size configuration reached its 300-second encode ceiling without completing. This new immutable diagnostic allows up to 1200 seconds, within the existing runner's moderate-contiguous policy, because this complete Silesia member is 10,192,446 bytes (below 16 MiB). Temporary space is raised from 100 MB to 300 MB after separate larger-file decodes hit the previous cap. No result-driven configuration or codec setting changes.",
        "promotion_criteria": "Complete archive within budget, independent Rust decode, exact restored byte count and SHA-256; otherwise preserve terminal failure without retry.",
        "exposure": "Previously exposed official Silesia Dickens asset only; no acquisition or other dataset comparison.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.time.txt", sys.executable, adapter, "encode", "{source}", archive, "--profile", "size", "--format", "cixm6", "--workdir", "{workdir}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.time.txt", sys.executable, adapter, "decode", archive, restored, "--profile", "size", "--format", "cixm6", "--workdir", "{workdir}"],
        "artifacts": {"archive": archive, "restored": restored},
        "build_paths": build,
        "resource_accounting": "WaveScheduler: one physical core, 2 GB per-cell memory, 300 MB per-cell temporary cap, 1200 seconds per phase, no swap; aggregate scheduler remains four cores/12 GB/4 GB.",
    }
    MANIFEST.write_bytes(canonical(manifest) + b"\n")
    frozen, manifest_sha = load_manifest(MANIFEST)
    build_sha = build_identity(frozen, ROOT)
    cell = {"cell_id": CELL_ID, "owner": "/root", "manifest_path": str(MANIFEST.relative_to(ROOT)),
            "output_dir": str((AREA / "run").relative_to(ROOT)), "expected_manifest_sha256": manifest_sha,
            "expected_build_sha256": build_sha,
            "fresh_justification": "New experiment identity is required to increase the declared wall and temporary-space budgets after the prior cell terminated at its frozen ceiling."}
    (AREA / "cells.json").write_text(json.dumps([cell], indent=2) + "\n")
    (AREA / "environment.json").write_text(json.dumps({"status": "FROZEN_NOT_YET_RUN", "cells": 1,
      "wall_seconds": 1200, "temporary_bytes": 300_000_000, "memory_bytes": 2_000_000_000,
      "aggregate": {"cores": 4, "ram_bytes": 12_000_000_000, "temporary_bytes": 4_000_000_000, "swap_bytes": 0},
      "input": item["name"], "input_sha256": item["sha256"], "profile": "CIXM6 size (-9)"}, indent=2) + "\n")
    print(json.dumps({"cell_id": CELL_ID, "manifest_sha256": manifest_sha, "build_sha256": build_sha}, sort_keys=True))


def run():
    cells = json.loads((AREA / "cells.json").read_text())
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    results = scheduler.run_wave(cells)
    print(json.dumps(results, sort_keys=True), flush=True)
    if any(row.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for row in results):
        raise RuntimeError("extended Dickens CIXM6 size trial stopped on failure; do not retry")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("prepare", "run"))
    a = p.parse_args()
    prepare() if a.action == "prepare" else run()
