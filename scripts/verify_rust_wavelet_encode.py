#!/usr/bin/env python3
"""Verify native CIXM6 mode-18 encoding against the frozen Python codec."""
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
        "CIX_WAVELET_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/wavelet_fixture",
    )
)


def native(data: bytes, *args: str) -> bytes:
    result = subprocess.run(
        [str(BIN), *args], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE
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
            "wavelet_fixture",
            "--manifest-path",
            str(MANIFEST),
            "-j",
            "4",
        ],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.wavelet import decode_wavelet, encode_wavelet

    rng = random.Random(18018)
    cases = [
        b"",
        b"\x00",
        b"\xff",
        b"\x00\xff",
        bytes(range(256)),
        b"hierarchical colour index " * 400,
        bytes(index & 7 for index in range(16_385)),
        bytes(rng.choices(range(16), weights=range(16, 0, -1), k=32_768)),
        rng.randbytes(65_536),
    ]
    for data in cases:
        expected = encode_wavelet(data)
        actual = native(data)
        assert actual == expected, (len(data), len(actual), len(expected))
        assert decode_wavelet(actual, source_length=len(data)) == data
        assert native(expected, "--decode", str(len(data))) == data

    print(
        "verified canonical Python-identical CIXM6 mode-18 bytes and exact "
        "Python/Rust cross-decoding for empty, tiny, complete-alphabet, repetitive, "
        "low-alphabet, skewed, and 64-KiB random fixtures"
    )


if __name__ == "__main__":
    main()
