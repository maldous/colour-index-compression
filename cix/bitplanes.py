"""Binary special case of CIX: per-bit-plane combinatorial ranking."""

from __future__ import annotations

import math

from .multinomial import (
    _fixed_bytes,
    _read_fixed,
    combination_rank_colex,
    combination_unrank_colex,
    vdecode,
    vencode,
)

BITPLANE_VERSION = 1


def encode_bitplanes(data: bytes) -> tuple[bytes, str]:
    n = len(data)
    out = bytearray((BITPLANE_VERSION,))

    for shift in range(7, -1, -1):
        ones = sum((byte >> shift) & 1 for byte in data)
        majority = 1 if ones > n // 2 else 0
        minority_count = n - ones if majority else ones
        minority = 1 - majority

        positions = [
            index
            for index, byte in enumerate(data)
            if ((byte >> shift) & 1) == minority
        ]
        rank = combination_rank_colex(positions)
        cardinality = math.comb(n, minority_count)
        width = (cardinality - 1).bit_length()

        out.append(majority)
        out += vencode(minority_count)
        out += _fixed_bytes(rank, width)

    return bytes(out), "bitplane-combinatorial"


def decode_bitplanes(blob: bytes, *, source_length: int) -> bytes:
    if not blob or blob[0] != BITPLANE_VERSION:
        raise ValueError("unknown bitplane block version")

    pos = 1
    planes = []

    for _ in range(8):
        if pos >= len(blob):
            raise ValueError("truncated bitplane block")
        majority = blob[pos]
        pos += 1
        if majority not in (0, 1):
            raise ValueError("invalid bitplane majority")

        minority_count, pos = vdecode(blob, pos)
        if minority_count > source_length:
            raise ValueError("invalid minority count")

        cardinality = math.comb(source_length, minority_count)
        width = (cardinality - 1).bit_length()
        rank, pos = _read_fixed(blob, pos, width)
        positions = combination_unrank_colex(
            rank, minority_count, source_length
        )

        plane = [majority] * source_length
        minority = 1 - majority
        for index in positions:
            plane[index] = minority
        planes.append(plane)

    if pos != len(blob):
        raise ValueError("trailing bitplane bytes")

    out = bytearray(source_length)
    for index in range(source_length):
        value = 0
        for plane in planes:
            value = (value << 1) | plane[index]
        out[index] = value

    return bytes(out)
