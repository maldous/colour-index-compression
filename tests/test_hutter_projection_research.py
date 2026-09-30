import hashlib
import json
import struct
from pathlib import Path

import pytest

from benchmarks.hutter_projection_research import _control, _source


def test_source_and_paq_control_require_exact_rehashed_identity(tmp_path: Path):
    source_path = tmp_path / "input.bin"; source_path.write_bytes(b"abcdefgh")
    source = {"path": str(source_path), "offset": 2, "length": 4,
              "sha256": hashlib.sha256(b"cdef").hexdigest(), "dataset_sha256": "d" * 64}
    actual = _source(source)
    archive, restored = tmp_path / "a.bin", tmp_path / "r.bin"
    metadata=b"{}"; archive.write_bytes(struct.pack(">8sBQQI", b"CIXSTR1\0", 0, 4, 4, len(metadata)) + metadata + b"paq8px")
    restored.write_bytes(b"cdef")
    frozen={"mode":"original","paq_binary_sha256":"a" * 64,"paq_options":"-4","source_filename":"candidate.source.bin"}
    receipt = {"status":"VERIFIED_SCREENING", "identity":{"input":actual,"initial_state":"empty model state","configuration":{
        **frozen}},
        "verification":{"matched":True,"source_sha256":actual["sha256"],"restored_sha256":actual["sha256"]},
        "artifacts":{"archive":str(archive),"restored":str(restored)}, "archive_bytes":archive.stat().st_size,
        "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest()}
    receipt_path=tmp_path / "receipt.json"; receipt_path.write_text(json.dumps(receipt))
    assert _control(receipt_path, actual, frozen)["archive_bytes"] == archive.stat().st_size
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="incomplete|rehash"):
        _control(receipt_path, actual, frozen)
