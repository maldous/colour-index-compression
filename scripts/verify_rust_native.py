#!/usr/bin/env python3
"""Cross-verify the bounded native CIXG1 routes against the frozen Python oracle."""
from __future__ import annotations
import hashlib
import json
import os
import random
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
    from cix.pipeline import encode_file, decode_file
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
            for route in ("raw", "runs", "deflate"):
                py_archive = d / f"{name}.python-{route}.cix"
                encode_file(source, py_archive, effort="fast", backend="deflate", force=route, block_bytes=32768)
                rust_restore = d / f"{name}.rust-{route}.bin"
                run(str(BIN / "uncix"), "-f", "-o", str(rust_restore), str(py_archive))
                assert rust_restore.read_bytes() == data
                if name == "repetitive" and route == "deflate":
                    malformed = bytearray(py_archive.read_bytes())
                    payload_end = 13 + 41 + int.from_bytes(malformed[18:22], "little")
                    malformed[18:22] = (int.from_bytes(malformed[18:22], "little") + 1).to_bytes(4, "little")
                    malformed[payload_end:payload_end] = b"X"
                    trailing = d / "trailing-deflate.cix"; trailing.write_bytes(malformed)
                    run(str(BIN / "uncix"), "-c", str(trailing), ok=False)

                rust_archive = d / f"{name}.rust-{route}.cix"
                run(str(BIN / "cix"), "--route", route, "-f", "--block", "32768", str(source))
                generated = source.with_name(source.name + ".cix")
                generated.rename(rust_archive)
                assert rust_archive.read_bytes() == py_archive.read_bytes(), (name, route, "not canonical")
                py_restore = d / f"{name}.python-restore-{route}.bin"
                decode_file(rust_archive, py_restore)
                assert py_restore.read_bytes() == data
                rows.append({"fixture": name, "route": route, "source_bytes": len(data),
                    "source_sha256": hashlib.sha256(data).hexdigest(),
                    "archive_bytes": rust_archive.stat().st_size,
                    "archive_sha256": hashlib.sha256(rust_archive.read_bytes()).hexdigest(),
                    "canonical_equal": True, "cross_decode": True})
        src = d / "pipe.bin"
        encoded = run(str(BIN / "cix"), "-c", "-", input=b"pipe input\0" * 100).stdout
        restored = run(str(BIN / "cixcat"), "-", input=encoded).stdout
        assert restored == b"pipe input\0" * 100
        archive = d / "pipe.cix"; archive.write_bytes(encoded)
        run(str(BIN / "uncix"), "-t", str(archive))
        run(str(BIN / "uncix"), "-l", str(archive))
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
