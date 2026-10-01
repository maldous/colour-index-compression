#!/usr/bin/env python3
"""Verify canonical Rust CIXM6 mode-11/12 payloads against the frozen Python codecs."""

from __future__ import annotations

import os
import random
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
FIXTURE = ROOT / "rust/cix-native/target/release/sparse_runs_fixture"
BIN = Path(os.environ.get("CIX_NATIVE_BIN", ROOT / "rust/cix-native/target/release"))


def run(*args: str, input: bytes = b"", ok: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ok and result.returncode:
        raise AssertionError(f"{args}: {result.stderr.decode(errors='replace')}")
    if not ok and not result.returncode:
        raise AssertionError(f"unexpected success: {args}")
    return result


def vencode(value: int) -> bytes:
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def archive(mode: int, source: bytes, payload: bytes) -> bytes:
    return (
        b"CIXM6"
        + vencode(max(1 << 20, len(source)))
        + bytes((mode,))
        + vencode(len(source))
        + vencode(len(payload))
        + payload
        + bytes((255,))
        + vencode(len(source))
        + struct.pack("<I", zlib.crc32(source))
    )


def main() -> None:
    subprocess.run(
        ["cargo", "build", "--release", "--bin", "sparse_runs_fixture", "--manifest-path", str(MANIFEST)],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.multinomial import decompress
    from cix.runs import decode_run_block, encode_run_block
    from cix.sparse import decode_sparse_block, encode_sparse_block

    rng = random.Random(0xC1_11_12)
    sparse_cases = [
        (b"Z", True),
        (b"\0" * 257, True),
        (bytes(range(256)), True),
        (bytes([7, 9, 7, 9]), True),  # dominant tie selects the lowest byte.
        (bytes([0]) * 8192, True),
        (bytes(1 if index in {0, 127, 128, 4095, 8191} else 0 for index in range(8192)), True),
        (bytes(rng.randrange(8) for _ in range(3072)), True),
    ]
    run_cases = [
        (b"Q", True),
        (b"A" * 16385, True),
        (bytes(range(256)), True),
        (b"A" * 128 + b"B" + b"C" * 129 + b"D" * 16384, True),
        (bytes([index & 1 for index in range(10001)]), True),
        (b"".join(bytes((index & 255,)) * (1 + (index * 73) % 4096) for index in range(400)), True),
        # These two force distinct local integer class models, including nested
        # context mode 3 and wavelet mode 4.
        (b"".join(bytes((index & 255,)) * (1 + (index & 1) * 255) for index in range(3000)), True),
        (b"".join(bytes((index & 3,)) * (1 << (index % 16)) for index in range(128)), True),
    ]

    checked = 0
    for mode, cases, py_encode, py_decode, command in (
        (11, sparse_cases, encode_sparse_block, decode_sparse_block, "sparse"),
        (12, run_cases, encode_run_block, decode_run_block, "runs"),
    ):
        for source, rust_decodable in cases:
            expected, _ = py_encode(source)
            actual = run(str(FIXTURE), command, input=source).stdout
            assert actual == expected, (mode, len(source), len(actual), len(expected))
            assert py_decode(actual, source_length=len(source)) == source
            packed = archive(mode, source, actual)
            assert decompress(packed) == source
            native = run(str(BIN / "uncix"), "-c", "-", input=packed, ok=rust_decodable)
            assert native.stdout == source
            checked += 1

    for command in ("sparse", "runs"):
        failed = run(str(FIXTURE), command, input=b"", ok=False)
        assert b"empty" in failed.stderr

    print(
        f"verified {checked} canonical Rust/Python sparse/run payloads, Python and Rust decoding, "
        "empty rejection, dominant ties, long runs, local integer models, and combinatorial ranks"
    )


if __name__ == "__main__":
    main()
