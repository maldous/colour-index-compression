#!/usr/bin/env python3
"""Verify canonical native CIXM6 mode-2 encoding against frozen Python."""
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
        "CIX_CONTEXT_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/context_fixture",
    )
)


def invoke(
    data: bytes,
    order: int,
    bucket_bits: int,
    prefix: bytes = b"",
    *,
    decode: bool = False,
    ok: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    envelope = struct.pack("<QQQQ", len(data), len(prefix), order, bucket_bits)
    envelope += prefix + data
    command = [str(BIN)] + (["--decode"] if decode else [])
    result = subprocess.run(
        command, input=envelope, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("invalid context fixture unexpectedly succeeded")
    return result


def decode_native(
    payload: bytes,
    source_length: int,
    order: int,
    bucket_bits: int,
    prefix: bytes = b"",
    *,
    ok: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    envelope = struct.pack("<QQQQ", source_length, len(prefix), order, bucket_bits)
    envelope += prefix + payload
    result = subprocess.run(
        [str(BIN), "--decode"],
        input=envelope,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("malformed context payload unexpectedly decoded")
    return result


def main() -> None:
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--example",
            "context_fixture",
            "--manifest-path",
            str(MANIFEST),
            "-j",
            "4",
        ],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.multinomial import (
        decode_context_type_classes,
        encode_context_type_classes,
    )

    rng = random.Random(2002)
    cases = [
        (b"", b"", 1, 8),
        (b"x", b"", 1, 8),
        (bytes(range(256)), b"", 1, 8),
        (b"context mode two " * 260, b"", 2, 8),
        (rng.randbytes(8192), b"", 1, 1),
        (rng.randbytes(4097), bytes(range(256)) * 4, 4, 12),
        (b"retained-history " * 350, b"discarded" * 40 + b"retained-history ", 16, 16),
    ]
    for data, prefix, order, bucket_bits in cases:
        expected = encode_context_type_classes(
            data,
            order=order,
            bucket_bits=bucket_bits,
            prefix_history=prefix,
        )
        actual = invoke(data, order, bucket_bits, prefix).stdout
        assert actual == expected, (
            len(data),
            len(prefix),
            order,
            bucket_bits,
            len(actual),
            len(expected),
        )
        restored, used = decode_context_type_classes(
            actual, 0, len(data), prefix_history=prefix
        )
        assert used == len(actual)
        assert restored == data
        assert (
            decode_native(expected, len(data), order, bucket_bits, prefix).stdout
            == data
        )

    for order, bucket_bits in [(0, 8), (17, 8), (1, 0), (1, 17)]:
        invoke(b"invalid parameters", order, bucket_bits, ok=False)

    malformed_cases = [
        (b"\x01", 0),
        (b"\x00\x08\x00", 0),
        (b"\x01\x08\x00", 1),
        (b"\x01\x08\x00\x00", 0),
    ]
    valid = encode_context_type_classes(
        b"truncation fixture " * 120,
        order=2,
        bucket_bits=8,
        prefix_history=b"prefix fixture",
    )
    malformed_cases.extend((valid[:cut], len(b"truncation fixture " * 120)) for cut in [2, 4, len(valid) - 1])
    for payload, source_length in malformed_cases:
        try:
            restored, used = decode_context_type_classes(
                payload, 0, source_length, prefix_history=b"prefix fixture"
            )
            if used != len(payload):
                raise ValueError("trailing payload bytes")
            del restored
        except (ValueError, IndexError):
            pass
        else:
            raise AssertionError("Python accepted malformed context payload")
        decode_native(payload, source_length, 2, 8, b"prefix fixture", ok=False)

    truncated_envelope = struct.pack("<QQQ", 0, 0, 1)
    result = subprocess.run(
        [str(BIN)],
        input=truncated_envelope,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode

    print(
        "verified canonical Python-identical CIXM6 mode-2 payloads in Python and "
        "Rust: empty, tiny, all-symbol, retained history, orders 1..16, bucket "
        "widths 1..16, rank/range lanes, and malformed inputs"
    )


if __name__ == "__main__":
    main()
