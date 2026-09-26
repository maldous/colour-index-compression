"""Binary CIX: exact bit-plane type classes.

Version 1 stored a giant combinatorial rank per plane. Version 2 realizes the same
C(n,k) type class with arithmetic sampling without replacement. That is mathematically
equivalent enumerative coding, but linear-time and practical for large streaming blocks.
"""

from __future__ import annotations

import math

from .multinomial import (
    _ArithmeticDecoder,
    _ArithmeticEncoder,
    _fixed_bytes,
    _read_fixed,
    combination_unrank_colex,
    vdecode,
    vencode,
)

BITPLANE_VERSION = 2


def encode_bitplanes(data: bytes) -> tuple[bytes, str]:
    n = len(data)
    out = bytearray((BITPLANE_VERSION,))
    plane_counts = []

    for shift in range(7, -1, -1):
        ones = sum((byte >> shift) & 1 for byte in data)
        majority = 1 if ones > n // 2 else 0
        minority_count = n - ones if majority else ones
        out.append(majority)
        out += vencode(minority_count)
        plane_counts.append(ones)

    encoder = _ArithmeticEncoder()

    # Conditioned on each plane's Hamming weight, every arrangement is equally
    # likely. Updating the remaining zero/one counts after each bit realizes
    # exactly that finite type class without constructing a giant integer rank.
    for shift, ones in zip(range(7, -1, -1), plane_counts):
        zeros = n - ones
        remaining_ones = ones
        remaining_zeros = zeros

        for byte in data:
            bit = (byte >> shift) & 1
            total = remaining_zeros + remaining_ones
            if bit:
                encoder.encode(remaining_zeros, total, total)
                remaining_ones -= 1
            else:
                encoder.encode(0, remaining_zeros, total)
                remaining_zeros -= 1

    payload, bit_length = encoder.finish()
    out += vencode(bit_length)
    out += payload
    return bytes(out), "bitplane-enumerative-range"


def _decode_v1(blob: bytes, source_length: int) -> bytes:
    """Decode the original giant-rank representation for compatibility."""
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


def decode_bitplanes(blob: bytes, *, source_length: int) -> bytes:
    if not blob or blob[0] not in (1, BITPLANE_VERSION):
        raise ValueError("unknown bitplane block version")
    if blob[0] == 1:
        return _decode_v1(blob, source_length)

    pos = 1
    plane_counts = []
    n = source_length

    for _ in range(8):
        if pos >= len(blob):
            raise ValueError("truncated bitplane header")
        majority = blob[pos]
        pos += 1
        if majority not in (0, 1):
            raise ValueError("invalid bitplane majority")
        minority_count, pos = vdecode(blob, pos)
        if minority_count > n:
            raise ValueError("invalid minority count")
        ones = n - minority_count if majority else minority_count
        plane_counts.append(ones)

    bit_length, pos = vdecode(blob, pos)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("bitplane arithmetic payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    planes = []

    for ones in plane_counts:
        remaining_ones = ones
        remaining_zeros = n - ones
        plane = []

        for _ in range(n):
            total = remaining_zeros + remaining_ones
            target = decoder.target(total)
            if target < remaining_zeros:
                decoder.update(0, remaining_zeros, total)
                plane.append(0)
                remaining_zeros -= 1
            else:
                decoder.update(remaining_zeros, total, total)
                plane.append(1)
                remaining_ones -= 1

        planes.append(plane)

    out = bytearray(n)
    for index in range(n):
        value = 0
        for plane in planes:
            value = (value << 1) | plane[index]
        out[index] = value
    return bytes(out)
