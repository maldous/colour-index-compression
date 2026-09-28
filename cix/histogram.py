"""Experimental generic CIX count-vector representations.

This module is intentionally not wired into the canonical type-class format yet.  It
physically encodes and decodes histogram/count vectors so candidate savings can be
validated without invalidating an in-flight corpus baseline.
"""
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
from .substreams import decode_uints, encode_uints

VERSION = 1
ACTIVE_UINT = 0
ACTIVE_DELTA = 1
DENSE_UINT = 2
DENSE_DELTA = 3


def _zigzag(value: int) -> int:
    return value * 2 if value >= 0 else (-value) * 2 - 1


def _unzigzag(value: int) -> int:
    return value // 2 if value % 2 == 0 else -(value // 2) - 1


def _active_prefix(active: list[int]) -> bytes:
    m = len(active)
    out = bytearray(vencode(m))
    if m < 256:
        width = (math.comb(256, m) - 1).bit_length()
        out += _fixed_bytes(combination_rank_colex(active), width)
    return bytes(out)


def _decode_active(blob: bytes, pos: int) -> tuple[list[int], int]:
    m, pos = vdecode(blob, pos)
    if not 1 <= m <= 256:
        raise ValueError("invalid count-vector active alphabet")
    if m == 256:
        return list(range(256)), pos
    width = (math.comb(256, m) - 1).bit_length()
    rank, pos = _read_fixed(blob, pos, width)
    return combination_unrank_colex(rank, m, 256), pos


def encode_candidates(counts: list[int]) -> dict[str, bytes]:
    if len(counts) != 256 or any(value < 0 for value in counts):
        raise ValueError("count vector must contain 256 non-negative values")
    n = sum(counts)
    if n <= 0:
        raise ValueError("experimental count vector requires non-empty block")

    active_symbols = [symbol for symbol, count in enumerate(counts) if count]
    active_counts = [counts[symbol] for symbol in active_symbols]
    prefix = _active_prefix(active_symbols)

    result: dict[str, bytes] = {}

    # Last count is implied by total n and preceding counts.
    values = [count - 1 for count in active_counts[:-1]]
    result["active-uint"] = (
        bytes((VERSION, ACTIVE_UINT)) + prefix + encode_uints(values)
    )

    previous = 0
    deltas = []
    for count in active_counts[:-1]:
        deltas.append(_zigzag(count - previous))
        previous = count
    result["active-delta"] = (
        bytes((VERSION, ACTIVE_DELTA)) + prefix + encode_uints(deltas)
    )

    dense = counts[:-1]
    result["dense-uint"] = (
        bytes((VERSION, DENSE_UINT)) + encode_uints(dense)
    )

    previous = 0
    deltas = []
    for count in dense:
        deltas.append(_zigzag(count - previous))
        previous = count
    result["dense-delta"] = (
        bytes((VERSION, DENSE_DELTA)) + encode_uints(deltas)
    )
    return result


def encode_best(counts: list[int]) -> tuple[bytes, str]:
    candidates = encode_candidates(counts)
    name = min(candidates, key=lambda key: (len(candidates[key]), key))
    return candidates[name], name


def decode(blob: bytes, *, total: int) -> list[int]:
    if len(blob) < 2 or blob[0] != VERSION:
        raise ValueError("unknown count-vector version")
    if total <= 0:
        raise ValueError("invalid count-vector total")
    mode = blob[1]
    pos = 2
    counts = [0] * 256

    if mode in (ACTIVE_UINT, ACTIVE_DELTA):
        active, pos = _decode_active(blob, pos)
        encoded = decode_uints(blob[pos:], max(0, len(active) - 1))
        first = []
        if mode == ACTIVE_UINT:
            first = [value + 1 for value in encoded]
        else:
            previous = 0
            for value in encoded:
                current = previous + _unzigzag(value)
                if current <= 0:
                    raise ValueError("non-positive active count")
                first.append(current)
                previous = current

        last = total - sum(first)
        if last <= 0:
            raise ValueError("invalid implied active count")
        values = first + [last]
        if len(values) != len(active):
            raise ValueError("active count length mismatch")
        for symbol, value in zip(active, values):
            counts[symbol] = value
        return counts

    if mode in (DENSE_UINT, DENSE_DELTA):
        encoded = decode_uints(blob[pos:], 255)
        first = []
        if mode == DENSE_UINT:
            first = encoded
        else:
            previous = 0
            for value in encoded:
                current = previous + _unzigzag(value)
                if current < 0:
                    raise ValueError("negative dense count")
                first.append(current)
                previous = current
        last = total - sum(first)
        if last < 0:
            raise ValueError("invalid implied dense count")
        return first + [last]

    raise ValueError("unknown count-vector mode")
