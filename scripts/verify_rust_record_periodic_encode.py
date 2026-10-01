#!/usr/bin/env python3
"""Verify canonical native CIXM6 record/periodic payload encoding."""
from __future__ import annotations

import random
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "80b95427725ecf59d626b2982d50f6349abd56e1"
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
FIXTURE = ROOT / "rust/cix-native/target/debug/examples/record_periodic_fixture"
UNCIX = ROOT / "rust/cix-native/target/debug/uncix"


def frozen_python() -> None:
    for relative in (
        "cix/record.py",
        "cix/periodic.py",
        "cix/substreams.py",
        "cix/sparse.py",
        "cix/runs.py",
        "cix/bitplanes.py",
    ):
        expected = subprocess.run(
            ["git", "show", f"{REFERENCE}:{relative}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        if (ROOT / relative).read_bytes() != expected:
            raise AssertionError(f"{relative} differs from frozen reference {REFERENCE}")


def run(*args: object, data: bytes = b"", ok: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [str(arg) for arg in args],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and result.returncode == 0:
        raise AssertionError(f"unexpected success: {args}")
    return result


def vdecode(blob: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if pos >= len(blob):
            raise ValueError("truncated fixture varint")
        byte = blob[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
        shift += 7


def local_modes_record(payload: bytes) -> set[int]:
    if payload[0] == 1:
        return set()
    width, pos = vdecode(payload, 1)
    modes = set()
    for _ in range(width):
        size, pos = vdecode(payload, pos)
        modes.add(payload[pos])
        pos += size
    assert pos == len(payload)
    return modes


def local_mode_periodic(payload: bytes) -> int | None:
    if payload[2] != 4:
        return None
    _, pos = vdecode(payload, 3)
    return payload[pos]


def archive(mode: int, source: bytes, payload: bytes) -> bytes:
    from cix.multinomial import vencode

    return (
        b"CIXM6"
        + vencode(1 << 20)
        + bytes((mode,))
        + vencode(len(source))
        + vencode(len(payload))
        + payload
        + bytes((255,))
        + vencode(len(source))
        + struct.pack("<I", zlib.crc32(source))
    )


def histogram_local_fixture() -> bytes:
    # Frozen deterministic search case whose periodic local stream selects the
    # count-vector histogram replacement (byte substream mode 5).
    rng = random.Random(6)
    selected = b""
    for size in (1024, 2048, 4096):
        for alphabet in (32, 64, 128, 256):
            selected = bytes(rng.randrange(alphabet) for _ in range(size))
    return selected


def main() -> None:
    frozen_python()
    run(
        "cargo",
        "build",
        "--manifest-path",
        MANIFEST,
        "--example",
        "record_periodic_fixture",
        "--bin",
        "uncix",
        "--jobs",
        "2",
    )
    sys.path.insert(0, str(ROOT))
    from cix.periodic import decode_periodic_block, encode_periodic_block
    from cix.record import decode_record_block, encode_record_block

    lane_count = 2
    lane_size = 1024
    lanes = [
        bytes((lane,)) * (lane_size // 2)
        + bytes((lane + 64,)) * (lane_size // 2)
        for lane in range(lane_count)
    ]
    record_local = bytes(
        lanes[index % lane_count][index // lane_count]
        for index in range(lane_count * lane_size)
    )
    record_cases = [
        (b"ABCD" * 250, 2),
        (bytes(range(16)) * 100, 3),
        (
            b"".join(
                bytes((i & 255, (i * 7) & 255, (i * 13) & 255, 0, 1, 2, 3, 4))
                for i in range(500)
            ),
            4,
        ),
        (record_local, 4),
    ]

    noisy_rng = random.Random(3)
    bitplane_rng = random.Random(0)
    periodic_cases = [
        (bytes(range(256)) * 5, 3, 0, None),
        (bytes((0, 255, 1, 254, 2, 253, 3, 252)) * 100, 3, 1, None),
        (b"periodic CIX stream\0" * 100 + bytes(range(64)) * 8, 3, 2, None),
        (
            bytes(bitplane_rng.randrange(16) << 4 | bitplane_rng.randrange(2) for _ in range(1024)),
            2,
            3,
            None,
        ),
        (
            bytes((i % 251) ^ noisy_rng.randrange(16) for i in range(1000)),
            3,
            4,
            4,
        ),
        (histogram_local_fixture(), 2, 4, 5),
    ]

    exact = python_decoded = rust_decoded = 0
    supported_archives: list[bytes] = []
    for source, beam in record_cases:
        expected, description = encode_record_block(source, beam=beam)
        encoded = run(FIXTURE, "record", beam, data=source)
        assert encoded.stdout == expected
        assert encoded.stderr.decode().strip() == description
        assert decode_record_block(encoded.stdout, source_length=len(source)) == source
        exact += 1
        python_decoded += 1
        modes = local_modes_record(expected)
        framed = archive(14, source, encoded.stdout)
        assert run(UNCIX, "-c", "-", data=framed).stdout == source
        supported_archives.append(framed)
        rust_decoded += 1

    covered_inners = set()
    covered_local = set()
    for source, beam, expected_inner, expected_local in periodic_cases:
        expected, description = encode_periodic_block(source, beam=beam)
        assert expected[2] == expected_inner, (description, expected[2], expected_inner)
        local = local_mode_periodic(expected)
        assert local == expected_local, (description, local, expected_local)
        encoded = run(FIXTURE, "periodic", beam, data=source)
        assert encoded.stdout == expected
        assert encoded.stderr.decode().strip() == description
        assert decode_periodic_block(encoded.stdout, source_length=len(source)) == source
        exact += 1
        python_decoded += 1
        covered_inners.add(expected[2])
        if local is not None:
            covered_local.add(local)
        framed = archive(15, source, encoded.stdout)
        assert run(UNCIX, "-c", "-", data=framed).stdout == source
        supported_archives.append(framed)
        rust_decoded += 1

    assert covered_inners == {0, 1, 2, 3, 4}
    assert covered_local == {4, 5}

    # Encoder validation plus framed truncation/corruption rejection.
    run(FIXTURE, "record", 2, data=b"tiny", ok=False)
    run(FIXTURE, "record", 0, data=b"A" * 64, ok=False)
    run(FIXTURE, "periodic", 3, data=b"tiny", ok=False)
    run(FIXTURE, "periodic", 0, data=b"A" * 64, ok=False)
    run(FIXTURE, "unknown", 2, data=b"A" * 64, ok=False)
    for framed in (supported_archives[0], supported_archives[-1]):
        run(UNCIX, "-c", "-", data=framed[:-1], ok=False)
        damaged = bytearray(framed)
        damaged[len(damaged) // 2] ^= 0x80
        run(UNCIX, "-c", "-", data=bytes(damaged), ok=False)

    print(
        f"verified {exact} canonical record/periodic payloads byte-for-byte; "
        f"Python decoded {python_decoded}, Rust decoded {rust_decoded}; "
        "covered periodic inners 0-4 and local byte modes 4-5; "
        "verified invalid options, truncation, and corruption rejection"
    )


if __name__ == "__main__":
    main()
