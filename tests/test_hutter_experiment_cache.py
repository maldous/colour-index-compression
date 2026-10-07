import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from benchmarks.hutter_experiment_cache import Cache, CacheCorruption, CacheMiss


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt(tmp_path: Path, *, status="VERIFIED_SCREENING", config=None) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = b"exact input bytes"
    archive, restored = tmp_path / "archive.bin", tmp_path / "restored.bin"
    archive.write_bytes(b"complete physical archive")
    restored.write_bytes(source)
    row = {
        "status": status,
        "identity": {
            "input": {"path": "/input", "offset": 4, "length": len(source), "sha256": sha(source)},
            "configuration": config or {"mode": "raw", "options": ["-4"]},
            "build_sha256": {"codec.py": "a" * 64, "decoder.py": "b" * 64},
            "core": {"decoder_order": "causal"},
            "initial_state": "empty",
            "manifest_sha256": "c" * 64,
        },
        "verification": {"matched": True, "source_sha256": sha(source), "restored_sha256": sha(source)},
        "independent_decode": "archive-only decoder received no original input",
        "artifacts": {"archive": str(archive), "restored": str(restored)},
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha(archive.read_bytes()),
    }
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(row))
    return path


def preproc_spec(source: bytes) -> dict:
    return {
        "kind": "reversible_structure_frame",
        "input": {"path": "/input", "offset": 0, "length": len(source), "sha256": sha(source)},
        "source_hashes": {"transform.py": "d" * 64, "decoder.py": "e" * 64},
        "configuration": {"mode": "body-v1", "rule_limit": 512},
        "verification": {"matched": True, "source_sha256": sha(source), "restored_sha256": sha(source)},
        "independent_decode_evidence": "caller ran archive-only decoder in a separate process",
        "verification_source": "caller_attested",
    }


def test_control_rehashes_and_reuses_exact_immutable_identity(tmp_path: Path):
    cache = Cache(tmp_path / "cache")
    path = receipt(tmp_path)
    key = cache.put_control(path)
    record = cache.get_control(key)
    assert record["archive_bytes"] == len(b"complete physical archive")
    assert record["verification_level"] == "bounded_receipt_independent_archive_only"
    assert cache.put_control(path) == key
    with pytest.raises(CacheMiss):
        cache.get_control("0" * 64)


def test_control_rejects_unverified_config_difference_and_artifact_tamper(tmp_path: Path):
    cache = Cache(tmp_path / "cache")
    failed = receipt(tmp_path / "failed", status="SIZE_REJECTED_UNVERIFIED")
    with pytest.raises(CacheCorruption, match="VERIFIED_SCREENING"):
        cache.put_control(failed)
    first = receipt(tmp_path / "first")
    second = receipt(tmp_path / "second", config={"mode": "raw", "options": ["-5"]})
    assert cache.put_control(first) != cache.put_control(second)
    key = cache.put_control(first)
    (tmp_path / "first" / "archive.bin").write_bytes(b"tampered")
    with pytest.raises(CacheCorruption, match="archive"):
        cache.get_control(key)


def test_preprocessing_rehashes_and_forbids_prediction_trace(tmp_path: Path):
    source = b"preprocessing exact source"
    artifact, restored = tmp_path / "frame.bin", tmp_path / "restored.bin"
    artifact.write_bytes(b"self-contained frame")
    restored.write_bytes(source)
    cache = Cache(tmp_path / "cache")
    spec = preproc_spec(source)
    key = cache.put_preprocessing(spec, artifact, restored)
    record = cache.get_preprocessing(key)
    assert record["verification_level"] == "caller_attested_not_independently_reexecuted_by_cache"
    artifact.write_bytes(b"changed")
    with pytest.raises(CacheCorruption, match="artifact"):
        cache.get_preprocessing(key)
    spec["kind"] = "prediction_trace"
    with pytest.raises(CacheCorruption, match="forbidden"):
        cache.put_preprocessing(spec, artifact, restored)


def test_unrelated_verified_archive_cannot_certify_preprocessing(tmp_path):
    proof = receipt(tmp_path / "proof")
    source = b"exact input bytes"
    spec = preproc_spec(source)
    spec["input"]["offset"] = 4
    spec["verification_source"] = "bounded_receipt"
    spec["verification_receipt"] = str(proof)
    artifact, restored = tmp_path / "other-frame", tmp_path / "other-restored"
    artifact.write_bytes(b"unverified different frame")
    restored.write_bytes(source)
    with pytest.raises(CacheCorruption, match="this exact input and artifact"):
        Cache(tmp_path / "cache").put_preprocessing(spec, artifact, restored)


def test_concurrent_cache_insertions_are_not_lost(tmp_path):
    receipts = [receipt(tmp_path / str(i), config={"mode": "raw", "trial": i}) for i in range(8)]
    cache = Cache(tmp_path / "cache")
    with ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(cache.put_control, receipts))
    assert len(set(keys)) == 8
    assert all(cache.get_control(key)["archive_bytes"] > 0 for key in keys)
