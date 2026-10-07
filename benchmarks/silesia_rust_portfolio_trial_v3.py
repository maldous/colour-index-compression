#!/usr/bin/env python3
"""Bounded Dickens trial of Rust's portfolio CLI against frozen Python CIX size."""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.silesia_rust_native_matrix import INPUT_PLAN, ROOT, physical_cpus, sha

AREA = ROOT / "docs/research/2026-10-01-rust-native/silesia-rust-portfolio-dickens-v3"
MANIFEST = AREA / "manifest.json"
CELL_ID = "silesia-rust-portfolio-dickens-size-v3"


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
    cix, uncix = str(ROOT / "dist/cix"), str(ROOT / "dist/uncix")
    archive, restored = "{workdir}/candidate.cix", "{workdir}/restored.bin"
    manifest = {
        "hypothesis": "The native Rust --portfolio size route can match or improve the frozen Python CIX portfolio on the same Silesia Dickens member while restoring exactly.",
        "matched_control": "Frozen Python Silesia v3 size CIX cell on identical Dickens SHA-256; compare complete archive bytes and full encode/decode timings.",
        "input": {"path": item["path"], "offset": 0, "length": item["bytes"], "sha256": item["sha256"], "full_asset_sha256": item["sha256"], "dataset": "official Silesia"},
        "configuration": {"method": "cix-rust-native-portfolio", "profile": "size", "format": "portfolio auto", "level": 9, "memory_mib": 512, "streaming": False, "repetitions": 1, "warmups": 0, "native_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "selection_policy": "Rust CLI --portfolio size; full candidate and framing size selection"},
        "initial_state": "fresh process and empty selector state for the complete input",
        "mechanism": "Native Rust portfolio compares its CIXG1 candidate with eligible CIXB1 system-library backends and fixed CIX routes. The decoder uses only the final archive. The run is bounded by CLI portfolio format's 16 MiB input limit.",
        "budget": {"cpu": cpu, "max_rss_bytes": 2_000_000_000, "max_temp_bytes": 100_000_000, "wall_seconds": 300, "swap_bytes": 0},
        "stage": "screening",
        "promotion_criteria": "A complete archive must decode independently to exact source length and SHA-256. Compare archive size and encode/decode time with the frozen Python CIX size row.",
        "exposure": "Existing official Silesia Dickens member only; no acquisition or other dataset comparison.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.time.txt", sys.executable, str(ROOT / "benchmarks/silesia_rust_portfolio_adapter.py"), "encode", "{source}", archive, "--profile", "size", "--workdir", "{workdir}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.time.txt", sys.executable, str(ROOT / "benchmarks/silesia_rust_portfolio_adapter.py"), "decode", archive, restored, "--profile", "size", "--workdir", "{workdir}"],
        "artifacts": {"archive": archive, "restored": restored},
        "build_paths": ["dist/cix", "dist/uncix", "benchmarks/silesia_rust_portfolio_trial_v2.py", "benchmarks/silesia_rust_portfolio_adapter.py", "benchmarks/silesia_rust_native_matrix.py", "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py", "rust/cix-native/Cargo.toml", "rust/cix-native/Cargo.lock"] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / "rust/cix-native/src").rglob("*.rs"))],
        "resource_accounting": "Existing WaveScheduler: one physical core, 2 GB process memory, 100 MB temp, 300 seconds per phase, no swap; aggregate 4 cores/12 GB/4 GB.",
    }
    MANIFEST.write_bytes(canonical(manifest) + b"\n")
    frozen, manifest_sha = load_manifest(MANIFEST)
    build_sha = build_identity(frozen, ROOT)
    cell = {"cell_id": CELL_ID, "owner": "/root", "manifest_path": str(MANIFEST.relative_to(ROOT)), "output_dir": str((AREA / "run").relative_to(ROOT)), "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_sha, "fresh_justification": "New cell invokes the Rust auto-portfolio CLI through an executable-copy adapter; earlier harness attempts failed in the isolated adapter setup before codec execution; this identity includes root-path setup for the copied runner."}
    (AREA / "cells.json").write_text(json.dumps([cell], indent=2) + "\n")
    print(json.dumps({"cell_id": CELL_ID, "manifest_sha256": manifest_sha, "build_sha256": build_sha}, sort_keys=True))


def run():
    cells = json.loads((AREA / "cells.json").read_text())
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    results = scheduler.run_wave(cells)
    print(json.dumps(results, sort_keys=True), flush=True)
    if any(row.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for row in results):
        raise RuntimeError("Rust portfolio trial stopped on failure; do not retry this identity")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("action", choices=("prepare", "run")); a = p.parse_args()
    prepare() if a.action == "prepare" else run()
