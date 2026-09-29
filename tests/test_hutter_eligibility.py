import hashlib
from pathlib import Path

from benchmarks import hutter_eligibility as gate


def _file(path: Path, payload: bytes) -> dict:
    path.write_bytes(payload)
    return {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest()}


def _json(path: Path, value: dict) -> dict:
    import json
    return _file(path, json.dumps(value, sort_keys=True).encode())


def _manifest(tmp_path: Path, *, same_binary: bool = False) -> dict:
    encoder = _file(tmp_path / "encoder.zip", b"encoder")
    decoder = encoder if same_binary else _file(tmp_path / "decoder.zip", b"decoder")
    archive = _file(tmp_path / "archive.cix", b"archive")
    source = tmp_path / "source"
    source.mkdir()
    for name in ("LICENSE", "DEPENDENCIES", "USAGE", "ALGORITHM"):
        (source / name).write_text(name)
    result = {
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
    hashes = {name: result["artifacts"][name]["sha256"] for name in ("compressor", "decompressor", "archive")}
    common = {"completed": True, "exit_code": 0, "input_sha256": None, "input_bytes": gate.ENWIK9_BYTES,
              "compressor_sha256": hashes["compressor"], "decompressor_sha256": hashes["decompressor"],
              "archive_sha256": hashes["archive"]}
    documentation_hashes = {field: hashlib.sha256((source / filename).read_bytes()).hexdigest()
                            for field, filename in {"root_license_path": "LICENSE", "dependency_license_manifest_path": "DEPENDENCIES",
                                                    "usage_document_path": "USAGE", "algorithm_document_path": "ALGORITHM"}.items()}
    result["evidence"] = {"encode": _json(tmp_path / "encode.json", {**common, "measurement": result["measurements"]["compression"]}),
                          "decode": _json(tmp_path / "decode.json", {**common, "measurement": result["measurements"]["decompression"]}),
                          "restored": _file(tmp_path / "restored", b"canonical"),
                          "packaging_review": _json(tmp_path / "review.json", {
                              "offline_execution_verified": True, "public_source_access_verified": True,
                              "osi_license_verified": True, "license_completeness_verified": True,
                              "offline_execution_audit": "local audit receipt v1", "public_source_access_audit": "public URL audit v1",
                              "public_source_url": result["packaging"]["public_source_url"], "artifact_hashes": hashes,
                              "documentation_hashes": documentation_hashes})}
    return result


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
    for key in ("encode", "decode"):
        record = Path(manifest["evidence"][key]["path"])
        import json
        payload = json.loads(record.read_text())
        payload["input_sha256"] = gate.ENWIK9_SHA256
        payload["input_bytes"] = gate.ENWIK9_BYTES
        if key == "decode":
            payload.update(restored_sha256=gate.ENWIK9_SHA256, restored_bytes=len(b"canonical"))
        manifest["evidence"][key] = _json(record, payload)
    result = gate.evaluate(manifest)
    assert result["status"] == "LOCAL_ELIGIBILITY_CANDIDATE"
    assert result["official_approval"] is False


def test_decode_receipt_must_be_bound_to_archive_and_restore(tmp_path):
    manifest = _manifest(tmp_path)
    import json
    record = Path(manifest["evidence"]["decode"]["path"])
    payload = json.loads(record.read_text())
    payload["archive_sha256"] = "0" * 64
    manifest["evidence"]["decode"] = _json(record, payload)
    result = gate.evaluate(manifest, verify_input=False)
    assert any("evidence.decode: archive_sha256" in failure for failure in result["failures"])
    assert any("evidence.restored" in failure for failure in result["failures"])


def test_nonfinite_or_invalid_resource_numbers_fail(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["measurements"]["compression"]["wall_seconds"] = float("nan")
    manifest["measurements"]["decompression"]["peak_temp_bytes"] = -1
    result = gate.evaluate(manifest, verify_input=False)
    assert any("wall time" in failure for failure in result["failures"])
    assert any("temporary disk must" in failure for failure in result["failures"])


def test_zero_rss_and_unbound_packaging_review_fail(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["measurements"]["compression"]["peak_process_tree_rss_bytes"] = 0
    manifest["evidence"]["packaging_review"]["sha256"] = "0" * 64
    result = gate.evaluate(manifest, verify_input=False)
    assert any("RSS must be a positive" in failure for failure in result["failures"])
    assert any("packaging_review: SHA-256" in failure for failure in result["failures"])


def test_exact_time_limit_and_boolean_numeric_fields_fail(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["measurements"]["compression"].update(wall_seconds=70_000 * 3600 / 1000, geekbench5_single_core=1000)
    manifest["measurements"]["decompression"].update(wall_seconds=True, cpu_cores=True)
    result = gate.evaluate(manifest, verify_input=False)
    assert any("strict 70,000/T" in failure for failure in result["failures"])
    assert any("numeric, not strings or booleans" in failure for failure in result["failures"])
    assert any("one CPU core" in failure for failure in result["failures"])
