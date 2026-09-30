"""Native integer/telemetry coding for CIX.

Candidates:
- frame of reference (FOR)
- ZigZag delta bit packing
- ZigZag delta-of-delta bit packing
- patched FOR with combinatorially ranked exception positions

All candidates are self-contained and reversible; the smallest physical payload wins.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .multinomial import (
    _fixed_bytes,
    _read_fixed,
    combination_rank_colex,
    combination_unrank_colex,
    vdecode,
    vencode,
)
from .substreams import BitReader, BitWriter, decode_uints, encode_uints

NUMERIC_VERSION = 1
MODE_FOR = 1
MODE_DELTA = 2
MODE_DELTA2 = 3
MODE_PFOR = 4


@dataclass(frozen=True)
class WordSpec:
    width: int
    endian: str

    @property
    def code(self) -> int:
        endian_bit = 1 if self.endian == "big" else 0
        return ({2: 0, 4: 1, 8: 2}[self.width] << 1) | endian_bit

    @classmethod
    def from_code(cls, code: int) -> "WordSpec":
        width_code = code >> 1
        width = {0: 2, 1: 4, 2: 8}.get(width_code)
        if width is None:
            raise ValueError("invalid numeric word width")
        return cls(width, "big" if code & 1 else "little")


SPECS = tuple(
    WordSpec(width, endian)
    for width in (2, 4, 8)
    for endian in ("little", "big")
)


def _zigzag(value: int) -> int:
    return (value << 1) if value >= 0 else ((-value << 1) - 1)


def _unzigzag(value: int) -> int:
    return (value >> 1) if not (value & 1) else -((value >> 1) + 1)


def _signed_mod(value: int, bits: int) -> int:
    modulus = 1 << bits
    value &= modulus - 1
    return value if value < (modulus >> 1) else value - modulus


def _split_words(data: bytes, spec: WordSpec) -> tuple[list[int], bytes]:
    usable = (len(data) // spec.width) * spec.width
    values = [
        int.from_bytes(data[pos : pos + spec.width], spec.endian)
        for pos in range(0, usable, spec.width)
    ]
    return values, data[usable:]


def _pack(values: list[int], width: int) -> bytes:
    writer = BitWriter()
    for value in values:
        if width:
            writer.bits(value, width)
    return writer.finish()


def _unpack(blob: bytes, count: int, width: int) -> list[int]:
    if width == 0:
        return [0] * count
    reader = BitReader(blob)
    return [reader.bits(width) for _ in range(count)]


def _encode_for(values: list[int], tail: bytes, spec: WordSpec) -> bytes:
    base = min(values)
    residuals = [value - base for value in values]
    width = max((value.bit_length() for value in residuals), default=0)

    out = bytearray((NUMERIC_VERSION, MODE_FOR, spec.code, width))
    out += base.to_bytes(spec.width, spec.endian)
    out += _pack(residuals, width)
    out += tail
    return bytes(out)


def _decode_for(blob: bytes, pos: int, source_length: int, spec: WordSpec) -> bytes:
    width = blob[pos]
    pos += 1
    base = int.from_bytes(blob[pos : pos + spec.width], spec.endian)
    pos += spec.width

    count = source_length // spec.width
    tail_length = source_length % spec.width
    packed_bytes = (count * width + 7) // 8
    end = pos + packed_bytes
    if end + tail_length != len(blob):
        raise ValueError("numeric FOR payload length mismatch")

    residuals = _unpack(blob[pos:end], count, width)
    values = [base + residual for residual in residuals]
    limit = 1 << (8 * spec.width)
    if any(value >= limit for value in values):
        raise ValueError("numeric FOR value overflow")

    return (
        b"".join(value.to_bytes(spec.width, spec.endian) for value in values)
        + blob[end:]
    )


def _delta_values(values: list[int], spec: WordSpec) -> list[int]:
    bits = 8 * spec.width
    out = []
    for previous, current in zip(values, values[1:]):
        delta = _signed_mod(current - previous, bits)
        out.append(_zigzag(delta))
    return out


def _encode_delta(values: list[int], tail: bytes, spec: WordSpec) -> bytes:
    residuals = _delta_values(values, spec)
    width = max((value.bit_length() for value in residuals), default=0)

    out = bytearray((NUMERIC_VERSION, MODE_DELTA, spec.code, width))
    out += values[0].to_bytes(spec.width, spec.endian)
    out += _pack(residuals, width)
    out += tail
    return bytes(out)


def _decode_delta(blob: bytes, pos: int, source_length: int, spec: WordSpec) -> bytes:
    width = blob[pos]
    pos += 1
    first = int.from_bytes(blob[pos : pos + spec.width], spec.endian)
    pos += spec.width

    count = source_length // spec.width
    tail_length = source_length % spec.width
    residual_count = max(0, count - 1)
    packed_bytes = (residual_count * width + 7) // 8
    end = pos + packed_bytes
    if end + tail_length != len(blob):
        raise ValueError("numeric delta payload length mismatch")

    residuals = _unpack(blob[pos:end], residual_count, width)
    modulus = 1 << (8 * spec.width)
    values = [first]
    for residual in residuals:
        values.append((values[-1] + _unzigzag(residual)) % modulus)

    return (
        b"".join(value.to_bytes(spec.width, spec.endian) for value in values)
        + blob[end:]
    )


def _encode_delta2(values: list[int], tail: bytes, spec: WordSpec) -> bytes:
    bits = 8 * spec.width
    deltas = [
        _signed_mod(current - previous, bits)
        for previous, current in zip(values, values[1:])
    ]

    if not deltas:
        first_delta = 0
        residuals = []
    else:
        first_delta = deltas[0]
        residuals = [
            _zigzag(_signed_mod(current - previous, bits))
            for previous, current in zip(deltas, deltas[1:])
        ]

    width = max((value.bit_length() for value in residuals), default=0)
    first_delta_zz = _zigzag(first_delta)

    out = bytearray((NUMERIC_VERSION, MODE_DELTA2, spec.code, width))
    out += values[0].to_bytes(spec.width, spec.endian)
    out += vencode(first_delta_zz)
    out += _pack(residuals, width)
    out += tail
    return bytes(out)


def _decode_delta2(blob: bytes, pos: int, source_length: int, spec: WordSpec) -> bytes:
    width = blob[pos]
    pos += 1
    first = int.from_bytes(blob[pos : pos + spec.width], spec.endian)
    pos += spec.width
    first_delta_zz, pos = vdecode(blob, pos)

    count = source_length // spec.width
    tail_length = source_length % spec.width
    residual_count = max(0, count - 2)
    packed_bytes = (residual_count * width + 7) // 8
    end = pos + packed_bytes
    if end + tail_length != len(blob):
        raise ValueError("numeric delta2 payload length mismatch")

    residuals = _unpack(blob[pos:end], residual_count, width)
    modulus = 1 << (8 * spec.width)
    bits = 8 * spec.width
    values = [first]

    if count >= 2:
        previous_delta = _unzigzag(first_delta_zz)
        values.append((values[-1] + previous_delta) % modulus)

        for encoded in residuals:
            previous_delta = _signed_mod(
                previous_delta + _unzigzag(encoded), bits
            )
            values.append((values[-1] + previous_delta) % modulus)

    return (
        b"".join(value.to_bytes(spec.width, spec.endian) for value in values)
        + blob[end:]
    )


def _encode_pfor(
    values: list[int],
    tail: bytes,
    spec: WordSpec,
    low_width: int,
) -> bytes:
    base = min(values)
    residuals = [value - base for value in values]
    mask = (1 << low_width) - 1 if low_width else 0

    exception_positions = [
        index for index, residual in enumerate(residuals)
        if residual >> low_width
    ]
    exception_high = [
        residual >> low_width
        for residual in residuals
        if residual >> low_width
    ]

    low_values = [residual & mask for residual in residuals]
    low_blob = _pack(low_values, low_width)

    exception_count = len(exception_positions)
    position_cardinality = math.comb(len(values), exception_count)
    position_width = (position_cardinality - 1).bit_length()
    position_rank = combination_rank_colex(exception_positions)

    high_blob = encode_uints(exception_high)

    out = bytearray((NUMERIC_VERSION, MODE_PFOR, spec.code, low_width))
    out += base.to_bytes(spec.width, spec.endian)
    out += vencode(exception_count)
    out += _fixed_bytes(position_rank, position_width)
    out += vencode(len(high_blob))
    out += high_blob
    out += low_blob
    out += tail
    return bytes(out)


def _decode_pfor(blob: bytes, pos: int, source_length: int, spec: WordSpec) -> bytes:
    low_width = blob[pos]
    pos += 1
    base = int.from_bytes(blob[pos : pos + spec.width], spec.endian)
    pos += spec.width

    count = source_length // spec.width
    tail_length = source_length % spec.width
    exception_count, pos = vdecode(blob, pos)
    if exception_count > count:
        raise ValueError("too many PFOR exceptions")

    position_cardinality = math.comb(count, exception_count)
    position_width = (position_cardinality - 1).bit_length()
    position_rank, pos = _read_fixed(blob, pos, position_width)
    exception_positions = combination_unrank_colex(
        position_rank, exception_count, count
    )

    high_len, pos = vdecode(blob, pos)
    high_end = pos + high_len
    if high_end > len(blob):
        raise ValueError("truncated PFOR exceptions")
    highs = decode_uints(blob[pos:high_end], exception_count)
    pos = high_end

    low_bytes = (count * low_width + 7) // 8
    low_end = pos + low_bytes
    if low_end + tail_length != len(blob):
        raise ValueError("PFOR payload length mismatch")
    lows = _unpack(blob[pos:low_end], count, low_width)

    for index, high in zip(exception_positions, highs):
        lows[index] |= high << low_width

    values = [base + residual for residual in lows]
    limit = 1 << (8 * spec.width)
    if any(value >= limit for value in values):
        raise ValueError("PFOR value overflow")

    return (
        b"".join(value.to_bytes(spec.width, spec.endian) for value in values)
        + blob[low_end:]
    )


def encode_numeric_block(data: bytes) -> tuple[bytes, str]:
    candidates: list[tuple[bytes, str]] = []

    for spec in SPECS:
        values, tail = _split_words(data, spec)
        if len(values) < 3:
            continue

        candidates.append((_encode_for(values, tail, spec), f"for-{spec.width * 8}{spec.endian[0]}"))
        candidates.append((_encode_delta(values, tail, spec), f"delta-{spec.width * 8}{spec.endian[0]}"))
        candidates.append((_encode_delta2(values, tail, spec), f"delta2-{spec.width * 8}{spec.endian[0]}"))

        base = min(values)
        bit_lengths = sorted((value - base).bit_length() for value in values)
        choices = {0}
        for fraction in (0.90, 0.95, 0.99):
            index = min(len(bit_lengths) - 1, int(len(bit_lengths) * fraction))
            choices.add(bit_lengths[index])
        choices.add(max(bit_lengths))

        for low_width in sorted(choices):
            if low_width >= spec.width * 8:
                continue
            candidates.append(
                (
                    _encode_pfor(values, tail, spec, low_width),
                    f"pfor{low_width}-{spec.width * 8}{spec.endian[0]}",
                )
            )

    if not candidates:
        raise ValueError("no numeric candidates")
    return min(candidates, key=lambda item: len(item[0]))


def decode_numeric_block(blob: bytes, *, source_length: int) -> bytes:
    if len(blob) < 4 or blob[0] != NUMERIC_VERSION:
        raise ValueError("unknown numeric block version")

    mode = blob[1]
    spec = WordSpec.from_code(blob[2])
    pos = 3

    if source_length // spec.width < 1:
        raise ValueError("numeric source too short")

    if mode == MODE_FOR:
        return _decode_for(blob, pos, source_length, spec)
    if mode == MODE_DELTA:
        return _decode_delta(blob, pos, source_length, spec)
    if mode == MODE_DELTA2:
        return _decode_delta2(blob, pos, source_length, spec)
    if mode == MODE_PFOR:
        return _decode_pfor(blob, pos, source_length, spec)
    raise ValueError("unknown numeric mode")
