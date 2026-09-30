#!/usr/bin/env python3
"""Read-only, physical evidence collector for bounded Wikipedia experiments.

This module deliberately consumes runner receipts rather than trial reports.  It
does not execute a codec, select a portfolio, or make an aggregate/full-enwik9
claim.  A complete archive is rehashed before it is reported; an archive that
lost the completed size gate remains a useful *unverified* size observation.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any


HEADER = struct.Struct(">8sBQQI")
MAGICS = {
    b"CIXSTR1\0": {0, 1, 2, 3},
    b"CIXWCOL1": {0, 1, 2},
    b"CIXWBOD1": {0},
    b"CIXWUNT1": {0, 1, 2},
}
TERMINAL_FILES = ("receipt.json", "size-rejected.json", "failed.json")
EVIDENCE_ROOTS = (
    "docs/research/2026-09-30-wikipedia-structure/moderate/runs",
    "docs/research/2026-09-30-wikipedia-structure/results",
    "docs/research/2026-09-30-wikipedia-columns/runs",
    "docs/research/2026-09-30-wikipedia-body/runs",
    "docs/research/2026-09-30-wikipedia-matrix/runs",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def parse_complete_archive(path: Path, expected_sha256: str | None = None,
                           expected_bytes: int | None = None) -> dict[str, Any]:
    """Rehash and account for one complete CIX outer frame.

    The layout is shared deliberately by CIXSTR1, CIXWCOL1 and CIXWBOD1:
    29-byte header, paid metadata, then PAQ payload.  Metadata is not added to
    any transform accounting a second time.
    """
    actual_sha, total = sha256(path), path.stat().st_size
    if expected_sha256 is not None and actual_sha != expected_sha256:
        raise ValueError("archive SHA-256 mismatch")
    if expected_bytes is not None and total != expected_bytes:
        raise ValueError("archive byte count mismatch")
    with path.open("rb") as stream:
        head = stream.read(HEADER.size)
        if len(head) != HEADER.size:
            raise ValueError("short outer archive")
        magic, mode, original_bytes, transformed_bytes, metadata_bytes = HEADER.unpack(head)
        metadata = stream.read(metadata_bytes)
        payload_prefix = stream.read(6)
    if magic not in MAGICS or mode not in MAGICS[magic]:
        raise ValueError("unknown outer archive magic or mode")
    payload_bytes = total - HEADER.size - metadata_bytes
    if payload_bytes < 6 or payload_prefix != b"paq8px":
        raise ValueError("outer frame has no PAQ payload")
    # Read the paid metadata only as opaque bytes.  Some old structure frames
    # contain transform statistics, but those are not independent byte costs.
    del metadata
    return {
        "total_bytes": total,
        "archive_sha256": actual_sha,
        "outer_magic": magic.decode("ascii"),
        "outer_mode": mode,
        "original_bytes": original_bytes,
        "transformed_bytes": transformed_bytes,
        "framing_bytes": HEADER.size,
        "metadata_bytes": metadata_bytes,
        "paq_payload_bytes": payload_bytes,
        "physical_size_conserved": total == HEADER.size + metadata_bytes + payload_bytes,
    }


def _terminal_paths(root: Path) -> list[Path]:
    found: list[Path] = []
    for relative in EVIDENCE_ROOTS:
        base = root / relative
        if not base.is_dir():
            continue
        for name in TERMINAL_FILES:
            found.extend(base.rglob(name))
    return sorted(set(found))


def _first_terminal(directory: Path) -> Path | None:
    paths = [directory / name for name in TERMINAL_FILES if (directory / name).is_file()]
    if len(paths) > 1:
        raise ValueError(f"multiple terminal records in {directory}")
    return paths[0] if paths else None


def _stratum(record: dict[str, Any], receipt_path: Path) -> str:
    inp = record.get("identity", {}).get("input", {})
    source = str(inp.get("path", "")).lower()
    config = record.get("identity", {}).get("configuration", {})
    declared = str(config.get("evidence_stratum", "")).strip()
    if declared in {"synthetic", "targeted_real", "fixed_development", "untouched_holdout"}:
        return declared
    if "synthetic" in source or "fixture" in source or "synthetic" in str(receipt_path).lower():
        return "synthetic"
    # A promotion criterion mentioning future holdouts does not make this
    # completed input a holdout.  Require an explicit input/config declaration.
    if "holdout" in str(config).lower() or "/holdout/" in source:
        return "untouched_holdout"
    if int(inp.get("length", 0) or 0) >= 4 * 1024 * 1024:
        # Fixed offsets are development samples.  They have not been sampled
        # probabilistically, so calling them representative would overstate
        # the evidence.
        return "fixed_development"
    return "targeted_real"


def _extract_transform_accounting(directory: Path) -> dict[str, Any] | None:
    """Return encoder diagnostics, never a made-up per-field PAQ allocation."""
    logs = sorted(directory.glob("*-encode.stdout.log"))
    for log in logs:
        try:
            lines = log.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and isinstance(value.get("transform_accounting"), dict):
                return value["transform_accounting"]
    return None


def _program_costs(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """Report source dependency identities without pretending this is packaging."""
    builds = record.get("identity", {}).get("build_sha256", {})
    sources = []
    if isinstance(builds, dict):
        for name, expected in sorted(builds.items()):
            path = root / str(name)
            current_bytes: int | None = None
            current_match: bool | None = None
            if path.is_file():
                current_bytes = path.stat().st_size
                current_match = sha256(path) == expected
            sources.append({"path": str(name), "build_sha256": expected,
                            "current_source_bytes": current_bytes,
                            "current_source_hash_matches_build": current_match})
    binary: dict[str, Any] = {"path": None, "bytes": None, "sha256": None, "hash_matches_pinned": None}
    expected = record.get("identity", {}).get("configuration", {}).get("paq_binary_sha256")
    for phase in record.get("phases", []) or []:
        command = phase.get("command", []) if isinstance(phase, dict) else []
        if "--paq-binary" in command:
            candidate = Path(command[command.index("--paq-binary") + 1])
            if candidate.is_file():
                actual = sha256(candidate)
                binary = {"path": str(candidate), "bytes": candidate.stat().st_size,
                          "sha256": actual, "hash_matches_pinned": actual == expected}
            break
    return {"source_dependencies": sources, "paq_binary": binary,
            "runtime_closure": "incomplete; source and current PAQ binary sizes are audit fields, not a Hutter package score"}


def _is_raw_paq_control(row: dict[str, Any]) -> bool:
    config = row["configuration"]
    mechanism = str(row.get("mechanism", "")).lower()
    return (row["status"] == "VERIFIED_SCREENING" and row["verification"] is True
            and str(config.get("mode", "")) == "original"
            and any(marker in mechanism for marker in ("raw", "original-byte", "unchanged-byte")))


def _control_key(row: dict[str, Any]) -> tuple[Any, ...]:
    inp, config = row["input"], row["configuration"]
    # Receipts use slightly different prose for the same documented empty
    # reset.  Normalize only that narrow, decoder-reproducible policy; every
    # non-reset policy stays literal and therefore cannot be accidentally
    # matched with it.
    initial = str(row.get("initial_state") or "")
    words = initial.lower()
    reset_policy = "reset_empty" if ("empty" in words and "preserv" not in words
                                     and "shared" not in words and "warm-up" in words) else initial
    return (inp.get("path"), inp.get("offset"), inp.get("length"), inp.get("sha256"),
            config.get("paq_binary_sha256"), config.get("paq_options"),
            config.get("source_filename"), reset_policy)


def _decode_status(record: dict[str, Any], restored: Path | None, source_hash: str | None) -> tuple[bool, str | None]:
    verification = record.get("verification", {})
    if record.get("status") != "VERIFIED_SCREENING" or not verification.get("matched"):
        return False, None
    if restored is None or not restored.is_file():
        raise ValueError("verified receipt lacks restored artifact")
    restored_sha = sha256(restored)
    if restored_sha != source_hash or restored_sha != verification.get("restored_sha256"):
        raise ValueError("restored output SHA-256 mismatch")
    return True, restored_sha


def _row(root: Path, path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text())
    identity = record.get("identity")
    if not isinstance(identity, dict) or not isinstance(identity.get("input"), dict) or not isinstance(identity.get("configuration"), dict):
        raise ValueError(f"malformed receipt identity: {path}")
    input_id, configuration = identity["input"], identity["configuration"]
    artifacts = record.get("artifacts", {})
    archive_path = Path(artifacts["archive"]) if artifacts.get("archive") else None
    restored_path = Path(artifacts["restored"]) if artifacts.get("restored") else None
    status = str(record.get("status", "UNKNOWN"))
    encode = next((phase for phase in record.get("phases", []) if isinstance(phase, dict) and str(phase.get("phase", "")).endswith("-encode")), None)
    encoded_complete = bool(encode and encode.get("exit_code") == 0 and encode.get("stop_reason") is None)
    archive = None
    partial = None
    if archive_path is not None and archive_path.is_file() and encoded_complete:
        archive = parse_complete_archive(archive_path, record.get("archive_sha256"), record.get("archive_bytes"))
        archive["path"] = _relative(root, archive_path)
    elif archive_path is not None and archive_path.is_file():
        partial = {"path": _relative(root, archive_path), "bytes": archive_path.stat().st_size,
                   "sha256": sha256(archive_path),
                   "note": "encode did not complete; partial bytes are diagnostic and excluded from compression-size evidence"}
    verified, restored_sha = _decode_status(record, restored_path, input_id.get("sha256"))
    phases = []
    for phase in record.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        phases.append({key: phase.get(key) for key in ("phase", "elapsed_seconds", "cpu_usage_seconds", "exit_code", "stop_reason", "peak_temp_bytes", "sampled_cgroup_memory_high_water_bytes", "memory_measurement_note")})
    return {
        "evidence_id": str(record.get("experiment_id", path.parent.name)),
        "receipt_path": _relative(root, path),
        "source_tree": _relative(root, path.parent),
        "status": status,
        "evidence_stratum": _stratum(record, path),
        "hypothesis": record.get("hypothesis"),
        "mechanism": record.get("mechanism"),
        "matched_control_claim": record.get("matched_control"),
        "promotion_criteria": record.get("promotion_criteria"),
        "input": dict(input_id),
        "configuration": dict(configuration),
        "initial_state": identity.get("initial_state"),
        "build_sha256": identity.get("build_sha256", {}),
        "archive": archive,
        "partial_archive": partial,
        "verification": verified,
        "restored_sha256": restored_sha,
        "decode_skipped": status == "SIZE_REJECTED_UNVERIFIED",
        "decode_size_gate": record.get("decode_size_gate"),
        "phases": phases,
        "cgroup_memory_note": record.get("cgroup_memory_note", "sampled cgroup high-water is a lower bound, not RSS"),
        "transform_accounting": _extract_transform_accounting(path.parent),
        "transform_accounting_note": "encoder diagnostic only; no joint PAQ payload is assigned to individual fields",
        "program_costs": _program_costs(root, record),
    }


def collect(root: Path | str) -> list[dict[str, Any]]:
    """Collect de-duplicated, rehashed terminal evidence in stable order.

    Duplicate receipt paths and repeated experiment identifiers are refused
    rather than silently counted twice.  Every candidate is returned before
    any caller's portfolio-selection or ranking logic.
    """
    repository = Path(root).resolve()
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    for candidate in _terminal_paths(repository):
        terminal = _first_terminal(candidate.parent)
        if terminal is None or terminal in seen_paths:
            continue
        seen_paths.add(terminal)
        row = _row(repository, terminal)
        if row["evidence_id"] in seen_ids:
            raise ValueError(f"duplicate experiment evidence id: {row['evidence_id']}")
        seen_ids.add(row["evidence_id"])
        rows.append(row)
    controls = { _control_key(row): row for row in rows if _is_raw_paq_control(row) and row["archive"] }
    for row in rows:
        control = controls.get(_control_key(row))
        if control is None:
            row["matched_raw_paq_control"] = None
            row["control_match_reason"] = "no independently verified raw PAQ control with identical input, PAQ hash/options, filename, and initial state"
            row["difference_vs_matched_raw_paq_bytes"] = None
        else:
            row["matched_raw_paq_control"] = {"evidence_id": control["evidence_id"],
                                               "archive_bytes": control["archive"]["total_bytes"],
                                               "receipt_path": control["receipt_path"]}
            row["control_match_reason"] = "exact input and pinned reset PAQ configuration match"
            row["difference_vs_matched_raw_paq_bytes"] = (row["archive"]["total_bytes"] - control["archive"]["total_bytes"] if row["archive"] else None)
    return sorted(rows, key=lambda item: (item["evidence_stratum"], item["receipt_path"]))
