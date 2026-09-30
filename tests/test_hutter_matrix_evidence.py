import hashlib
import json
import struct
from pathlib import Path

import pytest

from benchmarks.hutter_matrix_evidence import HEADER, collect, parse_complete_archive


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_archive(path: Path, *, magic=b"CIXSTR1\0", mode=0):
    metadata, payload = b"{}", b"paq8px-test"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(HEADER.pack(magic, mode, 9, 8, len(metadata)) + metadata + payload)


def receipt(directory: Path, *, experiment_id: str, status="VERIFIED_SCREENING", mode="original", mechanism="raw original-byte PAQ control", fixture=False, complete=True):
    work = directory / "work"; work.mkdir(parents=True)
    archive, restored = work / "candidate.cix", work / "restored.bin"
    if complete:
        write_archive(archive, magic=b"CIXWBOD1" if mode == "body" else b"CIXSTR1\0")
    restored.write_bytes(b"source-ok")
    source = "/tmp/fixture.bin" if fixture else "/tmp/enwik9"
    row = {
        "experiment_id": experiment_id, "status": status, "archive_bytes": archive.stat().st_size if complete else 0,
        "archive_sha256": digest(archive) if complete else "", "artifacts": {"archive": str(archive), "restored": str(restored)},
        "identity": {"input": {"path": source, "offset": 0, "length": 9, "sha256": digest(restored)},
                     "configuration": {"mode": mode, "paq_binary_sha256": "p", "paq_options": "-4", "source_filename": "candidate.source.bin"},
                     "initial_state": "empty", "build_sha256": {}},
        "verification": {"matched": status == "VERIFIED_SCREENING", "restored_sha256": digest(restored)},
        "phases": [{"phase": "trial-encode", "exit_code": 0 if complete else 1, "stop_reason": None if complete else "budget"}],
        "mechanism": mechanism,
    }
    name = "receipt.json" if status == "VERIFIED_SCREENING" else "size-rejected.json" if status == "SIZE_REJECTED_UNVERIFIED" else "failed.json"
    (directory / name).write_text(json.dumps(row))


def test_parse_complete_archive_rehashes_and_accounts(tmp_path):
    archive = tmp_path / "a"; write_archive(archive, magic=b"CIXWCOL1", mode=2)
    parsed = parse_complete_archive(archive, digest(archive), archive.stat().st_size)
    assert parsed["total_bytes"] == parsed["framing_bytes"] + parsed["metadata_bytes"] + parsed["paq_payload_bytes"]
    with pytest.raises(ValueError, match="SHA-256"):
        parse_complete_archive(archive, "0" * 64)


def test_collect_keeps_size_rejection_and_matches_only_identical_control(tmp_path):
    base = tmp_path / "docs/research/2026-09-30-wikipedia-body/runs"
    receipt(base / "control", experiment_id="control", fixture=True)
    receipt(base / "candidate", experiment_id="candidate", mode="body", mechanism="body dictionary", fixture=True)
    receipt(base / "rejected", experiment_id="rejected", status="SIZE_REJECTED_UNVERIFIED", mode="body", mechanism="body dictionary", fixture=True)
    rows = collect(tmp_path)
    by_id = {row["evidence_id"]: row for row in rows}
    assert by_id["control"]["verification"] is True
    assert by_id["candidate"]["difference_vs_matched_raw_paq_bytes"] == 0
    assert by_id["rejected"]["verification"] is False
    assert by_id["rejected"]["decode_skipped"] is True
    assert by_id["candidate"]["evidence_stratum"] == "synthetic"


def test_collect_excludes_partial_failure_from_size_evidence(tmp_path):
    base = tmp_path / "docs/research/2026-09-30-wikipedia-columns/runs"
    receipt(base / "failed", experiment_id="failed", status="FAILED", complete=False)
    row = collect(tmp_path)[0]
    assert row["archive"] is None
    assert row["partial_archive"] is None  # no partial file was emitted
    assert row["difference_vs_matched_raw_paq_bytes"] is None


def test_duplicate_experiment_ids_are_refused(tmp_path):
    base = tmp_path / "docs/research/2026-09-30-wikipedia-body/runs"
    receipt(base / "one", experiment_id="same", fixture=True)
    receipt(base / "two", experiment_id="same", fixture=True)
    with pytest.raises(ValueError, match="duplicate experiment"):
        collect(tmp_path)
