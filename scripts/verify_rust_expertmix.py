#!/usr/bin/env python3
"""Cross-check the native CIXM6 mode-17 decoder against Python fixtures."""
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
        "CIX_EXPERT_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/expertmix_fixture",
    )
)


def decode(payload: bytes, source_length: int, prefix: bytes = b"", limit: int = 1 << 24, *, ok: bool = True):
    envelope = struct.pack("<QQQ", source_length, len(prefix), limit) + prefix + payload
    result = subprocess.run(
        [str(BIN)], input=envelope, stdout=subprocess.PIPE, stderr=subprocess.PIPE
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

    rng = random.Random(1701)
    cases = [
        (b"", b"", (0,)),
        (b"expert switching fixture " * 70, b"", (0, 1, 2, 4)),
        (bytes(range(256)) * 8, b"", (0, 1, 3, 8)),
        (rng.randbytes(4096), b"", (0, 1, 2, 3, 4, 6, 8)),
        (bytes(rng.randrange(8) for _ in range(12_000)), b"", (0, 1, 2, 4)),
        (
            b"retained prefix predicts this phrase " * 100,
            b"retained prefix predicts this phrase " * 80,
            (0, 1, 2, 4, 8),
        ),
    ]
    for data, prefix, orders in cases:
        payload = encode_expert_mix(data, orders=orders, prefix_history=prefix)
        assert decode_expert_mix(
            payload, source_length=len(data), prefix_history=prefix
        ) == data
        assert decode(payload, len(data), prefix).stdout == data

    valid = encode_expert_mix(b"bounded context table" * 20, orders=(0, 1, 2, 4))
    decode(valid, len(b"bounded context table" * 20), limit=1, ok=False)
    malformed = [
        b"",
        b"\x02\x01\x00\x00",
        b"\x01\x00\x00",
        b"\x01\x02\x00\x00\x00",
        b"\x01\x02\x01\x00\x00",
        b"\x01\x02\x00\x09\x00",
        valid[:-1],
        valid + b"\x00",
    ]
    for payload in malformed:
        decode(payload, 32, ok=False)

    print(
        "verified Python-produced CIXM6 mode-17 payloads: empty, orders 0..8, "
        "random, prefix-history, malformed-input, and bounded-context cases"
    )


if __name__ == "__main__":
    main()
