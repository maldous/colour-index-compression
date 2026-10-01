#!/usr/bin/env python3
"""Verify Rust CIXM6 mode-4 decoding against frozen Python BWT payloads."""
from __future__ import annotations

import math
import json
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pack_streams(version: int, primary: int, tags: bytes, nonzero: bytes,
                  runs: list[int], tag_blob: bytes, nonzero_blob: bytes,
                  run_blob: bytes) -> bytes:
    from cix.multinomial import vencode

    out = bytearray((version,))
    out += vencode(primary)
    out += vencode(len(tags))
    out += vencode(len(nonzero))
    out += vencode(len(runs))
    for stream in (tag_blob, nonzero_blob, run_blob):
        out += vencode(len(stream))
        out += stream
    return bytes(out)


def _byte_encoder(mode: int, values: bytes, variant: str | None = None) -> bytes:
    from cix.adaptive import encode_adaptive
    from cix.histogram import encode_best, encode_candidates
    from cix.multinomial import (
        _composition_rank,
        encode_type_class_known_n,
        vencode,
    )
    from cix.wavelet import encode_wavelet

    if mode == 0:
        return b"\0" + encode_type_class_known_n(values)
    if mode == 1:
        chunk = max(1, min(17, len(values)))
        return (b"\1" + vencode(chunk) + b"".join(
            encode_type_class_known_n(values[start:start + chunk])
            for start in range(0, len(values), chunk)
        ))
    if mode == 2:
        return b"\2" + encode_adaptive(values, order=0, bucket_bits=8)
    if mode == 3:
        order = 2 if variant == "order-2" else 1
        return bytes((3, order)) + encode_adaptive(
            values, order=order, bucket_bits=8 if order == 1 else 10,
        )
    if mode == 4:
        return b"\4" + encode_wavelet(values)
    if mode == 5:
        incumbent = encode_type_class_known_n(values)
        counts = [values.count(symbol) for symbol in range(256)]
        active = [symbol for symbol, count in enumerate(counts) if count]
        if variant is None:
            histogram, _ = encode_best(counts)
        else:
            histogram = encode_candidates(counts)[variant]
        header_size = len(vencode(len(active)))
        if len(active) < 256:
            header_size += ((math.comb(256, len(active)) - 1).bit_length() + 7) // 8
        if len(active) > 1:
            parts = [counts[symbol] for symbol in active]
            assert _composition_rank(parts) < math.comb(len(values) - 1, len(active) - 1)
            header_size += ((math.comb(len(values) - 1, len(active) - 1) - 1).bit_length() + 7) // 8
        return (b"\5" + vencode(len(histogram)) + histogram
                + incumbent[header_size:])
    raise AssertionError(mode)


def _uint_encoder(mode: int, values: list[int]) -> bytes:
    from cix.multinomial import encode_type_class_known_n, vencode
    from cix.substreams import BitWriter

    if mode == 0:
        return b"\0" + b"".join(vencode(value) for value in values)
    if mode == 1:
        width = 2
        writer = BitWriter()
        for value in values:
            for _ in range(value >> width):
                writer.bit(1)
            writer.bit(0)
            writer.bits(value & ((1 << width) - 1), width)
        return bytes((1, width)) + writer.finish()

    classes = []
    lows = []
    writer = BitWriter()
    for value in values:
        width = (value + 1).bit_length() - 1
        classes.append(width)
        lows.append(value + 1 - (1 << width))
    for low, width in zip(lows, classes):
        writer.bits(low, width)
    class_blob = (
        encode_type_class_known_n(bytes(classes))
        if mode == 2 else _byte_encoder(0, bytes(classes))
    )
    return bytes((mode,)) + vencode(len(class_blob)) + class_blob + writer.finish()


def _legacy_payload(data: bytes, version: int, byte_mode: int = 0,
                    uint_mode: int = 0) -> bytes:
    from cix.bwt import _split_zero_runs, bwt_transform, mtf_encode
    from cix.multinomial import encode_type_class_known_n

    primary, transformed = bwt_transform(data)
    tags, nonzero, runs = _split_zero_runs(mtf_encode(transformed))
    if version == 1:
        tag_blob = encode_type_class_known_n(tags)
        nonzero_blob = encode_type_class_known_n(nonzero)
    elif version == 2:
        tag_blob = _byte_encoder(byte_mode, tags)
        nonzero_blob = _byte_encoder(byte_mode, nonzero)
    else:
        tag_blob = _byte_encoder(byte_mode, tags)
        nonzero_blob = b"\0" + _byte_encoder(byte_mode, nonzero)
    return _pack_streams(
        version, primary, tags, nonzero, runs,
        tag_blob, nonzero_blob, _uint_encoder(uint_mode, runs),
    )


