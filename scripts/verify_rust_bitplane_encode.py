#!/usr/bin/env python3
"""Verify native CIXM6 mode-6 encoding against the frozen Python codec."""
from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
BIN = Path(
    os.environ.get(
        "CIX_BITPLANE_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/bitplane_fixture",
    )
)


def native_encode(data: bytes) -> bytes:
    result = subprocess.run(
        [str(BIN)], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    return result.stdout


def native_decode(payload: bytes, source_length: int) -> bytes:
    result = subprocess.run(
        [str(BIN), "--decode", str(source_length)],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    return result.stdout


def main() -> None:
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--example",
            "bitplane_fixture",
            "--manifest-path",
            str(MANIFEST),
            "-j",
            "4",
        ],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.bitplanes import decode_bitplanes, encode_bitplanes

    rng = random.Random(6002)
    cases = [
        b"",
        b"\x00",
        b"\xff",
        b"\x00\xff",
        b"\x00\xff\x00\xff",
        bytes(range(256)),
        b"A" * 8193,
        bytes((index * 17 + index // 5) & 0xff for index in range(16_385)),
        rng.randbytes(65_536),
    ]
    for data in cases:
        expected, description = encode_bitplanes(data)
        actual = native_encode(data)
        assert description == "bitplane-enumerative-range"
        assert actual == expected, (len(data), len(actual), len(expected))
        assert decode_bitplanes(actual, source_length=len(data)) == data
        assert native_decode(expected, len(data)) == data

    print(
        "verified canonical Python-identical CIXM6 mode-6 bytes and Python decode "
        "for empty, tiny, tied-majority, exhaustive-byte, repetitive, patterned, "
        "and 64-KiB random fixtures"
    )


if __name__ == "__main__":
    main()
