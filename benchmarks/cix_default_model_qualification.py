#!/usr/bin/env python3
"""Prepared-only matched development check for the DEFAULT PPM policy change.

Execution is impossible without ``--run``, full candidate/control revisions,
an experiment prefix, an immutable control receipt, and an immutable existing
control build snapshot. It compares that attested control CIX binary with a
candidate release-lto CIX binary using the same latest uncix decoder,
automatic DEFAULT CLI behavior, and two frozen one-MiB Dickens
development/replication ranges in ABBA order.
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

SOURCE = Path("/home/user/src/colour-index-compression/benchmark-work/silesia/dickens")
SOURCE_BYTES = 10_192_446
SOURCE_SHA256 = "b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a"
RANGES = (("development", 0), ("replication", 1 << 20))
RANGE_LENGTH = 1 << 20
KNOWN_DEVELOPMENT_SHA256 = "afd479dd0e0339643530bf4ee3d10423265c515a06e7994bbe26ccba39aea9ab"
RESERVED_CPUS = [16, 17, 18, 19]
REPETITIONS, WALL_SECONDS = 2, 300
MEMORY_BYTES, TEMP_BYTES = 2 * 1024**3, 512 * 1024**2
POLICY = "DEFAULT: admit PPM only when input-derived predictability is greater than 0.1 and at least 64 causal prediction opportunities are present; all remaining route/model selection stays automatic."
REVISION = re.compile(r"^[0-9a-f]{40}$")
PREFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,32}$")


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


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError as error:
        raise ValueError(f"path must be within integration root: {path}") from error


def verify_cpus() -> None:
    missing = set(RESERVED_CPUS) - os.sched_getaffinity(0)
    if missing:
        raise RuntimeError(f"required CPUs unavailable: {sorted(missing)}")
    seen: set[tuple[int, int]] = set()
    for cpu in RESERVED_CPUS:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            physical = (int((base / "physical_package_id").read_text()), int((base / "core_id").read_text()))
        except (OSError, ValueError):
            physical = (0, cpu)
        if physical in seen:
            raise RuntimeError("CPU reservation contains sibling logical CPUs")
        seen.add(physical)


def validate_control_receipt(receipt: dict, control_sha256: str, control_revision: str) -> None:
    """Reject historical receipts that label a candidate revision as control provenance."""
    identity = receipt.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("--control-receipt lacks immutable identity")
    configuration = identity.get("configuration")
    if not isinstance(configuration, dict):
        raise ValueError("--control-receipt lacks immutable configuration")
    if configuration.get("implementation") != "control":
        raise ValueError("--control-receipt does not attest a control implementation")
    if configuration.get("implementation_revision") != control_revision:
        raise ValueError("--control-receipt implementation_revision does not match --control-revision")
    if configuration.get("encoder_sha256") != control_sha256:
        raise ValueError("--control-receipt encoder_sha256 does not match --control-cix")


def validate_environment(control: Path, candidate: Path, decoder: Path, candidate_revision: str,
                         control_revision: str, control_receipt: Path, prefix: str) -> tuple[dict[str, dict], dict]:
    if not REVISION.fullmatch(candidate_revision):
        raise ValueError("--candidate-revision must be a full 40-character lowercase git revision")
    if not REVISION.fullmatch(control_revision):
        raise ValueError("--control-revision must be a full 40-character lowercase git revision")
    if not PREFIX.fullmatch(prefix):
        raise ValueError("--experiment-prefix must be 1..33 safe identifier characters")
    actual_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if candidate_revision != actual_revision:
        raise RuntimeError("--candidate-revision must equal the exact current HEAD; abbreviated comparisons are forbidden")
    frozen_control_revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{control_revision}^{{commit}}"], cwd=ROOT, text=True).strip()
    if frozen_control_revision != control_revision:
        raise RuntimeError("--control-revision must name an available exact frozen commit")
    if SOURCE.stat().st_size != SOURCE_BYTES or sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("verified Dickens source identity changed")
    verify_cpus()
    for binary in (control, candidate, decoder):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise RuntimeError(f"binary is not executable: {binary}")
        relative(binary)
    control_parts = control.resolve().relative_to(ROOT).parts
    if "build" not in control_parts:
        raise ValueError("--control-cix must refer to an immutable existing profile-run build snapshot under ROOT/build")
    if not control_receipt.is_file():
        raise ValueError("--control-receipt must name an immutable receipt file")
    relative(control_receipt)
    try:
        receipt = json.loads(control_receipt.read_text())
    except json.JSONDecodeError as error:
        raise ValueError("--control-receipt is not valid JSON") from error
    control_sha256 = sha256(control)
    validate_control_receipt(receipt, control_sha256, control_revision)
    hashes = {}
    for name, offset in RANGES:
        digest = sha256(SOURCE, offset, RANGE_LENGTH)  # computed before manifest/scheduler dispatch
        if name == "development" and digest != KNOWN_DEVELOPMENT_SHA256:
            raise RuntimeError("frozen development range hash changed")
        hashes[name] = {"offset": offset, "length": RANGE_LENGTH, "sha256": digest}
    return hashes, {
        "receipt_path": relative(control_receipt),
        "receipt_sha256": sha256(control_receipt),
        "control_revision": control_revision,
        "control_encoder_sha256": control_sha256,
    }


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
            terms = [float(term) for term in elapsed.split(":")]
            row["wall"] = elapsed
            row["wall_seconds"] = sum(term * 60**power for power, term in enumerate(reversed(terms)))
    return row


def declared_build_paths(control: Path, candidate: Path, decoder: Path) -> list[str]:
    paths = [relative(control), relative(candidate), relative(decoder), "benchmarks/cix_default_model_qualification.py",
             "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py"]
    # Encoder artifacts and implementation revisions identify the two codecs.
    # Do not attribute the current harness checkout's Rust source to an older
    # immutable control build.
    return paths


def manifest(control: Path, candidate: Path, decoder: Path, candidate_revision: str, range_name: str, identity: dict,
             implementation: str, cix: Path, repetition: int, control_provenance: dict,
             harness_revision: str) -> dict:
    implementation_revision = (control_provenance["control_revision"]
                               if implementation == "control" else candidate_revision)
    return {
        "hypothesis": "The frozen DEFAULT PPM predictability >0.1 plus at least 64 causal-opportunity admission policy changes automatic model selection only when it improves the complete valid archive enough to justify its CPU/memory tradeoff.",
        "matched_control": "Control and candidate use the same input range, automatic DEFAULT CLI, latest archive-only decoder, CPU reservation, fresh process, and two repetitions. Only the immutable CIX encoder binary differs.",
        "input": {"path": str(SOURCE), **identity, "full_asset_sha256": SOURCE_SHA256, "dataset": "existing verified Silesia Dickens", "range_kind": range_name},
        "configuration": {"implementation": implementation, "profile": "default", "effort_flags": [], "verbose": True,
                          "explicit_strategy_overrides": [], "policy": POLICY, "repetition": repetition,
                          "range_kind": range_name,
                          "expected_selector_defaults": {"memory": "512MiB", "threads": 4},
                          "implementation_revision": implementation_revision,
                          "candidate_revision": candidate_revision,
                          "harness_revision": harness_revision,
                          "harness_source_sha256": sha256(Path(__file__)),
                          "encoder_sha256": sha256(cix), "decoder_sha256": sha256(decoder),
                          "control_encoder_sha256": control_provenance["control_encoder_sha256"],
                          "candidate_encoder_sha256": sha256(candidate),
                          "control_receipt_path": control_provenance["receipt_path"],
                          "control_receipt_sha256": control_provenance["receipt_sha256"]},
        "initial_state": "fresh encoder and fresh archive-only decoder; host background/cache state uncontrolled",
        "mechanism": "Actual DEFAULT CLI auto-selection with --verbose only. No route/backend/format/block/history/memory/thread flags are supplied; CPUs 16..19 are available by affinity for the normal default worker policy.",
        "budget": {"cpu": RESERVED_CPUS, "max_rss_bytes": MEMORY_BYTES, "max_temp_bytes": TEMP_BYTES, "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "stage": "method_development",
        "promotion_criteria": "Exact archive-only restoration plus complete archive hash/size, GNU time wall/CPU/max-RSS, and verbose selector stderr. Publish losses and resource tradeoffs alongside any archive-size change; no single metric constitutes domination.",
        "exposure": "Development and disjoint replication ranges from already verified Dickens bytes. The replication range hash is generated before dispatch; neither is represented as an unseen historical holdout or a ranking result.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(cix.resolve()), "--verbose", "-o", "{workdir}/candidate.cix", "{source}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(decoder.resolve()), "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": declared_build_paths(control, candidate, decoder),
        "resource_accounting": "All cells lease CPUs 16,17,18,19 and run in serial waves. WaveScheduler aggregate cap: four physical cores, 12 GB RAM, 4 GB temporary storage, no swap.",
    }


def abba_order(control: Path, candidate: Path) -> tuple[tuple[str, Path, int], ...]:
    return (("control", control, 1), ("native-candidate", candidate, 1),
            ("native-candidate", candidate, 2), ("control", control, 2))


def prepare(area: Path, control: Path, candidate: Path, decoder: Path, candidate_revision: str,
            control_revision: str, control_receipt: Path, prefix: str) -> list[dict]:
    identities, control_provenance = validate_environment(
        control, candidate, decoder, candidate_revision, control_revision, control_receipt, prefix)
    harness_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if area.exists():
        raise RuntimeError(f"evidence area exists; preserve its immutable cells: {area}")
    directory = area / "manifests"
    directory.mkdir(parents=True)
    cells = []
    for range_name, _ in RANGES:
        for implementation, cix, repetition in abba_order(control, candidate):
            # Full revisions are included; never compare or identify builds by a short SHA.
            cell_id = f"{prefix}-native-{candidate_revision}-{range_name}-{implementation}-r{repetition}"
            path = directory / f"{cell_id}.json"
            path.write_bytes(canonical(manifest(
                control, candidate, decoder, candidate_revision, range_name, identities[range_name],
                implementation, cix, repetition, control_provenance, harness_revision)) + b"\n")
            frozen, manifest_sha = load_manifest(path)
            cells.append({"cell_id": cell_id, "owner": "/root", "manifest_path": str(path.relative_to(ROOT)),
                          "output_dir": str((area / "runs" / cell_id).relative_to(ROOT)), "cpu": RESERVED_CPUS,
                          "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_identity(frozen, ROOT),
                          "fresh_justification": "Predeclared ABBA repetitions distinguish archive effect from local timing variation."})
    (area / "cells.json").write_text(json.dumps(cells, indent=2) + "\n")
    return cells


def selector_stderr(receipt: Path) -> dict:
    experiment = json.loads(receipt.read_text())["experiment_id"][:12]
    path = receipt.parent / f"cix-bounded-{experiment}-encode.stderr.log"
    return {"path": str(path), "available": path.is_file(), "sha256": sha256(path) if path.is_file() else None,
            "text": path.read_text(errors="replace") if path.is_file() else None}


def validate_complete_archive_replicates(rows: list[dict]) -> dict[str, int]:
    """Require two equal complete archive sizes for every implementation/range."""
    grouped: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        value = row.get("archive_bytes")
        if type(value) is not int or value < 0:
            raise RuntimeError(f"{row.get('cell_id', 'unknown cell')} lacks a non-negative complete archive byte count")
        range_kind, implementation = row.get("range_kind"), row.get("implementation")
        if not isinstance(range_kind, str) or not isinstance(implementation, str):
            raise RuntimeError(f"{row.get('cell_id', 'unknown cell')} lacks implementation/range provenance")
        key = (range_kind, implementation)
        grouped.setdefault(key, []).append(value)
    result = {}
    for (range_kind, implementation), values in grouped.items():
        if len(values) != REPETITIONS:
            raise RuntimeError(f"{range_kind}/{implementation} has {len(values)} archive repetitions, expected {REPETITIONS}")
        if len(set(values)) != 1:
            raise RuntimeError(f"{range_kind}/{implementation} archive bytes differ across repetitions: {values}")
        result[f"{range_kind}/{implementation}"] = values[0]
    return result


def provenance_from_normalized_identity(cell: dict, configuration: dict, input_identity: dict,
                                        root: Path = ROOT, manifest_loader=load_manifest) -> tuple[object, object, object]:
    """Restore only declared immutable provenance omitted by scheduler normalization."""
    implementation = configuration.get("implementation")
    range_kind = configuration.get("range_kind")
    implementation_revision = configuration.get("implementation_revision")
    if isinstance(implementation, str) and isinstance(range_kind, str):
        return implementation, range_kind, implementation_revision
    manifest_path = cell.get("manifest_path")
    expected_sha = cell.get("expected_manifest_sha256")
    if not isinstance(manifest_path, str) or not isinstance(expected_sha, str):
        raise RuntimeError(f"{cell.get('cell_id', 'unknown cell')} lacks immutable manifest provenance")
    candidate = (root / manifest_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError("declared manifest path escapes qualification root") from error
    declared, actual_sha = manifest_loader(candidate)
    if actual_sha != expected_sha:
        raise RuntimeError(f"{cell.get('cell_id', 'unknown cell')} declared manifest hash changed")
    declared_configuration = declared.get("configuration", {})
    declared_input = declared.get("input", {})
    if not isinstance(declared_configuration, dict) or not isinstance(declared_input, dict):
        raise RuntimeError("declared manifest has invalid provenance sections")
    return (
        implementation if isinstance(implementation, str) else declared_configuration.get("implementation"),
        range_kind if isinstance(range_kind, str) else declared_input.get("range_kind"),
        implementation_revision if isinstance(implementation_revision, str)
        else declared_configuration.get("implementation_revision"),
    )


def summarize(area: Path, dispatched: list[dict]) -> list[dict]:
    required = {"wall_seconds", "user_seconds", "system_seconds", "max_rss_kib"}
    rows = []
    for cell in dispatched:
        receipt_name = cell.get("runner_result", {}).get("receipt")
        if not receipt_name:
            rows.append({"cell_id": cell["cell_id"], "runner_status": cell.get("runner_status")})
            continue
        receipt = Path(receipt_name)
        record = json.loads(receipt.read_text())
        identity = record.get("identity", {})
        configuration = identity.get("configuration", {}) if isinstance(identity, dict) else {}
        input_identity = identity.get("input", {}) if isinstance(identity, dict) else {}
        implementation, range_kind, implementation_revision = provenance_from_normalized_identity(
            cell, configuration, input_identity)
        work = receipt.parent / "work"
        encoded, decoded = gnu_time(work / "encode.gnu-time.txt"), gnu_time(work / "decode.gnu-time.txt")
        rows.append({"cell_id": cell["cell_id"], "runner_status": cell.get("runner_status"), "archive_bytes": record.get("archive_bytes"),
                     "archive_sha256": record.get("archive_sha256"), "verification": record.get("verification"),
                     "implementation": implementation,
                     "implementation_revision": implementation_revision,
                     "range_kind": range_kind,
                     "encode_gnu_time": encoded, "decode_gnu_time": decoded, "selector_stderr": selector_stderr(receipt),
                     "gnu_time_complete": required <= set(encoded) and required <= set(decoded),
                     "interpretation": "Record archive cost and all losses; compare size, encode/decode wall/CPU, and RSS as a Pareto tradeoff, never a universal domination claim."})
    replicate_archive_bytes = validate_complete_archive_replicates(rows)
    (area / "default-model-summary.json").write_bytes(canonical({"policy": POLICY, "replicate_archive_bytes": replicate_archive_bytes, "rows": rows}) + b"\n")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="create immutable cells and execute serial WaveScheduler waves")
    parser.add_argument("--control-cix", type=Path, required=True, help="existing profile-run immutable build/cix under ROOT")
    parser.add_argument("--candidate-cix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/cix")
    parser.add_argument("--uncix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/uncix")
    parser.add_argument("--candidate-revision", required=True, help="full 40-character candidate git revision")
    parser.add_argument("--control-revision", required=True, help="full 40-character frozen control source revision")
    parser.add_argument("--control-receipt", type=Path, required=True,
                        help="immutable receipt attesting --control-cix hash and control implementation revision")
    parser.add_argument("--experiment-prefix", required=True, help="new immutable experiment identifier prefix")
    parser.add_argument("--area", type=Path, default=ROOT / "docs/research/2026-10-01-cix-optimization/cix-default-model-qualification")
    args = parser.parse_args()
    plan = {"policy": POLICY, "ranges": [{"name": name, "offset": offset, "length": RANGE_LENGTH,
            "sha256": KNOWN_DEVELOPMENT_SHA256 if name == "development" else "calculated-before-dispatch"} for name, offset in RANGES],
            "matrix": "development+replication × ABBA(control r1, candidate r1, candidate r2, control r2)", "cells": 8,
            "reserved_cpus": RESERVED_CPUS, "execution": "blocked until --run; no source hash of replication range or benchmark execution occurred"}
    if not args.run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    cells = prepare(args.area.resolve(), args.control_cix.resolve(), args.candidate_cix.resolve(),
                    args.uncix.resolve(), args.candidate_revision, args.control_revision,
                    args.control_receipt.resolve(), args.experiment_prefix)
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    dispatched = []
    for cell in cells:
        dispatched.extend(scheduler.run_wave([cell]))
    rows = summarize(args.area.resolve(), dispatched)
    print(json.dumps(dispatched, indent=2, sort_keys=True))
    if any(cell.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for cell in dispatched):
        raise RuntimeError("one or more immutable model-policy cells did not verify; do not retry their identity")
    if any(not row.get("gnu_time_complete", False) or not row["selector_stderr"]["available"] for row in rows):
        raise RuntimeError("missing GNU time or selector stderr evidence; do not claim comparison results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
