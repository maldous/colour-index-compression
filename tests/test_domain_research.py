import hashlib
import json
import struct
from pathlib import Path

import pytest

from benchmarks import domain_research


def _setup(root: Path):
    (root / "benchmarks").mkdir(parents=True)
    (root / "benchmark-work/references/paq8px-v216/build-local").mkdir(parents=True)
    for name in ("domain_probe.py", "domain_molecular.py", "hutter_bounded_runner.py", "domain_research.py"):
        (root / "benchmarks" / name).write_text("# frozen\n")
    binary = root / domain_research.PAQ_BINARY
    binary.write_bytes(b"not the production binary")
    asset = root / "asset.sdf"; asset.write_bytes(b"molecule\n")
    return asset, binary


def test_prepare_freezes_asset_and_never_creates_a_decode_size_gate(tmp_path: Path, monkeypatch):
    asset, binary = _setup(tmp_path)
    monkeypatch.setattr(domain_research, "PAQ_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    cell = domain_research.prepare(asset, "molecular", "hydrogen_slots_v1", "native", [], 0, root=tmp_path)
    manifest = json.loads(Path(cell["manifest_path"]).read_text())
    assert manifest["input"]["sha256"] == hashlib.sha256(asset.read_bytes()).hexdigest()
    assert "decode_size_gate" not in manifest
    assert "--variant" in manifest["encode_command"]
    assert "--variant" not in manifest["decode_command"]
    assert manifest["encode_command"][:4] == ["/usr/bin/time", "-v", "-o", "{workdir}/encode.time.txt"]
    assert manifest["decode_command"][:4] == ["/usr/bin/time", "-v", "-o", "{workdir}/decode.time.txt"]
    assert len(manifest["configuration"]["time_binary_sha256"]) == 64
    assert manifest["budget"]["cpu"] == 0
    assert manifest["matched_control"].startswith("DECLARED original-byte PAQ control")
    assert cell == domain_research.prepare(asset, "molecular", "hydrogen_slots_v1", "native", [], 0, root=tmp_path)


def test_prepare_rejects_unknown_domain_and_unpinned_binary(tmp_path: Path, monkeypatch):
    asset, binary = _setup(tmp_path)
    monkeypatch.setattr(domain_research, "PAQ_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="pinned PAQ"):
        domain_research.prepare(asset, "molecular", "v", "native", [], 0, root=tmp_path)
    monkeypatch.setattr(domain_research, "PAQ_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="domain must"):
        domain_research.prepare(asset, "unknown", "v", "native", [], 0, root=tmp_path)


def test_physical_accounts_paid_json_metadata(tmp_path: Path):
    metadata = json.dumps({"variant": "v", "dictionary_bytes": 3}).encode()
    archive = tmp_path / "a.cixdom"
    archive.write_bytes(struct.pack(">8sBBQQI", b"CIXDOM01", 1, 2, 9, 7, len(metadata)) + metadata + b"payload")
    row = domain_research._physical(archive)
    assert row["header_bytes"] == 30
    assert row["metadata_bytes"] == len(metadata)
    assert row["payload_bytes"] == 7
    assert row["complete_bytes"] == 30 + len(metadata) + 7


def test_time_peak_is_separate_per_phase_and_moderate_budget_is_declared(tmp_path: Path, monkeypatch):
    asset, binary = _setup(tmp_path)
    monkeypatch.setattr(domain_research, "PAQ_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    cell = domain_research.prepare(asset, "molecular", "hydrogen_slots_v1", "native", [], 0, budget=600, root=tmp_path)
    manifest = json.loads(Path(cell["manifest_path"]).read_text())
    assert manifest["stage"] == "moderate_contiguous"
    assert manifest["longer_budget_justification"]
    encode, decode = tmp_path / "encode.time.txt", tmp_path / "decode.time.txt"
    encode.write_text("\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:02.50\n\tMaximum resident set size (kbytes): 123\n")
    decode.write_text("\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:02:03.45\n\tMaximum resident set size (kbytes): 456\n")
    assert domain_research._time_peak_kib(encode) == 123
    assert domain_research._time_peak_kib(decode) == 456
    assert domain_research._time_wall_seconds(encode) == 62.5
    assert domain_research._time_wall_seconds(decode) == 3723.45


def test_control_requires_raw_paq_variant_backend_and_full_identifiers(tmp_path: Path, monkeypatch):
    asset, binary = _setup(tmp_path)
    monkeypatch.setattr(domain_research, "PAQ_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    source = domain_research._asset(asset)
    archive, restored = tmp_path / "control.arc", tmp_path / "restored.bin"
    archive.write_bytes(b"complete"); restored.write_bytes(asset.read_bytes())
    configuration = {"domain": "molecular", "variant": "original", "backend": "paq",
                     "paq_binary_sha256": domain_research.PAQ_SHA256, "paq_options": domain_research.PAQ_OPTIONS,
                     "source_filename": "candidate.source.bin", "wrapper_magic": "CIXDOM01"}
    receipt = {"status": "VERIFIED_SCREENING", "identity": {"input": source, "configuration": configuration},
               "verification": {"matched": True}, "artifacts": {"archive": str(archive), "restored": str(restored)},
               "archive_bytes": len(b"complete"), "archive_sha256": hashlib.sha256(b"complete").hexdigest()}
    path = tmp_path / "control.json"; path.write_text(json.dumps(receipt))
    assert domain_research._control(path, source, "molecular")["configuration"]["variant"] == "original"
    receipt["identity"]["configuration"]["backend"] = "native"; path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="pinned original-byte PAQ"):
        domain_research._control(path, source, "molecular")
