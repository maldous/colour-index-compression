#!/usr/bin/env python3
"""Verify canonical native CIXM6 mode-17 encoding in both decoders."""
from __future__ import annotations

import os
import random
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
ENCODER = Path(
    os.environ.get(
        "CIX_EXPERT_ENCODER_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/expertmix_encode_fixture",
    )
)
DECODER = Path(
    os.environ.get(
        "CIX_EXPERT_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/expertmix_fixture",
    )
)


def encode(
    data: bytes,
    orders: tuple[int, ...],
    prefix: bytes = b"",
    limit: int = 1 << 24,
    *,
    ok: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    envelope = struct.pack("<QQQQ", len(data), len(prefix), limit, len(orders))
    envelope += bytes(orders) + prefix + data
    result = subprocess.run(
        [str(ENCODER)], input=envelope, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("invalid context-expert encoding unexpectedly succeeded")
    return result


def decode_rust(
    payload: bytes, source_length: int, prefix: bytes = b"", *, ok: bool = True
) -> subprocess.CompletedProcess[bytes]:
    envelope = struct.pack("<QQQ", source_length, len(prefix), 1 << 24)
    envelope += prefix + payload
    result = subprocess.run(
        [str(DECODER)], input=envelope, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("malformed context-expert payload unexpectedly decoded")
    return result


def main() -> None:
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--example",
            "expertmix_encode_fixture",
            "--example",
            "expertmix_fixture",
            "--manifest-path",
            str(MANIFEST),
            "-j",
            "4",
        ],
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.expertmix import decode_expert_mix, encode_expert_mix

    rng = random.Random(1717)
    cases = [
        (b"", b"", (0,)),
        (b"a", b"", (0, 1, 2, 4)),
        (b"expert switching fixture " * 70, b"", (0, 1, 2, 4)),
        (bytes(range(256)) * 8, b"", (0, 1, 3, 8)),
        (rng.randbytes(4096), b"", (0, 1, 2, 3, 4, 6, 8)),
        (b"\x00" * 6000, b"", (0, 1, 2, 4)),
        (
            b"retained prefix predicts this phrase " * 100,
            b"retained prefix predicts this phrase " * 80,
            (0, 1, 2, 4, 8),
        ),
    ]
    for data, prefix, orders in cases:
        native = encode(data, orders, prefix).stdout
        reference = encode_expert_mix(data, orders=orders, prefix_history=prefix)
        assert native == reference, (len(data), orders, len(native), len(reference))
        assert decode_expert_mix(
            native, source_length=len(data), prefix_history=prefix
        ) == data
        assert decode_rust(native, len(data), prefix).stdout == data

    encode(b"bounded contexts", (0, 1, 2, 4), limit=0, ok=False)
    assert encode(b"", (0,), limit=0).stdout == encode_expert_mix(b"", orders=(0,))
    for orders in [(), (1,), (0, 0), (0, 2, 1), (0, 9), tuple(range(9)) + (8,)]:
        encode(b"invalid orders", orders, ok=False)

    valid = encode(b"malformed payload target" * 20, (0, 1, 2, 4)).stdout
    malformed = [valid[:-1], valid + b"\x00", b"\x02" + valid[1:], b"\x01\x00"]
    for payload in malformed:
        try:
            decode_expert_mix(payload, source_length=32)
        except (ValueError, IndexError):
            pass
        else:
            raise AssertionError("Python accepted malformed native payload")
        decode_rust(payload, 32, ok=False)

    print(
        "verified canonical Rust CIXM6 mode-17 payloads in Python and Rust: "
        "empty, context orders 0..8, prefix history, rescaling, bounded contexts, "
        "and malformed inputs"
    )


if __name__ == "__main__":
    main()
