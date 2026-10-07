import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from benchmarks import competitive_codec
from benchmarks import domain_probe as probe


class _Dummy:
    @staticmethod
    def encode(data, variant):
        if variant != "reverse-v1":
            raise ValueError("unknown dummy variant")
        return b"D" + data[::-1]

    @staticmethod
    def decode(frame):
        if not frame.startswith(b"D"):
            raise ValueError("invalid dummy frame")
        return frame[1:][::-1]


def _binary():
    path = competitive_codec.paq_binary("v216")
    return path, hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_dummy_adapter_paq_frame_is_self_describing(monkeypatch, tmp_path):
    monkeypatch.setattr(probe, "DOMAINS", {"dummy": (99, _Dummy)})
    monkeypatch.setattr(probe, "BY_CODE", {99: ("dummy", _Dummy)})
    binary, digest = _binary()
    source = b"independent domain adapter test" * 20
    frame, report = probe.encode(source, domain="dummy", variant="reverse-v1", backend="paq",
                                 paq_binary_path=binary, paq_sha256=digest, temporary=tmp_path / "work")
    assert report["round_trip"] == "not_verified_by_encoder"
    assert probe.decode(frame, paq_binary_path=binary, paq_sha256=digest, temporary=tmp_path / "decode") == source
    domain, _adapter, backend, original, transformed, metadata, payload = probe._parse(frame)
    assert domain == "dummy" and backend == probe.PAQ and original == len(source)
    assert transformed == len(b"D" + source[::-1]) and len(payload) > 9
    assert probe._read_meta(metadata)["variant"] == "reverse-v1"


def test_rejects_native_except_compressed_volume_and_bad_binary(tmp_path):
    binary, digest = _binary()
    with pytest.raises(ValueError, match="native backend"):
        probe.encode(b"x", domain="molecular", variant="original", backend="native",
                     paq_binary_path=binary, paq_sha256=digest, temporary=tmp_path / "work")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        probe.encode(b"x", domain="molecular", variant="original", backend="paq",
                     paq_binary_path=binary, paq_sha256="0" * 64, temporary=tmp_path / "work2")


def _snapshot(tmp_path, *, include_adapter=True):
    root = tmp_path / "snapshot"
    (root / "benchmarks").mkdir(parents=True)
    (root / "cix").mkdir()
    shutil.copy2(probe.__file__, root / "benchmarks" / "domain_probe.py")
    (root / "cix" / "__init__.py").write_text("SNAPSHOT = True\n")
    if include_adapter:
        (root / "benchmarks" / "domain_volume.py").write_text(
            "def encode(data, variant):\n"
            "    if variant != 'jxl-planar3-e10': raise ValueError('bad variant')\n"
            "    return b'S' + data\n"
            "def decode(frame):\n"
            "    if not frame.startswith(b'S'): raise ValueError('bad frame')\n"
            "    return frame[1:]\n"
        )
    return root


def test_direct_snapshot_bootstrap_uses_copied_adapter_not_live_repo(tmp_path):
    root = _snapshot(tmp_path)
    source, archive, restored, binary = (tmp_path / "input", tmp_path / "archive", tmp_path / "restored", tmp_path / "binary")
    source.write_bytes(b"snapshot-only adapter proof")
    binary.write_bytes(b"not executed for native backend")
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    command = [sys.executable, str(root / "benchmarks" / "domain_probe.py"), "encode", str(source), str(archive),
               "--domain", "volume", "--variant", "jxl-planar3-e10", "--backend", "native",
               "--paq-binary", str(binary), "--paq-sha256", digest, "--snapshot-root", str(root)]
    encoded = json.loads(subprocess.check_output(command, text=True))
    assert encoded["snapshot_dependencies"]["benchmarks.domain_volume"]["path"] == "benchmarks/domain_volume.py"
    assert encoded["snapshot_dependencies"]["cix"]["path"] == "cix/__init__.py"
    decoded = json.loads(subprocess.check_output([sys.executable, str(root / "benchmarks" / "domain_probe.py"), "decode", str(archive), str(restored),
        "--paq-binary", str(binary), "--paq-sha256", digest, "--snapshot-root", str(root)], text=True))
    assert decoded["snapshot_dependencies"]["benchmarks.domain_volume"]["path"] == "benchmarks/domain_volume.py"
    assert restored.read_bytes() == source.read_bytes()


def test_snapshot_missing_adapter_cannot_fall_back_to_live_repo(tmp_path):
    root = _snapshot(tmp_path, include_adapter=False)
    source, archive, binary = tmp_path / "input", tmp_path / "archive", tmp_path / "binary"
    source.write_bytes(b"must not use live domain_volume")
    binary.write_bytes(b"not executed for native backend")
    failed = subprocess.run([sys.executable, str(root / "benchmarks" / "domain_probe.py"), "encode", str(source), str(archive),
        "--domain", "volume", "--variant", "jxl-planar3-e10", "--backend", "native", "--paq-binary", str(binary),
        "--paq-sha256", hashlib.sha256(binary.read_bytes()).hexdigest(), "--snapshot-root", str(root)], text=True, capture_output=True)
    assert failed.returncode != 0
    assert "No module named" in failed.stderr
