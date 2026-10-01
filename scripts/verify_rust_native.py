#!/usr/bin/env python3
"""Cross-verify the bounded native CIXG1 routes against the frozen Python oracle."""
from __future__ import annotations
import hashlib
import json
import os
import random
import struct
import subprocess
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get("CIX_NATIVE_BIN", ROOT / "rust/cix-native/target/release"))
sys.path.insert(0, str(ROOT))

def run(*args: str, input: bytes | None = None, ok: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ok and p.returncode:
        raise AssertionError(f"command failed ({p.returncode}): {args}\n{p.stderr.decode(errors='replace')}")
    if not ok and p.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {args}")
    return p

def main() -> None:
    subprocess.run(["cargo", "build", "--release", "--manifest-path", str(ROOT / "rust/cix-native/Cargo.toml")], check=True)
    from cix.pipeline import encode_file, decode_file, _count_range, route_encode
    rng = random.Random(92341)
    fixtures = {
        "empty": b"",
        "tiny": b"CIX\0\xff",
        "random": rng.randbytes(50_000),
        "repetitive": b"xyz123" * 9_000,
        "mixed": (b"header\n" + rng.randbytes(2048) + b"\0" * 500 + b"footer\n") * 8,
    }
    rows = []
    with tempfile.TemporaryDirectory(prefix="cix-native-verify-") as td:
        d = Path(td)
        for name, data in fixtures.items():
            source = d / f"{name}.bin"; source.write_bytes(data)
            for route in ("raw", "runs", "composition", "lz", "predictor", "bwt", "stride", "phrases", "ppm", "deflate"):
                route_data = data[:1024] if route == "ppm" else data
                route_source = d / f"{name}.{route}.input"; route_source.write_bytes(route_data)
                py_archive = d / f"{name}.python-{route}.cix"
                backend = "hybrid" if route in ("lz", "predictor", "bwt", "stride", "phrases") else "deflate"
                encode_file(route_source, py_archive, effort="fast", backend=backend, force=route, block_bytes=32768)
                rust_restore = d / f"{name}.rust-{route}.bin"
                run(str(BIN / "uncix"), "-f", "-o", str(rust_restore), str(py_archive))
                assert rust_restore.read_bytes() == route_data
                if route == "ppm" and route_data:
                    run(str(BIN / "uncix"), "--memory", "16MiB", "-c", str(py_archive), ok=False)
                if name == "repetitive" and route == "deflate":
                    malformed = bytearray(py_archive.read_bytes())
                    payload_end = 13 + 41 + int.from_bytes(malformed[18:22], "little")
                    malformed[18:22] = (int.from_bytes(malformed[18:22], "little") + 1).to_bytes(4, "little")
                    malformed[payload_end:payload_end] = b"X"
                    trailing = d / "trailing-deflate.cix"; trailing.write_bytes(malformed)
                    run(str(BIN / "uncix"), "-c", str(trailing), ok=False)

                rust_archive = d / f"{name}.rust-{route}.cix"
                run(str(BIN / "cix"), "--route", route, "-f", "--block", "32768", str(route_source))
                generated = route_source.with_name(route_source.name + ".cix")
                generated.rename(rust_archive)
                assert rust_archive.read_bytes() == py_archive.read_bytes(), (name, route, "not canonical")
                py_restore = d / f"{name}.python-restore-{route}.bin"
                decode_file(rust_archive, py_restore)
                assert py_restore.read_bytes() == route_data
                rows.append({"fixture": name, "route": route, "source_bytes": len(route_data),
                    "source_sha256": hashlib.sha256(route_data).hexdigest(),
                    "archive_bytes": rust_archive.stat().st_size,
                    "archive_sha256": hashlib.sha256(rust_archive.read_bytes()).hexdigest(),
                    "canonical_equal": True, "cross_decode": True})
        # Exercise the generic pipeline's adaptive-range backend explicitly.
        range_data = (fixtures["mixed"] * 2)[:4096]
        range_src = d / "adaptive.input"; range_src.write_bytes(range_data)
        range_py = d / "adaptive.python.cix"
        encode_file(range_src, range_py, effort="fast", backend="range", force="predictor", block_bytes=32768)
        run(str(BIN / "cix"), "--route", "predictor", "--backend", "range", "-f", "--block", "32768", str(range_src))
        range_rust = range_src.with_name(range_src.name + ".cix")
        assert range_rust.read_bytes() == range_py.read_bytes(), "adaptive-range bytes differ from Python"
        assert run(str(BIN / "cixcat"), "-", input=range_rust.read_bytes()).stdout == range_data
        rows.append({"fixture": "mixed-adaptive-range", "route": "predictor", "coder": "adaptive-range", "source_bytes": len(range_data), "canonical_equal": True, "cross_decode": True})
        count_py = d / "count-range.python.cix"
        encode_file(range_src, count_py, effort="fast", backend="count-range", force="predictor", block_bytes=32768)
        run(str(BIN / "cix"), "--route", "predictor", "--backend", "count-range", "-f", "--block", "32768", str(range_src))
        count_rust = range_src.with_name(range_src.name + ".cix")
        assert count_rust.read_bytes() == count_py.read_bytes(), "count-range bytes differ from Python"
        assert run(str(BIN / "cixcat"), "-", input=count_rust.read_bytes()).stdout == range_data
        rows.append({"fixture": "mixed-count-range", "route": "predictor", "coder": "count-range", "source_bytes": len(range_data), "canonical_equal": True, "cross_decode": True})
        mix_data = (b"ABCD" * 1024)
        mix_src = d / "mixture.input"; mix_src.write_bytes(mix_data)
        mix_py = d / "mixture.python.cix"
        mix_payload = route_encode("mixture", mix_data, "deflate")
        mix_hash = hashlib.sha256(mix_data).digest()
        mix_py.write_bytes(struct.pack("<5sII", b"CIXG1", 32768, 0)
            + struct.pack("<BII32s", 9, len(mix_data), len(mix_payload), mix_hash) + mix_payload
            + struct.pack("<BII32s", 255, 0, 0, mix_hash))
        run(str(BIN / "cix"), "--route", "mixture", "-f", "--block", "32768", str(mix_src))
        mix_rust = mix_src.with_name(mix_src.name + ".cix")
        assert mix_rust.read_bytes() == mix_py.read_bytes(), "mixture bytes differ from Python"
        assert run(str(BIN / "cixcat"), "-", input=mix_rust.read_bytes()).stdout == mix_data
        rows.append({"fixture": "mixed-fixed-mixer", "route": "mixture", "source_bytes": len(mix_data), "canonical_equal": True, "cross_decode": True})
        src = d / "pipe.bin"
        encoded = run(str(BIN / "cix"), "-c", "-", input=b"pipe input\0" * 100).stdout
        restored = run(str(BIN / "cixcat"), "-", input=encoded).stdout
        assert restored == b"pipe input\0" * 100
        archive = d / "pipe.cix"; archive.write_bytes(encoded)
        run(str(BIN / "uncix"), "-t", str(archive))
        run(str(BIN / "uncix"), "-l", str(archive))
        run(str(BIN / "cix"), "--route", "lz", "--memory", "4MiB", "-c", "-", input=b"abcd" * 100, ok=False)
        run(str(BIN / "cix"), "--route", "ppm", "--memory", "16MiB", "-c", "-", input=b"abcd" * 100, ok=False)
        range_data = (b"same-count arithmetic route\0" * 180)[:4096]
        range_cix = _count_range(range_data)
        range_payload = bytes((1,)) + struct.pack("<BII", 5, len(range_data), len(range_cix)) + range_cix
        digest = hashlib.sha256(range_data).digest()
        range_archive = d / "count-range.cix"
        range_archive.write_bytes(
            struct.pack("<5sII", b"CIXG1", len(range_data), 0)
            + struct.pack("<BII32s", 2, len(range_data), len(range_payload), digest)
            + range_payload
            + struct.pack("<BII32s", 255, 0, 0, digest)
        )
        assert run(str(BIN / "cixcat"), "-", input=range_archive.read_bytes()).stdout == range_data
        out = d / "existing"; out.write_bytes(b"keep me")
        run(str(BIN / "uncix"), "-o", str(out), str(archive), ok=False)
        assert out.read_bytes() == b"keep me"
        for malformed in (encoded[:-1], encoded[:13] + bytes([0]) + encoded[14:]):
            bad = d / "bad.cix"; bad.write_bytes(malformed)
            run(str(BIN / "uncix"), "-c", str(bad), ok=False)
        # Ensure an ordinary input remains intact after compression.
        src.write_bytes(b"retained")
        run(str(BIN / "cix"), "-f", str(src))
        assert src.read_bytes() == b"retained"
    (ROOT / "docs/research/2026-10-01-rust-native/fixtures.json").write_text(json.dumps({
        "reference_commit": "80b95427725ecf59d626b2982d50f6349abd56e1",
        "python_zlib_version": __import__("zlib").ZLIB_VERSION,
        "rust_binary_profile": "release-lto" if "release-lto" in str(BIN) else "release",
        "fixtures": rows,
        "performance_evidence": False,
    }, indent=2) + "\n")
    print(f"verified {len(rows)} cross-decoded canonical route fixtures plus streaming, integrity and overwrite checks")

if __name__ == "__main__": main()