def _fixtures() -> list[tuple[bytes, bytes]]:
    from cix.bwt import (
        _encode_bwt_v4,
        _encode_bwt_v5,
        _pack_runa_runb,
        _runa_runb_tokens,
        _split_zero_runs,
        bwt_transform,
        mtf_encode,
    )
    from cix.multinomial import vencode
    from cix.ppm import _encode_ppm_method, _encode_ppm_see, encode_ppm
    from cix.substreams import encode_bytes

    data = ((b"banana bandana abracadabra\0" * 48)
            + bytes(range(64)) * 8 + b"Z" * 240)
    primary, transformed = bwt_transform(data)
    mtf = mtf_encode(transformed)
    tags, nonzero, runs = _split_zero_runs(mtf)
    tokens, side_bits = _runa_runb_tokens(mtf)
    empty_primary, empty_transformed = bwt_transform(b"")
    empty_mtf = mtf_encode(empty_transformed)

    fixtures = [
        (b"", _legacy_payload(b"", 1)),
        (b"", _encode_bwt_v4(empty_primary, empty_mtf)),
        (b"", _encode_bwt_v5(empty_primary, empty_mtf)),
        (data, _legacy_payload(data, 1)),
        (data, _legacy_payload(data, 3)),
        (data, _encode_bwt_v4(primary, mtf)),
        (data, _encode_bwt_v5(primary, mtf)),
        (data, _pack_runa_runb(6, primary, tokens, side_bits,
                               b"\0" + encode_bytes(tokens))),
        (data, _pack_runa_runb(6, primary, tokens, side_bits,
                               b"\1" + encode_ppm(tokens, max_order=3))),
    ]
    for update_exclusion in (False, True):
        for escape_method in range(4):
            ppm = _encode_ppm_method(
                tokens, max_order=3, prefix_history=b"",
                escape_method=escape_method,
                update_exclusion=update_exclusion,
            )
            assert ppm is not None
            fixtures.append((data, _pack_runa_runb(
                6, primary, tokens, side_bits, b"\1" + ppm,
            )))
        ppm = _encode_ppm_see(
            tokens, max_order=3, prefix_history=b"",
            update_exclusion=update_exclusion,
        )
        assert ppm is not None
        fixtures.append((data, _pack_runa_runb(
            6, primary, tokens, side_bits, b"\1" + ppm,
        )))
    fixtures.extend(
        (data, _legacy_payload(data, 2, byte_mode=mode))
        for mode in range(6)
    )
    fixtures.extend(
        (data, _legacy_payload(data, 3, uint_mode=mode))
        for mode in range(4)
    )
    fixtures.append((data, _pack_streams(
        3, primary, tags, nonzero, runs,
        _byte_encoder(0, tags), b"\1" + _uint_encoder(2, [v - 1 for v in nonzero]),
        _uint_encoder(0, runs),
    )))
    fixtures.append((data, _pack_streams(
        2, primary, tags, nonzero, runs,
        _byte_encoder(3, tags, "order-2"),
        _byte_encoder(3, nonzero, "order-2"), _uint_encoder(0, runs),
    )))
    binary_runs = []
    current = tags[0]
    length = 1
    for tag in tags[1:]:
        if tag == current:
            length += 1
        else:
            binary_runs.append(length - 1)
            current = tag
            length = 1
    binary_runs.append(length - 1)
    for tag_blob in (
        b"\0" + _byte_encoder(0, tags),
        b"\1" + tags[:1] + vencode(len(binary_runs))
        + _uint_encoder(3, binary_runs),
    ):
        fixtures.append((data, _pack_streams(
            4, primary, tags, nonzero, runs, tag_blob,
            b"\1" + _uint_encoder(3, [v - 1 for v in nonzero]),
            _uint_encoder(1, runs),
        )))
    for histogram_variant in (
        "active-uint", "active-delta", "dense-uint", "dense-delta",
        "active-centered", "dense-centered",
    ):
        fixtures.append((data, _pack_streams(
            2, primary, tags, nonzero, runs,
            _byte_encoder(5, tags, histogram_variant),
            _byte_encoder(5, nonzero, histogram_variant),
            _uint_encoder(0, runs),
        )))
    return fixtures


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from cix.bwt import decode_bwt_block

    fixtures = _fixtures()
    versions = {payload[0] for _, payload in fixtures}
    assert versions == set(range(1, 7))
    for source, payload in fixtures:
        assert decode_bwt_block(payload, source_length=len(source)) == source

    with tempfile.TemporaryDirectory(prefix="cix-rust-bwt-") as directory:
        harness = Path(directory)
        fixture_path = harness / "fixtures.bin"
        out = bytearray(b"CIXBWT1\0")
        out += struct.pack("<I", len(fixtures))
        for source, payload in fixtures:
            out += struct.pack("<II", len(source), len(payload))
            out += source
            out += payload
        fixture_path.write_bytes(out)
        source_root = ROOT / "rust/cix-native/src"
        (harness / "src").mkdir()
        (harness / "Cargo.toml").write_text(
            "[package]\nname = \"cix-bwt-verify\"\nversion = \"0.0.0\"\n"
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
            CIX_BWT_FIXTURES=str(fixture_path),
        )
        subprocess.run(
            ["cargo", "test", "--release", "--lib", "-j", "2",
             "--manifest-path", str(harness / "Cargo.toml"),
             "bwt_legacy::tests"],
            cwd=harness, env=env, check=True,
        )
    subprocess.run(
        ["cargo", "build", "--release", "--bin", "uncix", "-j", "2",
         "--manifest-path", str(ROOT / "rust/cix-native/Cargo.toml")],
        cwd=ROOT, check=True,
    )
    uncix = Path(os.environ.get(
        "CIX_NATIVE_BIN", ROOT / "rust/cix-native/target/release",
    )) / "uncix"
    from cix.multinomial import vencode
    for source, payload in fixtures:
        if not source:  # CIXM6 represents an empty stream with no data frame.
            continue
        archive = (
            b"CIXM6" + vencode(1 << 20) + b"\4" + vencode(len(source))
            + vencode(len(payload)) + payload + b"\xff" + vencode(len(source))
            + struct.pack("<I", zlib.crc32(source))
        )
        result = subprocess.run(
            [str(uncix), "-c", "-"], input=archive,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if result.returncode or result.stdout != source:
            raise AssertionError(result.stderr.decode(errors="replace"))
    print(
        f"verified {len(fixtures)} frozen Python CIXM6 mode-4 fixtures: BWT "
        "versions 1-6, byte substreams 0-5, integer substreams 0-3, both "
        "binary-tag and nonzero modes, all histogram count modes, and v6 "
        "local/PPM tokens"
    )


if __name__ == "__main__":
    main()
