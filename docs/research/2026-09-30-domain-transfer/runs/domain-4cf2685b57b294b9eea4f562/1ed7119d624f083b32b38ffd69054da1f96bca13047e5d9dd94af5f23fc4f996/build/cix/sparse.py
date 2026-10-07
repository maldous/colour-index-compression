"""Generalised colour/index coding for byte alphabets.

Choose the dominant byte as the colour. Encode:
- the dominant byte;
- the number and exact positions of exceptions via C(n,k);
- exception byte values as their own 256-symbol multinomial type class.

For sparse residuals this is the direct byte-alphabet analogue of the original binary
minority-bit construction.
"""

from __future__ import annotations

import math

from .multinomial import (
    _fixed_bytes,
    _read_fixed,
    combination_rank_colex,
    combination_unrank_colex,
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)

SPARSE_VERSION = 1


def encode_sparse_block(data: bytes) -> tuple[bytes, str]:
    if not data:
        raise ValueError("empty sparse block")

    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    dominant = max(range(256), key=counts.__getitem__)

    positions = []
    values = bytearray()
    for index, byte in enumerate(data):
        if byte != dominant:
            positions.append(index)
            values.append(byte)

    k = len(positions)
    cardinality = math.comb(len(data), k)
    width = (cardinality - 1).bit_length()

    out = bytearray((SPARSE_VERSION, dominant))
    out += vencode(k)
    out += _fixed_bytes(combination_rank_colex(positions), width)
    out += encode_type_class_known_n(bytes(values))
    return bytes(out), f"dominant-{dominant:02x}-exceptions-{k}"


def decode_sparse_block(blob: bytes, *, source_length: int) -> bytes:
    if len(blob) < 2 or blob[0] != SPARSE_VERSION:
        raise ValueError("unknown sparse block version")

    dominant = blob[1]
    k, pos = vdecode(blob, 2)
    if k > source_length:
        raise ValueError("too many sparse exceptions")

    cardinality = math.comb(source_length, k)
    width = (cardinality - 1).bit_length()
    rank, pos = _read_fixed(blob, pos, width)
    positions = combination_unrank_colex(rank, k, source_length)

    values, pos = decode_type_class_known_n(blob, pos, k)
    if pos != len(blob):
        raise ValueError("unused sparse payload bytes")

    out = bytearray((dominant,)) * source_length
    for index, value in zip(positions, values):
        out[index] = value
    return bytes(out)
