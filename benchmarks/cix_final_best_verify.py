#!/usr/bin/env python3
"""Fresh full-Dickens archive qualification of the final native release."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks import cix_dickens_best_compare as comparison
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler


def main() -> None:
    if sys.argv[1:] != ["--run"]:
        raise SystemExit("Use --run to freeze and execute this final-release cell.")
    artifact = ROOT / "benchmark-work/cix-qualified-release/final"
    pair = {"cix": artifact / "cix", "uncix": artifact / "uncix", "metadata": artifact / "native-release.json"}
    pair["release"] = comparison.read_release_metadata(pair["metadata"], pair["cix"], pair["uncix"])
    target = comparison.verify_python_target()
    comparison.physical_cores()
    if comparison.sha256(comparison.SOURCE) != comparison.SOURCE_SHA256:
        raise RuntimeError("verified Dickens input identity changed")
    area = ROOT / "docs/research/2026-10-01-cix-optimization/cix-dickens-final-best-v1"
    area.mkdir(exist_ok=False)
    (area / ".gitignore").write_text("runs/**/work/\nruns/**/build/\n")
    manifest = comparison.manifest("corrected-best", 1, pair, target)
    manifest["hypothesis"] = "Removing arbitrary halving of the charged decoder remainder preserves the qualified whole-Dickens BEST archive and exact fresh restoration. Encoding policy/candidate registry are unchanged."
    manifest["matched_control"] = "The immediately preceding two corrected-BEST repetitions at source 08101079c have identical complete 2,799,567-byte CIXB1 archives. This cell independently verifies the final source/binary, not a timing speedup claim."
    manifest["configuration"]["mode"] = "final-best-validation"
    manifest["build_paths"].append("benchmarks/cix_final_best_verify.py")
    path = area / "manifest.json"
    path.write_bytes(canonical(manifest) + b"\n")
    frozen, manifest_sha = load_manifest(path)
    cell = {"cell_id": "cix-dickens-final-best-v1", "owner": "/root", "manifest_path": comparison.relative(path),
            "output_dir": comparison.relative(area / "runs"), "cpu": comparison.RESERVED_CPUS,
            "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_identity(frozen, ROOT),
            "fresh_justification": "Exact final release source/binary qualification after aggregate decoder-budget correction."}
    (area / "cell.json").write_text(json.dumps(cell, indent=2) + "\n")
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    rows = scheduler.run_wave([cell])
    summary = comparison.summarize(area, rows, target)
    if summary[0]["archive_sha256"] != comparison.PYTHON_TARGET_SHA256:
        raise RuntimeError("final BEST archive differs from the declared parity target")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
