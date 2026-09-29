import hashlib
from pathlib import Path

from benchmarks import hutter_eligibility as gate


def _file(path: Path, payload: bytes) -> dict:
    path.write_bytes(payload)
    return {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest()}


def _manifest(tmp_path: Path, *, same_binary: bool = False) -> dict:
    encoder = _file(tmp_path / "encoder.zip", b"encoder")
    decoder = encoder if same_binary else _file(tmp_path / "decoder.zip", b"decoder")
    archive = _file(tmp_path / "archive.cix", b"archive")
    source = tmp_path / "source"
    source.mkdir()
    for name in ("LICENSE", "DEPENDENCIES", "USAGE", "ALGORITHM"):
        (source / name).write_text(name)
    return {
        "schema_version": 1, "mode": "split",
        "input": {"path": str(tmp_path / "enwik9")},
        "artifacts": {"compressor": encoder, "decompressor": decoder, "archive": archive},
        "required_options": ["-9", "--decode"],
        "measurements": {stage: {"measurement_scope": "whole_enwik9_process_tree", "wall_seconds": 1,
                                   "peak_process_tree_rss_bytes": 1, "peak_temp_bytes": 1, "cpu_cores": 1,
                                   "gpu_used": False, "geekbench5_single_core": 1000}
                         for stage in ("compression", "decompression")},
        "packaging": {"offline_self_contained": True, "public_source_url": "https://example.test/cix",
                      "osi_license": "MIT", "source_root": str(source), "root_license_path": "LICENSE",
                      "dependency_license_manifest_path": "DEPENDENCIES", "usage_document_path": "USAGE",
                      "algorithm_document_path": "ALGORITHM"},
    }


def test_strict_integer_hurdle():
    assert gate.HURDLE_BYTES == 109_685_196
    assert gate.HURDLE_BYTES < 0.99 * gate.CURRENT_RECORD_BYTES
    assert gate.HURDLE_BYTES + 1 >= 0.99 * gate.CURRENT_RECORD_BYTES


def test_split_accounting_doubles_distinct_decoder(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path)
    result = gate.evaluate(manifest, verify_input=False)
    package = result["package"]
    assert package["decoder_multiplier"] == 2
    assert package["total_bytes"] == len(b"encoder") + 2 * len(b"decoder") + len(b"archive") + len(b"-9--decode")


def test_same_binary_still_counts_two_copies_total(tmp_path):
    manifest = _manifest(tmp_path, same_binary=True)
    result = gate.evaluate(manifest, verify_input=False)
    package = result["package"]
    assert package["decoder_multiplier"] == 1
    assert package["total_bytes"] == 2 * len(b"encoder") + len(b"archive") + len(b"-9--decode")


def test_wrong_enwik9_identity_fails_closed(tmp_path):
    manifest = _manifest(tmp_path)
    (tmp_path / "enwik9").write_bytes(b"not enwik9")
    result = gate.evaluate(manifest)
    assert result["status"] == "NOT_YET_QUALIFIED"
    assert any("not exactly" in failure for failure in result["failures"])
    assert any("not canonical" in failure for failure in result["failures"])


def test_resource_or_gpu_failure_is_visible(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["measurements"]["compression"]["gpu_used"] = True
    manifest["measurements"]["decompression"]["cpu_cores"] = 2
    result = gate.evaluate(manifest, verify_input=False)
    assert any("GPU" in failure for failure in result["failures"])
    assert any("one CPU core" in failure for failure in result["failures"])


def test_missing_license_evidence_fails(tmp_path):
    manifest = _manifest(tmp_path)
    (tmp_path / "source" / "LICENSE").unlink()
    result = gate.evaluate(manifest, verify_input=False)
    assert any("root_license_path" in failure for failure in result["failures"])


def test_local_candidate_never_claims_official_approval(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path, same_binary=True)
    input_path = tmp_path / "enwik9"
    input_path.write_bytes(b"canonical")
    monkeypatch.setattr(gate, "ENWIK9_BYTES", len(b"canonical"))
    monkeypatch.setattr(gate, "ENWIK9_SHA256", hashlib.sha256(b"canonical").hexdigest())
    result = gate.evaluate(manifest)
    assert result["status"] == "LOCAL_ELIGIBILITY_CANDIDATE"
    assert result["official_approval"] is False
