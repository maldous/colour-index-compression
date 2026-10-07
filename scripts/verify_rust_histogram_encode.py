#!/usr/bin/env python3
"""Verify native CIXM6 mode-20 candidate and type-class encoding."""
from __future__ import annotations

import os
import random
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
BIN = Path(
    os.environ.get(
        "CIX_HISTOGRAM_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/histogram_fixture",
    )
)


def native(data: bytes, *args: str, ok: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        [str(BIN), *args], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("malformed histogram unexpectedly succeeded")
    return result


def unpack_counts(blob: bytes) -> list[int]:
    assert len(blob) == 256 * 8
    return list(struct.unpack("<256Q", blob))


def main() -> None:
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--example",
            "histogram_fixture",
            "--manifest-path",
            str(MANIFEST),
            "-j",
            "2",
        ],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.histogram import (
        decode,
        decode_type_class,
        encode_best,
        encode_candidates,
        type_class_candidate,
    )
    from cix.multinomial import encode_type_class_known_n

    rng = random.Random(20020)
    count_cases = [
        b"\x00",
        b"\x00" * 31 + b"\xff" * 7,
        bytes(range(256)),
        bytes(range(256)) * 8,
        bytes(rng.choices(range(16), weights=range(16, 0, -1), k=12_000)),
        rng.randbytes(24_000),
    ]
    mode_by_name = {
        "active-uint": 0,
        "active-delta": 1,
        "dense-uint": 2,
        "dense-delta": 3,
        "active-centered": 4,
        "dense-centered": 5,
    }
    for data in count_cases:
        counts = [0] * 256
        for value in data:
            counts[value] += 1
        candidates = encode_candidates(counts)
        for name, expected in candidates.items():
            actual = native(
                data, "--candidate-mode", str(mode_by_name[name])
            ).stdout
            assert actual == expected, (name, len(data), len(actual), len(expected))
            assert decode(actual, total=len(data)) == counts
            decoded = native(
                expected, "--decode-counts", str(len(data))
            ).stdout
            assert unpack_counts(decoded) == counts
        expected, expected_name = encode_best(counts)
        actual = native(data, "--best").stdout
        assert actual == expected
        assert actual[1] == mode_by_name[expected_name]

    native(b"", "--best", ok=False)

    type_class_cases = [
        b"tiny",
        b"A" * 4096,
        bytes(range(256)) * 32,
        bytes(rng.choices(range(256), weights=range(256, 0, -1), k=16_384)),
        rng.randbytes(16_384),
    ]
    for data in type_class_cases:
        incumbent = encode_type_class_known_n(data)
        expected = type_class_candidate(data, incumbent)
        result = native(data, "--type-class-candidate", ok=expected is not None)
        if expected is None:
            continue
        assert result.stdout == expected
        assert decode_type_class(result.stdout, len(data)) == data
        assert native(
            expected, "--decode-type-class", str(len(data))
        ).stdout == data

    malformed_counts = [
        b"",
        b"\x02\x00\x01\x00",
        b"\x01\x09",
        b"\x01\x00",
        b"\x01\x00\x00",
        b"\x01\x00\x02",
        b"\x01\x00\x01",
        b"\x01\x01\x02\x00\x00",
    ]
    for payload in malformed_counts:
        native(payload, "--decode-counts", "1", ok=False)

    valid_data = bytes(range(256)) * 32
    valid_incumbent = encode_type_class_known_n(valid_data)
    valid = type_class_candidate(valid_data, valid_incumbent)
    assert valid is not None
    for payload in (b"", b"\x80", b"\xff\x01", valid[:-1]):
        native(payload, "--decode-type-class", str(len(valid_data)), ok=False)

    print(
        "verified all six Python-identical mode-20 count candidates, canonical "
        "best selection, mode-20 eligibility, Python/Rust cross-decode, singleton/"
        "dense/skewed/random counts, and malformed rejection"
    )


if __name__ == "__main__":
    main()
