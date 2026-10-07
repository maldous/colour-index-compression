"""Experimental generic CIX count-vector representations.

The incumbent type-class format remains unchanged. Byte-substream mode 5 can
replace its histogram while reusing the exact incumbent sequence payload.
"""
from __future__ import annotations

import math

from .multinomial import (
    _fixed_bytes,
    _read_fixed,
    _composition_rank,
    combination_rank_colex,
    combination_unrank_colex,
    decode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import decode_uints, encode_uints

VERSION = 1
ACTIVE_UINT = 0
ACTIVE_DELTA = 1
DENSE_UINT = 2
DENSE_DELTA = 3
ACTIVE_CENTERED = 4
DENSE_CENTERED = 5


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

    # A uniform prior is derived solely from the known total and alphabet size.
    # Unlike adjacent deltas, independent residuals do not add the noise of two
    # neighbouring counts. The last count is still implied, with no extra prior.
    center = n // len(active_counts)
    result["active-centered"] = (
        bytes((VERSION, ACTIVE_CENTERED)) + prefix
        + encode_uints([_zigzag(c - center) for c in active_counts[:-1]])
    )
    center = n // 256
    result["dense-centered"] = (
        bytes((VERSION, DENSE_CENTERED))
        + encode_uints([_zigzag(c - center) for c in dense])
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

    if mode in (ACTIVE_UINT, ACTIVE_DELTA, ACTIVE_CENTERED):
        active, pos = _decode_active(blob, pos)
        encoded = decode_uints(blob[pos:], max(0, len(active) - 1))
        first = []
        if mode == ACTIVE_UINT:
            first = [value + 1 for value in encoded]
        elif mode == ACTIVE_CENTERED:
            center = total // len(active)
            first = [center + _unzigzag(value) for value in encoded]
            if any(value <= 0 for value in first):
                raise ValueError("non-positive centered active count")
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

    if mode in (DENSE_UINT, DENSE_DELTA, DENSE_CENTERED):
        encoded = decode_uints(blob[pos:], 255)
        first = []
        if mode == DENSE_UINT:
            first = encoded
        elif mode == DENSE_CENTERED:
            center = total // 256
            first = [center + _unzigzag(value) for value in encoded]
            if any(value < 0 for value in first):
                raise ValueError("negative centered dense count")
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


def type_class_candidate(data: bytes, incumbent: bytes) -> bytes | None:
    """Replace metadata only when its complete physical representation shrinks.

    Count-vector integer coders recursively encode at most 255 class bytes.
    Requiring 512 source bytes prevents recursive portfolio search by construction.
    The 64-byte metadata gate avoids spending search work on tiny histograms.
    Both gates depend only on generic byte statistics, never source identity.
    """
    if len(data) < 512:
        return None
    counts = [0] * 256
    for value in data:
        counts[value] += 1
    active = [symbol for symbol, count in enumerate(counts) if count]
    m = len(active)
    if m < 2:
        return None
    header_size = len(vencode(m))
    if m < 256:
        header_size += ((math.comb(256, m) - 1).bit_length() + 7) // 8
    header_size += ((math.comb(len(data) - 1, m - 1) - 1).bit_length() + 7) // 8
    if header_size < 64:
        return None
    histogram, _ = encode_best(counts)
    prefix = vencode(len(histogram)) + histogram
    if len(prefix) >= header_size:
        return None
    return prefix + incumbent[header_size:]


def decode_type_class(blob: bytes, count: int) -> bytes:
    """Decode mode 5 using the incumbent sequence decoder and explicit counts."""
    size, pos = vdecode(blob)
    end = pos + size
    if end > len(blob):
        raise ValueError("truncated count-vector histogram")
    counts = decode(blob[pos:end], total=count)
    active = [symbol for symbol, value in enumerate(counts) if value]
    m = len(active)
    header = bytearray(vencode(m))
    if m < 256:
        header += _fixed_bytes(combination_rank_colex(active),
                               (math.comb(256, m) - 1).bit_length())
    if m > 1:
        header += _fixed_bytes(_composition_rank([counts[s] for s in active]),
                               (math.comb(count - 1, m - 1) - 1).bit_length())
    original = bytes(header) + blob[end:]
    values, consumed = decode_type_class_known_n(original, 0, count)
    if consumed != len(original):
        raise ValueError("unused count-vector type-class bytes")
    return values
