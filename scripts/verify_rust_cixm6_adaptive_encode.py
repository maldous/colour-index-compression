#!/usr/bin/env python3
"""Verify frozen CIXM6 mode-10 adaptive encoder parity."""

from __future__ import annotations

import random
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path("/home/user/src/colour-index-compression")
FROZEN = "80b95427725ecf59d626b2982d50f6349abd56e1"
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
EXAMPLE = ROOT / "rust/cix-native/target/release/examples/adaptive_fixture"


def request(
    operation: int,
    data: bytes,
    source_length: int,
    order: int,
    bucket_bits: int,
    history: bytes,
    model_limit: int = 1 << 16,
) -> subprocess.CompletedProcess[bytes]:
    header = bytes((operation, order, bucket_bits)) + struct.pack(
        "<QQQ", source_length, len(history), model_limit
    )
    return subprocess.run(
        [str(EXAMPLE)],
        input=header + history + data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    if subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            FROZEN,
            "--",
            "cix/adaptive.py",
            "cix/multinomial.py",
        ],
        cwd=REFERENCE,
        check=False,
    ).returncode:
        raise RuntimeError("live adaptive sources differ from the frozen reference")
    sys.path.insert(0, str(REFERENCE))
    from cix.adaptive import decode_adaptive, encode_adaptive

    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--manifest-path",
            str(MANIFEST),
            "--example",
            "adaptive_fixture",
            "-j",
            "2",
        ],
        cwd=ROOT,
        check=True,
    )

    generator = random.Random(0xC1A610)
    fixtures = [
        ("empty-o0", b"", b"", 0, 8),
        ("tiny-o0", b"adaptive model", b"", 0, 8),
        ("repeat-o1", b"abracadabra" * 80, b"", 1, 8),
        ("history-o2", b"history-aware:" * 70, b"prefix-history:" * 30, 2, 10),
        ("hashed-o4", bytes(generator.randrange(32) for _ in range(900)), b"seed" * 20, 4, 9),
        ("narrow-buckets", bytes(generator.randrange(256) for _ in range(1200)), b"", 3, 4),
        ("max-order", b"0123456789abcdef" * 70, bytes(range(64)), 16, 12),
    ]
    for name, source, history, order, bucket_bits in fixtures:
        reference = encode_adaptive(
            source,
            order=order,
            bucket_bits=bucket_bits,
            prefix_history=history,
        )
        encoded = request(0, source, len(source), order, bucket_bits, history)
        if encoded.returncode or encoded.stdout != reference:
            raise RuntimeError(
                f"Rust/Python adaptive bytes differ for {name}: "
                f"rc={encoded.returncode}, stderr={encoded.stderr!r}"
            )
        if decode_adaptive(
            encoded.stdout,
            source_length=len(source),
            prefix_history=history,
        ) != source:
            raise RuntimeError(f"Python failed to decode Rust adaptive fixture {name}")
        decoded = request(
            1, reference, len(source), order, bucket_bits, history
        )
        if decoded.returncode or decoded.stdout != source:
            raise RuntimeError(
                f"Rust failed to decode Python adaptive fixture {name}: "
                f"rc={decoded.returncode}, stderr={decoded.stderr!r}"
            )
        print(
            f"verified {name}: source={len(source)} payload={len(reference)} "
            f"order={order} buckets={bucket_bits}"
        )

    bounded = request(0, bytes(range(64)), 64, 1, 8, b"", model_limit=1)
    if bounded.returncode == 0 or b"memory budget" not in bounded.stderr:
        raise RuntimeError("adaptive encoder did not enforce its model bound")
    invalid = request(0, b"x", 1, 17, 8, b"")
    if invalid.returncode == 0:
        raise RuntimeError("adaptive encoder accepted an invalid order")
    print("verified bounded context rejection and invalid-parameter rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
