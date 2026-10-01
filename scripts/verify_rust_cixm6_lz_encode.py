#!/usr/bin/env python3
"""Cross-check native CIXM6 mode-3 LZ encoding against frozen Python."""

from __future__ import annotations

import os
import random
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path("/home/user/src/colour-index-compression")
FROZEN = "80b95427725ecf59d626b2982d50f6349abd56e1"
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
EXAMPLE = ROOT / "rust/cix-native/target/release/examples/encode_legacy_lz"


def check_frozen_sources() -> None:
    paths = (
        "cix/lz.py",
        "cix/substreams.py",
        "cix/multinomial.py",
        "cix/adaptive.py",
        "cix/ppm.py",
        "cix/fixedmix.py",
        "cix/wavelet.py",
        "cix/histogram.py",
    )
    if subprocess.run(
        ["git", "diff", "--quiet", FROZEN, "--", *paths],
        cwd=REFERENCE,
        check=False,
    ).returncode:
        raise RuntimeError("live Python LZ dependencies differ from the frozen reference")


def rust_encode(source: bytes, history: bytes, profile: int) -> bytes:
    request = bytes((profile,)) + struct.pack("<Q", len(history)) + history + source
    result = subprocess.run(
        [str(EXAMPLE)], input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        raise RuntimeError(
            f"native LZ encode failed: rc={result.returncode}, stderr={result.stderr!r}"
        )
    return result.stdout


def main() -> int:
    check_frozen_sources()
    sys.path.insert(0, str(REFERENCE))
    from cix.lz import _encode_parse, decode_lz_block, encode_lz_block, parse_lz
    from cix.multinomial import ContextModel

    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--manifest-path",
            str(MANIFEST),
            "--example",
            "encode_legacy_lz",
            "-j",
            "2",
        ],
        cwd=ROOT,
        check=True,
    )

    canonical = [
        ("empty", b"", b""),
        ("tiny", b"CIX pronounced six", b""),
        ("short-repeat", b"abc123" * 9, b""),
        ("short-history", b"prefix-pattern:" * 3, b"prefix-pattern:" * 12),
        ("binary", bytes(range(47)), b""),
    ]
    for name, source, history in canonical:
        native = rust_encode(source, history, 0)
        reference, description = encode_lz_block(
            source,
            prefix_history=history,
            context_models=(),
            chain=8,
            min_match=4,
        )
        if native != reference:
            raise RuntimeError(
                f"canonical mismatch for {name}: Rust={len(native)} Python={len(reference)}"
            )
        restored = decode_lz_block(
            native, source_length=len(source), prefix_history=history
        )
        if restored != source:
            raise RuntimeError(f"Python failed to decode canonical Rust fixture {name}")
        print(
            f"canonical {name}: source={len(source)} payload={len(native)} {description}"
        )

    generator = random.Random(0xC1A603)
    richer = [
        ("random-512", bytes(generator.randrange(256) for _ in range(512)), b""),
        (
            "random-history-700",
            bytes(generator.randrange(256) for _ in range(700)),
            bytes(generator.randrange(256) for _ in range(300)),
        ),
        ("uniform-alphabet", bytes(range(256)) * 3, b""),
    ]
    models = (ContextModel(1, 8), ContextModel(2, 10))
    for name, source, history in richer:
        native = rust_encode(source, history, 11)
        reference, description = encode_lz_block(
            source,
            prefix_history=history,
            context_models=models,
            chain=8,
            min_match=4,
        )
        if native != reference:
            raise RuntimeError(
                f"rich canonical mismatch for {name}: Rust={len(native)} Python={len(reference)}"
            )
        if decode_lz_block(
            native, source_length=len(source), prefix_history=history
        ) != source:
            raise RuntimeError(f"Python failed rich canonical fixture {name}")
        print(
            f"canonical-rich {name}: source={len(source)} payload={len(native)} {description}"
        )

    fixed_source = bytes(generator.randrange(32) for _ in range(700))
    fixed_parse = parse_lz(
        fixed_source,
        prefix_history=b"",
        min_match=4,
        window=1 << 20,
        chain=8,
        lazy=False,
    )
    fixed_reference, fixed_description = _encode_parse(
        fixed_parse,
        fixed_source,
        b"",
        (),
        4,
        "fixture",
        allow_fixed_mix=True,
    )
    fixed_native = rust_encode(fixed_source, b"", 12)
    if fixed_native != fixed_reference:
        raise RuntimeError(
            "fixed-mix canonical mismatch: "
            f"Rust={len(fixed_native)} Python={len(fixed_reference)}"
        )
    print(
        f"canonical fixed-mix portfolio: source={len(fixed_source)} "
        f"payload={len(fixed_native)} {fixed_description}"
    )

    routed = [
        ("repetitive", b"the quick brown fox jumps over the lazy dog. " * 100, b"", 3),
        ("history", (b"shared-history:" * 80)[-700:] * 5, b"shared-history:" * 80, 5),
        (
            "mixed",
            bytes(range(256)) * 8 + b"structured-pattern-0123456789|" * 90,
            b"",
            7,
        ),
    ]
    for name, source, history, effort in routed:
        native = rust_encode(source, history, effort)
        restored = decode_lz_block(
            native, source_length=len(source), prefix_history=history
        )
        if restored != source:
            raise RuntimeError(f"Python failed to decode Rust effort fixture {name}")
        print(
            f"cross-decode {name}: effort={effort} source={len(source)} payload={len(native)}"
        )

    version1_source = b"legacy-v1-distance-cache:" * 50
    version1 = rust_encode(version1_source, b"", 10)
    if version1[:1] != b"\x01" or decode_lz_block(
        version1, source_length=len(version1_source)
    ) != version1_source:
        raise RuntimeError("retained Python version-1 decode failed")
    print(f"cross-decode version1: payload={len(version1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
