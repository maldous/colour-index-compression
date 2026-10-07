#!/usr/bin/env python3
"""Verify canonical native CIXM6 mode-8 candidates and cross-decoding."""
from __future__ import annotations

import math
import os
import random
import struct
import subprocess
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
FIXTURE = Path(
    os.environ.get(
        "CIX_NUMERIC_FIXTURE_BIN",
        ROOT / "rust/cix-native/target/release/examples/numeric_encode_fixture",
    )
)
UNCIX = Path(
    os.environ.get("CIX_NATIVE_UNCIX_BIN", ROOT / "rust/cix-native/target/release/uncix")
)


def reference_candidates(data: bytes):
    import cix.numeric as numeric

    candidates = []
    for spec in numeric.SPECS:
        values, tail = numeric._split_words(data, spec)
        if len(values) < 3:
            continue
        suffix = f"{spec.width * 8}{spec.endian[0]}"
        candidates.append((numeric._encode_for(values, tail, spec), f"for-{suffix}"))
        candidates.append((numeric._encode_delta(values, tail, spec), f"delta-{suffix}"))
        candidates.append((numeric._encode_delta2(values, tail, spec), f"delta2-{suffix}"))
        base = min(values)
        widths = sorted((value - base).bit_length() for value in values)
        choices = {0, max(widths)}
        for fraction in (0.90, 0.95, 0.99):
            choices.add(widths[min(len(widths) - 1, int(len(widths) * fraction))])
        for low_width in sorted(choices):
            if low_width < spec.width * 8:
                candidates.append(
                    (
                        numeric._encode_pfor(values, tail, spec, low_width),
                        f"pfor{low_width}-{suffix}",
                    )
                )
    return candidates


def read_u64(blob: bytes, pos: int) -> tuple[int, int]:
    end = pos + 8
    if end > len(blob):
        raise AssertionError("truncated numeric fixture output")
    return struct.unpack_from("<Q", blob, pos)[0], end


def read_candidate(blob: bytes, pos: int) -> tuple[tuple[bytes, str], int]:
    description_length, pos = read_u64(blob, pos)
    payload_length, pos = read_u64(blob, pos)
    description_end = pos + description_length
    payload_end = description_end + payload_length
    if payload_end > len(blob):
        raise AssertionError("truncated numeric fixture candidate")
    description = blob[pos:description_end].decode()
    return (blob[description_end:payload_end], description), payload_end


