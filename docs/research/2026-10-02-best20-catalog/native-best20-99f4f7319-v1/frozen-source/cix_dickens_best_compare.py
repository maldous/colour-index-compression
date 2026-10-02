#!/usr/bin/env python3
"""Prepare or explicitly run a bounded full-Dickens Rust CIX BEST comparison.

This is a comparison driver, not a selector experiment.  Both named modes run
the public automatic command ``cix --best --verbose`` with no route, backend,
format, block, memory, history, thread, streaming, or external-codec override.
``--best`` currently means the implementation's automatic native block
shortlist plus any typed whole-archive CIXB1 backend candidates it reports. It
does not claim exhaustive search over all segmentations, container packagings,
or history policies.
It compares complete valid archives against the immutable historical Python
CIXB1/bzip2-9 receipt (2,799,567 bytes), but never treats that receipt as a
size gate: every Rust archive is decoded in a fresh archive-only process even
when it is larger.  Nothing is dispatched without ``--run``.

Use separately copied, release-metadata-bound binary pairs when comparing two
revisions.  The default ``dist`` pair is accepted for either named mode, but a
real two-mode run rejects identical encoder/decoder hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

SOURCE = ROOT / "benchmark-work/silesia/dickens"
SOURCE_BYTES = 10_192_446
SOURCE_SHA256 = "b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a"
PYTHON_RECEIPT = ROOT / (
    "docs/research/2026-10-01-complete-benchmarks/silesia-v3/runs/dickens-size-cix/"
    "57259bdced6da853a72732238697723e45b08805b99d43fd145049b421bfdd30/receipt.json"
)
PYTHON_TARGET_BYTES = 2_799_567
PYTHON_TARGET_SHA256 = "b4b0e195209b593a3cf7ee047a1addc2556c70035a3fc037b64a44ef3d45c955"
RESERVED_CPUS = [16, 17, 18, 19]
MAX_RSS_BYTES = 4_000_000_000
MAX_TEMP_BYTES = 512_000_000
WALL_SECONDS = 1_200
PREFIX = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
MODES = ("native-control", "corrected-best")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError as error:
        raise ValueError(f"path must be under repository root: {resolved}") from error


def physical_cores() -> None:
    missing = set(RESERVED_CPUS) - os.sched_getaffinity(0)
    if missing:
        raise RuntimeError(f"required CPUs unavailable: {sorted(missing)}")
    seen: set[tuple[int, int]] = set()
    for cpu in RESERVED_CPUS:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            identity = (
                int((topology / "physical_package_id").read_text()),
                int((topology / "core_id").read_text()),
            )
        except (OSError, ValueError):
            identity = (0, cpu)
        if identity in seen:
            raise RuntimeError("reserved CPU list contains sibling logical CPUs")
        seen.add(identity)


def checked_binary(path: Path, name: str) -> Path:
    resolved = path.resolve()
    if resolved.name != name:
        raise ValueError(f"{name} binary must retain its basename for archive-only execution: {resolved}")
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise RuntimeError(f"required executable binary is missing: {resolved}")
    relative(resolved)
    return resolved


def read_release_metadata(path: Path, cix: Path, uncix: Path) -> dict:
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"release metadata is missing: {path}")
    relative(path)
    try:
        metadata = json.loads(path.read_text())
        revision = metadata["source_revision"]
        binaries = metadata["binaries"]
        cix_declared = binaries["cix"]["sha256"]
        uncix_declared = binaries["uncix"]["sha256"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid release metadata: {path}") from error
    if not isinstance(revision, str) or not REVISION.fullmatch(revision):
        raise RuntimeError("release metadata must contain a full lowercase source_revision")
    resolved_revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    if resolved_revision != revision:
        raise RuntimeError("release metadata source_revision is not an available exact commit")
    for declared, binary, label in ((cix_declared, cix, "cix"), (uncix_declared, uncix, "uncix")):
        if not isinstance(declared, str) or not SHA256.fullmatch(declared):
            raise RuntimeError(f"release metadata lacks valid {label} SHA-256")
        actual = sha256(binary)
        if actual != declared:
            raise RuntimeError(f"release metadata {label} SHA-256 does not match binary: {binary}")
    return {
        "metadata_path": relative(path),
        "metadata_sha256": sha256(path),
        "source_revision": revision,
        "cix_sha256": cix_declared,
        "uncix_sha256": uncix_declared,
        "source_revision_note": "build provenance from release metadata; distinct from harness_sha256",
    }


def verify_python_target() -> dict:
    if not PYTHON_RECEIPT.is_file():
        raise RuntimeError(f"immutable Python comparison receipt missing: {PYTHON_RECEIPT}")
    try:
        receipt = json.loads(PYTHON_RECEIPT.read_text())
        identity = receipt["identity"]
        input_identity = identity["input"]
        configuration = identity["configuration"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("immutable Python comparison receipt is malformed") from error
    if (receipt.get("status") != "VERIFIED_SCREENING" or not receipt.get("verification", {}).get("matched")
            or receipt.get("archive_bytes") != PYTHON_TARGET_BYTES
            or receipt.get("archive_sha256") != PYTHON_TARGET_SHA256
            or input_identity.get("length") != SOURCE_BYTES
            or input_identity.get("sha256") != SOURCE_SHA256
            or receipt.get("verification", {}).get("restored_sha256") != SOURCE_SHA256
            or configuration.get("profile") != "size"):
        raise RuntimeError("immutable Python target receipt no longer has the declared CIXB1 comparison identity")
    return {
        "receipt": relative(PYTHON_RECEIPT),
        "receipt_sha256": sha256(PYTHON_RECEIPT),
        "archive_bytes": PYTHON_TARGET_BYTES,
        "archive_sha256": PYTHON_TARGET_SHA256,
        "format_and_route": "historical complete CIXB1 direct bzip2 level 9",
        "comparison_only": "historical Python archive is not executed or used as an early size gate",
    }


def require_environment(pairs: dict[str, dict]) -> dict:
    if not SOURCE.is_file() or SOURCE.stat().st_size != SOURCE_BYTES or sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("verified whole Dickens source identity changed")
    physical_cores()
    target = verify_python_target()
    for pair in pairs.values():
        pair["cix"] = checked_binary(pair["cix"], "cix")
        pair["uncix"] = checked_binary(pair["uncix"], "uncix")
        pair["release"] = read_release_metadata(pair["metadata"], pair["cix"], pair["uncix"])
    if (pairs["native-control"]["release"]["cix_sha256"] == pairs["corrected-best"]["release"]["cix_sha256"]
            and pairs["native-control"]["release"]["uncix_sha256"] == pairs["corrected-best"]["release"]["uncix_sha256"]):
        raise RuntimeError("comparison modes use identical binary pairs; provide a separately copied corrected-best artifact")
    return target


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
            parts = [float(value) for value in elapsed.split(":")]
            row["wall"] = elapsed
            row["wall_seconds"] = sum(value * 60 ** index for index, value in enumerate(reversed(parts)))
    return row


def selector_log(receipt: Path) -> Path:
    experiment = json.loads(receipt.read_text())["experiment_id"][:12]
    return receipt.parent / f"cix-bounded-{experiment}-encode.stderr.log"


def typed_whole_archive_ledger(text: str) -> dict:
    """Retain the forthcoming typed portfolio line without inventing coverage.

    The encoder will emit a whitespace-delimited line beginning with a CIX
    diagnostic prefix and containing ``whole_archive=yes`` plus evaluated,
    selected, and omissions fields.  Keep the source strings exactly because
    codec names and omission reasons are part of the evidence.  A missing,
    malformed, or ambiguous line remains explicitly unqualified.
    """
    lines = [line for line in text.splitlines() if re.search(r"\bwhole_archive=yes\b", line)]
    if not lines:
        return {"status": "not_emitted"}
    if len(lines) != 1:
        return {"status": "ambiguous", "line_count": len(lines), "lines": lines}
    line = lines[0]
    evaluated = re.search(r"\b(?:candidates_evaluated|evaluated)=(\d+)\b", line)
    selected = re.search(r"\bselected=(\S+)", line)
    omissions = re.search(r"\b(omitted|omissions|omission_strings|omission_reasons)=(.*)$", line)
    if evaluated is None or selected is None or omissions is None:
        return {"status": "malformed", "line": line}
    return {
        "status": "parsed", "line": line,
        "evaluated": int(evaluated.group(1)),
        "selected": selected.group(1),
        "omission_field": omissions.group(1),
        "omissions": omissions.group(2),
    }



def build_paths(pair: dict) -> list[str]:
    return [
        relative(pair["cix"]), relative(pair["uncix"]), relative(pair["metadata"]),
        "benchmarks/cix_dickens_best_compare.py", "benchmarks/hutter_bounded_runner.py",
        "benchmarks/hutter_experiment_scheduler.py",
    ]


def manifest(mode: str, repetition: int, pair: dict, python_target: dict) -> dict:
    release = pair["release"]
    return {
        "hypothesis": "Native CIX BEST automatically runs the current native per-block candidate shortlist and any implementation-reported typed whole-archive CIXB1 backend candidates on whole Dickens. The paired corrected-best artifact is measured against its named native-control artifact without user-selected route, backend, format, packaging, transform, block, history, memory, thread, stream, or external-codec override. This is not an exhaustive search over all legal segmentation, packaging, or history choices.",
        "matched_control": "Both modes use identical whole verified Dickens bytes, fresh encoder and archive-only decoder processes, two predeclared repetitions, physical CPUs 16/17/18/19, no swap, and exactly `cix --best --verbose -o OUTPUT INPUT`. The historical Python CIXB1/bzip2-9 archive is a frozen size comparator only.",
        "input": {"path": str(SOURCE), "offset": 0, "length": SOURCE_BYTES, "sha256": SOURCE_SHA256,
                  "dataset": "existing verified Silesia Dickens", "development_only": True},
        "configuration": {
            "mode": mode, "repetition": repetition, "profile": "best", "flags": ["--best", "--verbose"],
            "user_automatic_dimensions": ["route", "backend", "transform", "parameters", "block_strategy", "packaging", "history"],
            "explicit_strategy_overrides": [],
            "current_search_scope": {
                "native": "automatic current block-level shortlist with implementation-defined probes and fixed current block/segmentation policy",
                "whole_archive_backend": "only typed direct CIXB1 backend candidates explicitly emitted by the selector ledger",
                "not_established": ["exhaustive block segmentation", "all packaging variants", "all retained-history policies", "all parameter combinations"],
            },
            "encoder_sha256": release["cix_sha256"], "decoder_sha256": release["uncix_sha256"],
            "release_source_revision": release["source_revision"], "release_metadata": release,
            "harness_sha256": sha256(Path(__file__)),
            "historical_python_comparator": python_target,
        },
        "initial_state": "Fresh encoder and fresh archive-only decoder processes; host load and cache state are uncontrolled.",
        "mechanism": "A full-input BEST effort run. Native-block results and typed whole-archive backend results are recorded separately; no backend result is labelled a native-model gain. Candidate discovery, rejected trials, framing, metadata, and selected complete archive bytes are included. Verbose selector stderr is retained for post-run candidate-ledger inspection.",
        "budget": {"cpu": RESERVED_CPUS, "max_rss_bytes": MAX_RSS_BYTES, "max_temp_bytes": MAX_TEMP_BYTES,
                   "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "stage": "moderate_contiguous",
        "longer_budget_justification": "Whole Dickens is 10,192,446 bytes, below the bounded runner 16 MiB moderate-contiguous limit. BEST native candidate search previously requires about 200 seconds on representative runs; each 1,200-second cell preserves a fixed safety ceiling for complete encode plus mandatory archive-only decode. No early size gate is used.",
        "promotion_criteria": "Each cell retains a complete archive and must fresh-decode exactly before any size comparison. GNU time must provide wall, CPU, and max-RSS for encode and decode. Selector stderr is retained; native inner budget omissions and typed whole-archive evaluated/selected/omission strings are reported separately. Missing or malformed diagnostics remain unknown rather than zero omissions. This is local method-development evidence, not a ranking or renewed Silesia qualification.",
        "exposure": "Existing verified whole Dickens bytes only; no acquisition, held-out claim, corpus rank, or cross-platform claim.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(pair["cix"]), "--best", "--verbose", "-o", "{workdir}/candidate.cix", "{source}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(pair["uncix"]), "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": build_paths(pair),
        "resource_accounting": "Cells run serially. Each cell leases the four distinct physical CPUs 16/17/18/19; WaveScheduler aggregate cap is four cores, decimal 12 GB RAM, 4 GB temporary storage, and no swap.",
        "artifact_handling": "Physical input copies, archives, restored bytes, and immutable binary snapshots remain ignored under run work/build directories. Only text manifests, receipts, logs, and summaries are eligible evidence for Git.",
    }


def prepare(area: Path, prefix: str, pairs: dict, python_target: dict, repetitions: int) -> list[dict]:
    if area.exists():
        raise RuntimeError(f"immutable evidence area already exists: {area}")
    claims = ROOT / ".hutter-experiment-scheduler/claims"
    if claims.exists() and any(claims.glob(f"{prefix}-dickens-best-*.claim.json")):
        raise RuntimeError("experiment prefix already has scheduler claims")
    manifests = area / "manifests"
    manifests.mkdir(parents=True)
    (area / ".gitignore").write_text("runs/**/work/\nruns/**/build/\n")
    cells = []
    for repetition in range(1, repetitions + 1):
        for mode in MODES:
            cell_id = f"{prefix}-dickens-best-{mode}-r{repetition}"
            path = manifests / f"{cell_id}.json"
            path.write_bytes(canonical(manifest(mode, repetition, pairs[mode], python_target)) + b"\n")
            frozen, manifest_sha = load_manifest(path)
            cells.append({
                "cell_id": cell_id, "owner": "/root", "manifest_path": relative(path),
                "output_dir": relative(area / "runs" / cell_id), "cpu": RESERVED_CPUS,
                "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_identity(frozen, ROOT),
                "fresh_justification": "Predeclared fresh complete-file repetition; no archive size or timing selection between repetitions.",
            })
    (area / "cells.json").write_text(json.dumps(cells, indent=2) + "\n")
    return cells


def summarize(area: Path, rows: list[dict], python_target: dict) -> list[dict]:
    summary = []
    required_time = {"wall_seconds", "user_seconds", "system_seconds", "max_rss_kib"}
    for row in rows:
        receipt_name = row.get("runner_result", {}).get("receipt")
        if row.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} or not receipt_name:
            raise RuntimeError(f"full Dickens cell did not complete fresh verification: {row.get('cell_id')}")
        receipt = Path(receipt_name)
        result = json.loads(receipt.read_text())
        if not result.get("verification", {}).get("matched"):
            raise RuntimeError(f"fresh archive-only decode mismatch: {receipt}")
        work = receipt.parent / "work"
        encode, decode = gnu_time(work / "encode.gnu-time.txt"), gnu_time(work / "decode.gnu-time.txt")
        if not required_time <= set(encode) or not required_time <= set(decode):
            raise RuntimeError(f"incomplete GNU time evidence: {receipt}")
        log = selector_log(receipt)
        ledger = {"path": str(log), "available": log.is_file(), "sha256": sha256(log) if log.is_file() else None}
        if log.is_file():
            text = log.read_text(errors="replace")
            match = re.search(r"\bbudget_skips=(\d+)\b", text)
            ledger["native_inner"] = {
                "budget_skips": int(match.group(1)) if match else None,
                "budget_skips_status": "parsed" if match else "not_parseable",
            }
            ledger["typed_whole_archive"] = typed_whole_archive_ledger(text)
        else:
            ledger["native_inner"] = {"budget_skips": None, "budget_skips_status": "missing_log"}
            ledger["typed_whole_archive"] = {"status": "missing_log"}
        size = result.get("archive_bytes")
        summary.append({
            "cell_id": row["cell_id"], "mode": result["identity"]["configuration"]["mode"],
            "repetition": result["identity"]["configuration"]["repetition"], "archive_bytes": size,
            "archive_sha256": result.get("archive_sha256"),
            "bytes_vs_historical_python_target": size - python_target["archive_bytes"],
            "encode_gnu_time": encode, "decode_gnu_time": decode, "selector_ledger": ledger,
            "verification": result["verification"], "release_source_revision": result["identity"]["configuration"]["release_source_revision"],
        })
    (area / "comparison-summary.json").write_bytes(canonical({"historical_python_target": python_target, "rows": summary}) + b"\n")
    return summary


def pair_args(args: argparse.Namespace) -> dict[str, dict]:
    return {
        "native-control": {"cix": args.native_control_cix, "uncix": args.native_control_uncix, "metadata": args.native_control_metadata},
        "corrected-best": {"cix": args.corrected_best_cix, "uncix": args.corrected_best_uncix, "metadata": args.corrected_best_metadata},
    }


def plan(pairs: dict, prefix: str, area: Path, repetitions: int) -> dict:
    return {
        "experiment_prefix": prefix, "area": str(area), "source": {"path": str(SOURCE), "bytes": SOURCE_BYTES, "sha256": SOURCE_SHA256},
        "historical_python_target": {"bytes": PYTHON_TARGET_BYTES, "sha256": PYTHON_TARGET_SHA256, "receipt": str(PYTHON_RECEIPT), "format": "CIXB1 direct bzip2 level 9"},
        "modes": {mode: {key: str(value) for key, value in pair.items()} for mode, pair in pairs.items()},
        "command_per_cell": ["cix", "--best", "--verbose", "-o", "OUTPUT", "INPUT"], "repetitions_per_mode": repetitions,
        "cells": repetitions * len(MODES), "dispatch": "serial WaveScheduler cells only after --run",
        "resources": {"physical_cpus": RESERVED_CPUS, "aggregate_cores": 4, "aggregate_memory_bytes": 12_000_000_000,
                      "aggregate_temp_bytes": 4_000_000_000, "per_cell_rss_bytes": MAX_RSS_BYTES,
                      "per_cell_temp_bytes": MAX_TEMP_BYTES, "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "decode_policy": "fresh archive-only decoder runs for every completed archive, including archives larger than the Python target",
        "current_search_scope": "automatic current native block shortlist plus selector-emitted typed whole-archive CIXB1 backend candidates; not an exhaustive segmentation/packaging/history search",
        "artifact_handling": "Physical source/archive/restored bytes and binary snapshots are ignored; stage only text evidence.",
        "execution": "blocked until --run; no benchmark execution occurred",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="prepare immutable manifests and dispatch serial WaveScheduler cells")
    parser.add_argument("--experiment-prefix", default="cix-dickens-best-v1")
    parser.add_argument("--repetitions", type=int, choices=(1, 2), default=2)
    parser.add_argument("--area", type=Path, default=ROOT / "docs/research/2026-10-01-cix-optimization/cix-dickens-best-compare-v1")
    parser.add_argument("--native-control-cix", type=Path, default=ROOT / "dist/cix")
    parser.add_argument("--native-control-uncix", type=Path, default=ROOT / "dist/uncix")
    parser.add_argument("--native-control-metadata", type=Path, default=ROOT / "dist/native-release.json")
    parser.add_argument("--corrected-best-cix", type=Path, default=ROOT / "dist/cix")
    parser.add_argument("--corrected-best-uncix", type=Path, default=ROOT / "dist/uncix")
    parser.add_argument("--corrected-best-metadata", type=Path, default=ROOT / "dist/native-release.json")
    args = parser.parse_args()
    if not PREFIX.fullmatch(args.experiment_prefix):
        parser.error("--experiment-prefix must be 3..64 lowercase letters, digits, or hyphens")
    pairs = pair_args(args)
    if not args.run:
        print(json.dumps(plan(pairs, args.experiment_prefix, args.area.resolve(), args.repetitions), indent=2, sort_keys=True))
        return 0
    python_target = require_environment(pairs)
    cells = prepare(args.area.resolve(), args.experiment_prefix, pairs, python_target, args.repetitions)
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    rows = []
    for cell in cells:  # a four-core CIX cell consumes the complete aggregate CPU reservation
        rows.extend(scheduler.run_wave([cell]))
    summary = summarize(args.area.resolve(), rows, python_target)
    print(json.dumps({"scheduler_rows": rows, "summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
