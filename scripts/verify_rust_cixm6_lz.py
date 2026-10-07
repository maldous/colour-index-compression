#!/usr/bin/env python3
"""Verify native decoding of frozen Python CIXM6 mode-3 LZ payloads."""

from __future__ import annotations

import struct
import subprocess
import sys
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path("/home/user/src/colour-index-compression")
FROZEN = "80b95427725ecf59d626b2982d50f6349abd56e1"
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
EXAMPLE = ROOT / "rust/cix-native/target/release/examples/decode_legacy_lz"


def check_frozen_sources() -> None:
    paths = (
        "cix/lz.py",
        "cix/substreams.py",
        "cix/multinomial.py",
        "cix/ppm.py",
        "cix/fixedmix.py",
        "cix/wavelet.py",
        "cix/histogram.py",
    )
    changed = subprocess.run(
        ["git", "diff", "--quiet", FROZEN, "--", *paths],
        cwd=REFERENCE,
        check=False,
    ).returncode
    if changed:
        raise RuntimeError("live Python LZ dependencies differ from the frozen reference")


def decode(payload: bytes, source: bytes, history: bytes = b"") -> None:
    request = struct.pack("<QQ", len(source), len(history)) + history + payload
    result = subprocess.run(
        [str(EXAMPLE)], input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode or result.stdout != source:
        raise RuntimeError(
            f"native LZ decode failed: rc={result.returncode}, stderr={result.stderr!r}"
        )


def stream_modes(payload: bytes) -> list[int]:
    pos = 2
    for _ in range(3):
        while payload[pos] & 0x80:
            pos += 1
        pos += 1
    modes = []
    for _ in range(4):
        length = 0
        shift = 0
        while True:
            byte = payload[pos]
            pos += 1
            length |= (byte & 0x7F) << shift
            if byte < 128:
                break
            shift += 7
        modes.append(payload[pos] if length else -1)
        pos += length
    return modes


def pack_lz(
    version: int,
    min_match: int,
    token_count: int,
    literal_count: int,
    match_count: int,
    streams: tuple[bytes, bytes, bytes, bytes],
) -> bytes:
    from cix.multinomial import vencode

    out = bytearray((version, min_match))
    out += vencode(token_count) + vencode(literal_count) + vencode(match_count)
    for stream in streams:
        out += vencode(len(stream)) + stream
    return bytes(out)


def main() -> int:
    check_frozen_sources()
    sys.path.insert(0, str(REFERENCE))
    from cix.lz import encode_lz_block
    from cix.multinomial import ContextModel, encode_type_class_known_n, vencode
    from cix.adaptive import encode_adaptive
    from cix.fixedmix import encode_fixed_mix
    from cix.histogram import encode_candidates as encode_histogram_candidates
    from cix.lz import parse_lz
    from cix.substreams import (
        BitWriter,
        encode_bucketed_type_classes,
        encode_bytes,
        encode_distances,
        encode_distances_best,
        encode_uints,
    )
    from cix.wavelet import encode_wavelet

    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--manifest-path",
            str(MANIFEST),
            "--example",
            "decode_legacy_lz",
            "-j",
            "2",
        ],
        cwd=ROOT,
        check=True,
    )

    fixtures: list[tuple[str, bytes, bytes, tuple[ContextModel, ...], int]] = [
        (
            "repetitive",
            b"the quick brown fox jumps over the lazy dog. " * 80,
            b"",
            (ContextModel(1, 8), ContextModel(2, 10)),
            32,
        ),
        (
            "binary-local",
            bytes(range(256)) * 12 + (b"\x00\xffgeneric-LZ" * 200),
            b"",
            (),
            48,
        ),
        (
            "history",
            (b"shared-dictionary-sequence:" * 100)[-1000:] * 4,
            b"shared-dictionary-sequence:" * 100,
            (ContextModel(1, 8),),
            32,
        ),
        (
            "high-effort",
            (b"generic-long-match-pattern-0123456789|" * 40)
            + (bytes(range(128)) * 4)
            + (b"generic-long-match-pattern-0123456789|" * 35),
            b"",
            (ContextModel(1, 8), ContextModel(2, 10)),
            96,
        ),
    ]
    observed: set[tuple[int, int, int, int]] = set()
    for name, source, history, models, chain in fixtures:
        payload, description = encode_lz_block(
            source,
            prefix_history=history,
            context_models=models,
            chain=chain,
        )
        modes = stream_modes(payload)
        observed.add(tuple(modes))
        decode(payload, source, history)
        print(
            f"verified {name}: source={len(source)} payload={len(payload)} "
            f"version={payload[0]} stream_modes={modes} {description}"
        )

    # Force every byte-substream discriminator. The production encoder chooses
    # only the smallest candidate, so forcing here is necessary to retain decode
    # compatibility with archives produced under different local statistics.
    values = bytes(range(256)) * 2
    tag_stream = bytes((0,)) + encode_type_class_known_n(bytes(len(values)))
    empty_uints = encode_uints([])
    empty_distances = encode_distances_best([])
    byte_streams = {
        0: bytes((0,)) + encode_type_class_known_n(values),
        1: bytes((1,))
        + vencode(128)
        + b"".join(
            encode_type_class_known_n(values[start : start + 128])
            for start in range(0, len(values), 128)
        ),
        2: bytes((2,)) + encode_adaptive(values, order=0, bucket_bits=8),
        3: bytes((3, 1)) + encode_adaptive(values, order=1, bucket_bits=8),
        4: bytes((4,)) + encode_wavelet(values),
    }
    counts = [values.count(symbol) for symbol in range(256)]
    ordinary = encode_type_class_known_n(values)
    active = sum(count > 0 for count in counts)
    header_size = len(vencode(active))
    if active < 256:
        header_size += (math.comb(256, active) - 1).bit_length() // 8
    if active > 1:
        header_size += ((math.comb(len(values) - 1, active - 1) - 1).bit_length() + 7) // 8
    for histogram_name, histogram in encode_histogram_candidates(counts).items():
        histogram_blob = vencode(len(histogram)) + histogram + ordinary[header_size:]
        byte_streams[f"5/{histogram_name}"] = bytes((5,)) + histogram_blob
    for byte_mode, byte_stream in byte_streams.items():
        payload = pack_lz(
            3,
            4,
            len(values),
            len(values),
            0,
            (tag_stream, bytes((2,)) + byte_stream, empty_uints, empty_distances),
        )
        decode(payload, values)
        print(f"verified forced byte substream {byte_mode}")

    # Force the remaining tag and literal wrappers, including context lanes,
    # PPM, and the fixed-point mixer.
    tags = bytes(len(values))
    run_tags = bytes((1, 0)) + vencode(1) + encode_uints([len(values) - 1])
    local_tags = bytes((2,)) + encode_bytes(tags)
    literal_streams = {
        "static": bytes((0,)) + encode_type_class_known_n(values),
        "local": bytes((2,)) + encode_bytes(values),
        "ppm": bytes((3,)) + __import__("cix.ppm", fromlist=["encode_ppm"]).encode_ppm(
            values, max_order=4
        ),
        "fixed-mix": bytes((4,)) + encode_fixed_mix(values),
    }
    buckets: dict[int, bytearray] = {}
    for position, value in enumerate(values):
        bucket = values[position - 1] if position else 0
        buckets.setdefault(bucket, bytearray()).append(value)
    literal_streams["context"] = bytes((1, 1, 8)) + encode_bucketed_type_classes(
        buckets, bucket_count=256, total_items=len(values)
    )
    for tag_name, forced_tags in (("runs", run_tags), ("local", local_tags)):
        payload = pack_lz(
            3,
            4,
            len(values),
            len(values),
            0,
            (forced_tags, literal_streams["static"], empty_uints, empty_distances),
        )
        decode(payload, values)
        print(f"verified forced tag mode {tag_name}")
    for literal_name, forced_literals in literal_streams.items():
        payload = pack_lz(
            3,
            4,
            len(values),
            len(values),
            0,
            (tag_stream, forced_literals, empty_uints, empty_distances),
        )
        decode(payload, values)
        print(f"verified forced literal mode {literal_name}")

    # Force all integer stream modes and the retained version-1 distance form.
    matched_source = b"ABCD" * 300 + b"tail"
    parsed = parse_lz(matched_source, min_match=4, chain=32)
    parsed_tags = bytes((0,)) + encode_type_class_known_n(parsed.tags)
    parsed_literals = bytes((0,)) + encode_type_class_known_n(parsed.literals)

    def forced_uints(mode: int, integers: list[int]) -> bytes:
        if mode == 0:
            return bytes((0,)) + b"".join(vencode(value) for value in integers)
        if mode == 1:
            k = 2
            writer = BitWriter()
            for value in integers:
                for _ in range(value >> k):
                    writer.bit(1)
                writer.bit(0)
                writer.bits(value & 3, k)
            return bytes((1, k)) + writer.finish()
        classes = bytes((value + 1).bit_length() - 1 for value in integers)
        writer = BitWriter()
        for value, width in zip(integers, classes):
            writer.bits(value + 1 - (1 << width), width)
        class_blob = (
            encode_type_class_known_n(classes) if mode == 2 else encode_bytes(classes)
        )
        return bytes((mode,)) + vencode(len(class_blob)) + class_blob + writer.finish()

    for uint_mode in range(4):
        payload = pack_lz(
            3,
            4,
            len(parsed.tags),
            len(parsed.literals),
            len(parsed.lengths),
            (
                parsed_tags,
                parsed_literals,
                forced_uints(uint_mode, parsed.lengths),
                encode_distances_best(parsed.distances),
            ),
        )
        decode(payload, matched_source)
        print(f"verified forced integer mode {uint_mode}")
    version1 = pack_lz(
        1,
        4,
        len(parsed.tags),
        len(parsed.literals),
        len(parsed.lengths),
        (
            encode_type_class_known_n(parsed.tags),
            parsed_literals,
            encode_uints(parsed.lengths),
            encode_distances(parsed.distances),
        ),
    )
    decode(version1, matched_source)
    print("verified retained LZ version 1")

    malformed = struct.pack("<QQ", 1, 0) + b"\x02\x04"
    rejected = subprocess.run(
        [str(EXAMPLE)], input=malformed, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if rejected.returncode == 0:
        raise RuntimeError("native decoder accepted an unknown LZ version")
    print(f"verified {len(fixtures)} selected frozen-reference fixtures; mode tuples={sorted(observed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