def native_candidates(data: bytes) -> tuple[tuple[bytes, str], list[tuple[bytes, str]]]:
    result = subprocess.run(
        [str(FIXTURE)], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    selected, pos = read_candidate(result.stdout, 0)
    count, pos = read_u64(result.stdout, pos)
    candidates = []
    for _ in range(count):
        candidate, pos = read_candidate(result.stdout, pos)
        candidates.append(candidate)
    if pos != len(result.stdout):
        raise AssertionError("trailing numeric fixture output")
    return selected, candidates


def archive(data: bytes, payload: bytes) -> bytes:
    from cix.multinomial import vencode

    return (
        b"CIXM6"
        + vencode(1 << 20)
        + bytes((8,))
        + vencode(len(data))
        + vencode(len(payload))
        + payload
        + bytes((255,))
        + vencode(len(data))
        + struct.pack("<I", zlib.crc32(data))
    )


def rust_decode(data: bytes, payload: bytes, *, ok: bool = True) -> bytes:
    result = subprocess.run(
        [str(UNCIX), "-c", "-"],
        input=archive(data, payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("malformed numeric payload unexpectedly decoded")
    return result.stdout


def pfor_uint_mode(payload: bytes, source_length: int) -> int | None:
    import cix.numeric as numeric
    from cix.multinomial import vdecode

    if payload[1] != numeric.MODE_PFOR:
        return None
    spec = numeric.WordSpec.from_code(payload[2])
    count = source_length // spec.width
    pos = 4 + spec.width
    exception_count, pos = vdecode(payload, pos)
    width = (math.comb(count, exception_count) - 1).bit_length()
    pos += (width + 7) // 8
    high_length, pos = vdecode(payload, pos)
    return payload[pos] if high_length else None


def corpus() -> list[bytes]:
    cases = [
        b"\x01\x00" * 3,
        b"".join(value.to_bytes(2, "little") for value in range(3, 40)),
        b"".join((100 + value * value).to_bytes(4, "big") for value in range(80))
        + b"tail",
        b"".join(
            ((1 << 63) + value * 17).to_bytes(8, "little") for value in range(70)
        ),
        bytes(range(251)) * 3 + b"odd-tail",
    ]
    rng = random.Random(88)
    wanted = {("method", mode) for mode in range(1, 5)} | {
        ("uint", mode) for mode in range(4)
    }
    found = set()
    for size in (6, 8, 12, 16, 32, 64, 128, 256, 512, 1024, 2048):
        for pattern in range(20):
            count = max(3, size // 2)
            if pattern == 0:
                values = [100] * count
            elif pattern == 1:
                values = [100 + index for index in range(count)]
            elif pattern == 2:
                values = [(100 + index * index) & 65535 for index in range(count)]
            elif pattern == 3:
                values = [
                    100 + index % 8 + (500 if index % 79 == 0 else 0)
                    for index in range(count)
                ]
            elif pattern == 4:
                values = [
                    index % 8 + ((1 << (index % 15)) if index % 71 == 0 else 0)
                    for index in range(count)
                ]
            elif pattern == 5:
                values = [rng.randrange(65536) for _ in range(count)]
            elif pattern == 6:
                values = [
                    index % 64 + (10000 if (index // 128) % 2 else 0)
                    for index in range(count)
                ]
            elif pattern == 7:
                values = [
                    index % 4 + ((1 << 15) if index % 97 == 0 else 0)
                    for index in range(count)
                ]
            elif pattern == 8:
                values = [
                    ((index // 128) % 50 * 1000 + index % 8) & 65535
                    for index in range(count)
                ]
            elif pattern == 9:
                values = [0 if index < count // 2 else 65535 for index in range(count)]
            else:
                values = [
                    rng.randrange(65536) if index % max(2, pattern) == 0 else index % 8
                    for index in range(count)
                ]
            data = b"".join(value.to_bytes(2, "little") for value in values)
            from cix.numeric import encode_numeric_block

            selected, _ = encode_numeric_block(data)
            keys = {("method", selected[1])}
            if selected[1] == 4:
                keys.add(("uint", pfor_uint_mode(selected, len(data))))
            if keys - found:
                cases.append(data)
                found.update(keys)
            if wanted <= found:
                return cases
    raise AssertionError(f"numeric fixture corpus missed coverage: {sorted(wanted - found)}")


def main() -> None:
    if os.environ.get("CIX_NUMERIC_SKIP_BUILD") != "1":
        subprocess.run(
            [
                "cargo",
                "build",
                "--release",
                "--example",
                "numeric_encode_fixture",
                "--bin",
                "uncix",
                "--manifest-path",
                str(MANIFEST),
                "-j",
                "2",
            ],
            check=True,
        )
    sys.path.insert(0, str(ROOT))
    from cix.numeric import decode_numeric_block

    selected_modes = set()
    uint_modes = set()
    checked_candidates = 0
    for data in corpus():
        reference = reference_candidates(data)
        selected, native = native_candidates(data)
        assert native == reference, (len(data), len(native), len(reference))
        expected = min(reference, key=lambda item: len(item[0]))
        assert selected == expected, (len(data), selected[1], expected[1])
        assert decode_numeric_block(selected[0], source_length=len(data)) == data
        assert rust_decode(data, selected[0]) == data
        selected_modes.add(selected[0][1])
        mode = pfor_uint_mode(selected[0], len(data))
        if mode is not None:
            uint_modes.add(mode)
        checked_candidates += len(native)

    assert selected_modes == {1, 2, 3, 4}, selected_modes
    assert uint_modes == {0, 1, 2, 3}, uint_modes

    for tiny in (b"", b"x", b"abcde"):
        result = subprocess.run(
            [str(FIXTURE)], input=tiny, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert result.returncode and b"no numeric candidates" in result.stderr

    data = b"".join((100 + index % 8).to_bytes(2, "little") for index in range(200))
    payload = native_candidates(data)[0][0]
    malformed = [
        payload[:-1],
        payload + b"\x00",
        b"\x02" + payload[1:],
        payload[:2] + b"\xff" + payload[3:],
        payload[:1] + b"\xff" + payload[2:],
    ]
    for bad in malformed:
        try:
            decode_numeric_block(bad, source_length=len(data))
        except (ValueError, IndexError):
            pass
        else:
            raise AssertionError("Python accepted malformed numeric payload")
        rust_decode(data, bad, ok=False)

    print(
        "verified canonical Rust CIXM6 mode-8 selection and "
        f"{checked_candidates} ordered candidates in Python; selected numeric modes 1-4, "
        "PFOR integer modes 0-3, Rust/Python decoding, tails/endian widths, and malformed inputs"
    )


if __name__ == "__main__":
    main()
