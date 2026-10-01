#!/usr/bin/env python3
"""Verify native legacy BWT encoding against the frozen Python implementation."""
from __future__ import annotations

import json
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stream_variant(data: bytes, version: int) -> bytes:
    from cix.bwt import _split_zero_runs, bwt_transform, mtf_encode
    from cix.multinomial import encode_type_class_known_n, vencode
    from cix.substreams import encode_bytes, encode_uints

    primary, transformed = bwt_transform(data)
    tags, nonzero, runs = _split_zero_runs(mtf_encode(transformed))
    if version == 1:
        tag_blob = encode_type_class_known_n(tags)
        nonzero_blob = encode_type_class_known_n(nonzero)
    elif version == 2:
        tag_blob = encode_bytes(tags)
        nonzero_blob = encode_bytes(nonzero)
    elif version == 3:
        tag_blob = encode_bytes(tags)
        candidates = (
            b"\0" + encode_bytes(nonzero),
            b"\1" + encode_uints([value - 1 for value in nonzero]),
        )
        nonzero_blob = min(candidates, key=len)
    else:
        raise AssertionError(version)
    run_blob = encode_uints(runs)
    out = bytearray((version,))
    out += vencode(primary)
    out += vencode(len(tags))
    out += vencode(len(nonzero))
    out += vencode(len(runs))
    for stream in (tag_blob, nonzero_blob, run_blob):
        out += vencode(len(stream))
        out += stream
    return bytes(out)


def _cases() -> list[bytes]:
    rng = random.Random(0xC1_6B_47)
    cases = [
        b"",
        b"x",
        b"banana bandana",
        b"A" * 1024,
        bytes(range(256)) * 4,
        (b"the quick brown fox jumps over the lazy dog\n" * 90),
        bytes(rng.randrange(8) for _ in range(4096)),
        rng.randbytes(4096),
        (b"alpha\0beta\0gamma\0" * 400) + bytes(range(128)) * 8,
    ]
    cases.extend(rng.randbytes(size) for size in (2, 3, 7, 31, 32, 33, 127, 128, 255, 256, 511, 512))
    cases.extend((bytes(range(width)) * 40) for width in (2, 3, 7, 17))
    return cases


def _fixtures() -> list[tuple[bytes, bytes, str, list[bytes | None]]]:
    from cix.bwt import (
        _encode_bwt_v4,
        _encode_bwt_v5,
        _encode_bwt_v6,
        bwt_transform,
        encode_bwt_block,
        mtf_encode,
    )

    fixtures = []
    for source in _cases():
        primary, transformed = bwt_transform(source)
        mtf = mtf_encode(transformed)
        canonical, description = encode_bwt_block(source)
        variants: list[bytes | None] = [
            _stream_variant(source, 1),
            _stream_variant(source, 2),
            _stream_variant(source, 3),
            _encode_bwt_v4(primary, mtf),
            _encode_bwt_v5(primary, mtf),
            _encode_bwt_v6(primary, mtf),
        ]
        fixtures.append((source, canonical, description, variants))
    return fixtures


def main() -> None:
    sys.path.insert(0, str(ROOT))
    fixtures = _fixtures()
    with tempfile.TemporaryDirectory(prefix="cix-rust-bwt-encode-") as directory:
        harness = Path(directory)
        fixture_path = harness / "fixtures.bin"
        out = bytearray(b"CIXBWTE1")
        out += struct.pack("<I", len(fixtures))
        for source, canonical, description, variants in fixtures:
            description_bytes = description.encode("ascii")
            out += struct.pack("<IIB", len(source), len(canonical), len(description_bytes))
            out += source + canonical + description_bytes
            for payload in variants:
                if payload is None:
                    out += struct.pack("<I", 0xFFFF_FFFF)
                else:
                    out += struct.pack("<I", len(payload)) + payload
        fixture_path.write_bytes(out)

        source_root = ROOT / "rust/cix-native/src"
        (harness / "src").mkdir()
        (harness / "Cargo.toml").write_text(
            "[package]\nname = \"cix-bwt-encode-verify\"\nversion = \"0.0.0\"\n"
            "edition = \"2021\"\n\n[dependencies]\nnum-bigint = \"0.4\"\n"
            "num-traits = \"0.2\"\n",
            encoding="utf-8",
        )
        (harness / "src/lib.rs").write_text(
            "#![allow(dead_code)]\n"
            f"#[path = {json.dumps(str(source_root / 'rank.rs'))}] mod rank;\n"
            f"#[path = {json.dumps(str(source_root / 'adaptive.rs'))}] mod adaptive;\n"
            f"#[path = {json.dumps(str(source_root / 'ppm.rs'))}] mod ppm;\n"
            f"#[path = {json.dumps(str(source_root / 'bwt_legacy.rs'))}] mod bwt_legacy;\n",
            encoding="utf-8",
        )
        env = dict(
            os.environ,
            CARGO_NET_OFFLINE="true",
            CIX_BWT_ENCODE_FIXTURES=str(fixture_path),
        )
        subprocess.run(
            ["cargo", "test", "--release", "--lib", "-j", "2",
             "--manifest-path", str(harness / "Cargo.toml"),
             "bwt_legacy::tests::frozen_python_encoder_fixtures"],
            cwd=harness, env=env, check=True,
        )
    versions = sorted({payload[0] for _, _, _, variants in fixtures
                       for payload in variants if payload is not None})
    print(
        f"verified {len(fixtures)} canonical frozen Python BWT encodes and "
        f"explicit payload variants {versions}; Python decodes every Rust payload"
    )


if __name__ == "__main__":
    main()
