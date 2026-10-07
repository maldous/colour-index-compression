#!/usr/bin/env python3
"""Verify native CIXM6 mode-19 encoding against the frozen Python codec."""
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
        "CIX_FIXEDMIX_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/fixedmix_fixture",
    )
)


def encode_native(
    data: bytes,
    prefix: bytes = b"",
    eta_shift: int = 0,
    *,
    ok: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    envelope = struct.pack("<QQQ", len(data), len(prefix), eta_shift)
    result = subprocess.run(
        [str(BIN)],
        input=envelope + prefix + data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("invalid fixed-mix encoding unexpectedly succeeded")
    return result


def decode_native(
    payload: bytes,
    source_length: int,
    prefix: bytes = b"",
    *,
    ok: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    envelope = struct.pack("<QQQ", source_length, len(prefix), 0)
    result = subprocess.run(
        [str(BIN), "--decode"],
        input=envelope + prefix + payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("malformed fixed-mix payload unexpectedly decoded")
    return result


def main() -> None:
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--example",
            "fixedmix_fixture",
            "--manifest-path",
            str(MANIFEST),
            "-j",
            "4",
        ],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.fixedmix import decode_fixed_mix, encode_fixed_mix

    rng = random.Random(19019)
    cases = [
        (b"", b""),
        (b"fixed mixer tiny", b"prefix"),
        (b"fixed mixer patterned data " * 35, b"fixed mixer retained context " * 24),
        (rng.randbytes(257), rng.randbytes(4500)),
        (bytes(range(256)) * 9, b"training horizon " * 390),
    ]
    for data, prefix in cases:
        candidates = []
        for eta_shift in (5, 6, 7):
            expected = encode_fixed_mix(
                data, prefix_history=prefix, eta_shift=eta_shift
            )
            actual = encode_native(data, prefix, eta_shift).stdout
            assert actual == expected, (
                len(data),
                len(prefix),
                eta_shift,
                len(actual),
                len(expected),
            )
            assert decode_fixed_mix(
                actual, source_length=len(data), prefix_history=prefix
            ) == data
            assert decode_native(expected, len(data), prefix).stdout == data
            candidates.append(expected)

        expected_best = min(candidates, key=len)
        reference_best = encode_fixed_mix(data, prefix_history=prefix)
        actual_best = encode_native(data, prefix).stdout
        assert reference_best == expected_best
        assert actual_best == expected_best
        assert decode_fixed_mix(
            actual_best, source_length=len(data), prefix_history=prefix
        ) == data
        assert decode_native(reference_best, len(data), prefix).stdout == data

    for eta_shift in (1, 4, 8, 255):
        encode_native(b"invalid learning rate", eta_shift=eta_shift, ok=False)

    valid = encode_fixed_mix(
        b"malformed fixed-mix payload " * 40,
        prefix_history=b"retained prefix",
        eta_shift=6,
    )
    malformed = [
        b"",
        b"\x01",
        b"\x02\x00\x00",
        b"\x01\x03\x00",
        valid[:-1],
        valid + b"\x00",
    ]
    for payload in malformed:
        try:
            decode_fixed_mix(
                payload,
                source_length=len(b"malformed fixed-mix payload " * 40),
                prefix_history=b"retained prefix",
            )
        except (ValueError, IndexError):
            pass
        else:
            raise AssertionError("Python accepted malformed fixed-mix payload")
        decode_native(
            payload,
            len(b"malformed fixed-mix payload " * 40),
            b"retained prefix",
            ok=False,
        )

    truncated_envelope = struct.pack("<QQ", 0, 0)
    result = subprocess.run(
        [str(BIN)],
        input=truncated_envelope,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode

    print(
        "verified canonical Python-identical CIXM6 mode-19 payloads for learning "
        "rates 5/6/7 and selected candidates, retained-history horizons, Python/Rust "
        "cross-decode, and malformed inputs"
    )


if __name__ == "__main__":
    main()
