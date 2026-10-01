#!/usr/bin/env python3
"""Cross-check the native CIXM6 mode-7 transform-chain decoder."""
from __future__ import annotations

import io
import os
import random
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get("CIX_NATIVE_BIN", ROOT / "rust/cix-native/target/release"))


def run(*args: str, input: bytes, ok: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ok and result.returncode:
        raise AssertionError(f"{args}: {result.stderr.decode(errors='replace')}")
    if not ok and result.returncode == 0:
        raise AssertionError(f"unexpected success: {args}")
    return result


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from cix.adaptive import encode_adaptive
    from cix.bitplanes import encode_bitplanes
    from cix.bwt import (
        _encode_binary_tags,
        _encode_bwt_v4,
        _encode_bwt_v5,
        _pack_runa_runb,
        _runa_runb_tokens,
        _split_zero_runs,
        bwt_transform,
        mtf_encode,
    )
    from cix.chain import decode_chain_block
    from cix.fixedmix import encode_fixed_mix
    from cix.lz import encode_lz_block, parse_lz
    from cix.multinomial import (
        ContextModel,
        _context_bucket,
        encode_context_type_classes,
        encode_type_class_known_n,
        vencode,
    )
    from cix.ppm import encode_ppm
    from cix.runs import encode_run_block
    from cix.sparse import encode_sparse_block
    from cix.substreams import (
        encode_bucketed_type_classes,
        encode_bytes,
        encode_distances,
        encode_distances_best,
        encode_uints,
    )
    from cix.transforms import SPECS, apply_transform, invert_transform

    def archive(chain_payload: bytes, restored: bytes) -> bytes:
        return (
            b"CIXM6"
            + vencode(1 << 20)
            + bytes((7,))
            + vencode(len(restored))
            + vencode(len(chain_payload))
            + chain_payload
            + bytes((255,))
            + vencode(len(restored))
            + struct.pack("<I", zlib.crc32(restored))
        )

    verified = 0

    def check(spec, inner: int, inner_payload: bytes, transformed: bytes) -> None:
        nonlocal verified
        restored = invert_transform(transformed, spec)
        payload = bytes((1, spec.id, inner)) + inner_payload
        assert decode_chain_block(payload, source_length=len(restored)) == restored
        packed = archive(payload, restored)
        native = run(str(BIN / "uncix"), "-c", "-", input=packed).stdout
        assert native == restored
        verified += 1

    rng = random.Random(7007)
    source = (
        bytes(range(256))
        + bytes(rng.randrange(256) for _ in range(777))
        + b"transform-chain-fixture" * 31
        + b"tail!"
    )
    for spec in SPECS:
        transformed = apply_transform(source, spec)
        check(spec, 1, encode_type_class_known_n(transformed), transformed)

    spec = next(candidate for candidate in SPECS if candidate.id == 20)
    context_transformed = (b"context bucket fixture " * 70) + bytes(range(96)) * 3
    check(
        spec,
        2,
        encode_context_type_classes(context_transformed, order=2, bucket_bits=8),
        context_transformed,
    )

    bitplane_transformed = bytes(range(32)) * 96 + b"\0" * 700
    bitplane_payload, _ = encode_bitplanes(bitplane_transformed)
    check(spec, 5, bitplane_payload, bitplane_transformed)

    sparse_transformed = bytearray(b"\0" * 4096)
    for position in range(0, len(sparse_transformed), 113):
        sparse_transformed[position] = (position // 113 + 1) & 255
    sparse_payload, _ = encode_sparse_block(bytes(sparse_transformed))
    check(spec, 6, sparse_payload, bytes(sparse_transformed))

    runs_transformed = b"A" * 900 + b"BC" * 30 + b"Z" * 1100
    runs_payload, _ = encode_run_block(runs_transformed)
    check(spec, 7, runs_payload, runs_transformed)

    # Exercise both accepted LZ versions plus every current literal mode and tag mode.
    lz_transformed = (b"native chained LZ payload " * 120) + bytes(range(128)) * 5
    lz_payload, _ = encode_lz_block(
        lz_transformed,
        context_models=(ContextModel(1, 8), ContextModel(2, 8)),
        chain=32,
    )
    check(spec, 3, lz_payload, lz_transformed)

    parsed = parse_lz(lz_transformed, window=1 << 16, chain=32)
    v1_streams = (
        encode_type_class_known_n(parsed.tags),
        bytes((0,)) + encode_type_class_known_n(parsed.literals),
        encode_uints(parsed.lengths),
        encode_distances(parsed.distances),
    )
    v1 = bytearray((1, 4))
    v1 += vencode(len(parsed.tags)) + vencode(len(parsed.literals)) + vencode(len(parsed.lengths))
    for stream in v1_streams:
        v1 += vencode(len(stream)) + stream
    check(spec, 3, bytes(v1), lz_transformed)

    literal_source = (b"literal modes and contexts " * 110) + bytes(range(80)) * 4
    tags = bytes(len(literal_source))
    empty_lengths = encode_uints([])
    empty_distances = encode_distances_best([])
    buckets: dict[int, bytearray] = {}
    tail = bytearray()
    for value in literal_source:
        bucket = _context_bucket(tail, 1, 8)
        buckets.setdefault(bucket, bytearray()).append(value)
        tail.append(value)
    literal_streams = (
        bytes((0,)) + encode_type_class_known_n(literal_source),
        bytes((1, 1, 8))
        + encode_bucketed_type_classes(buckets, bucket_count=256, total_items=len(literal_source)),
        bytes((2,)) + encode_bytes(literal_source),
        bytes((3,))
        + encode_ppm(
            literal_source,
            max_order=3,
            escape_method=0,
            update_exclusion=False,
            secondary_escape=False,
        ),
        bytes((4,)) + encode_fixed_mix(literal_source),
    )
    tag_streams = (
        bytes((0,)) + encode_type_class_known_n(tags),
        bytes((1, 0)) + vencode(1) + encode_uints([len(tags) - 1]),
        bytes((2,)) + encode_bytes(tags),
    )
    for index, literals in enumerate(literal_streams):
        tag_stream = tag_streams[index % len(tag_streams)]
        streams = (tag_stream, literals, empty_lengths, empty_distances)
        payload = bytearray((3, 4))
        payload += vencode(len(tags)) + vencode(len(literal_source)) + vencode(0)
        for stream in streams:
            payload += vencode(len(stream)) + stream
        check(spec, 3, bytes(payload), literal_source)

    # Exercise every BWT payload version accepted by the frozen Python decoder.
    bwt_source = (b"banana_bandana::abracadabra::" * 120) + bytes(range(64)) * 8
    primary, transformed_bwt = bwt_transform(bwt_source)
    mtf = mtf_encode(transformed_bwt)
    bwt_tags, bwt_nonzero, bwt_runs = _split_zero_runs(mtf)

    def old_bwt(version: int, tag_stream: bytes, nonzero_stream: bytes) -> bytes:
        streams = (tag_stream, nonzero_stream, encode_uints(bwt_runs))
        payload = bytearray((version,)) + vencode(primary)
        payload += vencode(len(bwt_tags)) + vencode(len(bwt_nonzero)) + vencode(len(bwt_runs))
        for stream in streams:
            payload += vencode(len(stream)) + stream
        return bytes(payload)

    check(
        spec,
        4,
        old_bwt(1, encode_type_class_known_n(bwt_tags), encode_type_class_known_n(bwt_nonzero)),
        bwt_source,
    )
    check(spec, 4, old_bwt(2, encode_bytes(bwt_tags), encode_bytes(bwt_nonzero)), bwt_source)
    check(
        spec,
        4,
        old_bwt(3, encode_bytes(bwt_tags), bytes((1,)) + encode_uints([v - 1 for v in bwt_nonzero])),
        bwt_source,
    )
    check(spec, 4, _encode_bwt_v4(primary, mtf), bwt_source)
    check(spec, 4, _encode_bwt_v5(primary, mtf), bwt_source)
    tokens, side_bits = _runa_runb_tokens(mtf)
    check(
        spec,
        4,
        _pack_runa_runb(6, primary, tokens, side_bits, bytes((0,)) + encode_bytes(tokens)),
        bwt_source,
    )
    check(
        spec,
        4,
        _pack_runa_runb(
            6,
            primary,
            tokens,
            side_bits,
            bytes((1,))
            + encode_ppm(
                tokens,
                max_order=3,
                escape_method=0,
                update_exclusion=False,
                secondary_escape=False,
            ),
        ),
        bwt_source,
    )

    restored = invert_transform(b"malformed transform", spec)
    for payload in (b"", b"\x02\x14\x01", b"\x01\x20\x01", b"\x01\x14\xff"):
        run(str(BIN / "uncix"), "-c", "-", input=archive(payload, restored), ok=False)
    valid = archive(bytes((1, spec.id, 1)) + encode_type_class_known_n(b"truncated"), invert_transform(b"truncated", spec))
    run(str(BIN / "uncix"), "-c", "-", input=valid[:-3], ok=False)

    print(
        f"verified {verified} Rust/Python mode-7 cases: every transform ID, all seven inner codecs, "
        "LZ v1/v3 literal/tag modes, BWT v1-v6, and malformed/truncated rejection"
    )

    # Have the Rust selector emit its bounded high-effort winners and exact
    # per-candidate byte counts, then decode those payloads with the immutable
    # Python reference tree rather than the live working copy.
    reference = "80b95427725ecf59d626b2982d50f6349abd56e1"
    with tempfile.TemporaryDirectory(prefix="cix-chain-encoder-") as directory:
        temporary = Path(directory)
        fixtures = temporary / "fixtures"
        environment = os.environ.copy()
        environment["CIX_CHAIN_FIXTURE_DIR"] = str(fixtures)
        environment["CARGO_BUILD_JOBS"] = "2"
        subprocess.run(
            [
                "cargo",
                "test",
                "--release",
                "--manifest-path",
                str(ROOT / "rust/cix-native/Cargo.toml"),
                "--bin",
                "cix",
                "encoder_fixtures_cross_decode_in_rust",
                "--",
                "--nocapture",
            ],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        frozen = temporary / "frozen"
        frozen.mkdir()
        archive_bytes = subprocess.check_output(
            ["git", "archive", "--format=tar", reference, "cix"], cwd=ROOT
        )
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as reference_tar:
            reference_tar.extractall(frozen)
        reference_check = """
import sys
from pathlib import Path
reference, fixtures = map(Path, sys.argv[1:])
sys.path.insert(0, str(reference))
from cix.chain import decode_chain_block
count = 0
for payload_path in sorted(fixtures.glob('*.payload')):
    stem = payload_path.stem
    payload = payload_path.read_bytes()
    source = (fixtures / f'{stem}.source').read_bytes()
    assert decode_chain_block(payload, source_length=len(source)) == source
    measurement_path = fixtures / f'{stem}.candidates.tsv'
    if measurement_path.exists():
        rows = [line.split('\t', 3) for line in measurement_path.read_text().splitlines()]
        assert rows and min(int(row[2]) for row in rows) == len(payload)
        assert {int(row[0]) for row in rows} == {12, 13, 16, 20, 21, 29, 30, 31, 33}
    count += 1
assert count == 20
print(f'frozen Python decoded {count} Rust-encoded payloads with exact full-byte accounting')
"""
        subprocess.run(
            [sys.executable, "-c", reference_check, str(frozen), str(fixtures)],
            check=True,
        )


if __name__ == "__main__":
    main()
