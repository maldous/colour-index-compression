"""Reversible structured-data transforms for CIX."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)

TRANSFORM_VERSION = 1


@dataclass(frozen=True)
class TransformSpec:
    id: int
    name: str
    width: int = 1
    endian: str = "little"
    operation: str = "xor"
    shuffle: bool = False


SPECS = (
    TransformSpec(1, "byte-xor-1", 1, "little", "xor", False),
    TransformSpec(2, "byte-xor-2", 2, "little", "xor", False),
    TransformSpec(3, "byte-xor-4", 4, "little", "xor", False),
    TransformSpec(4, "byte-sub-1", 1, "little", "delta", False),
    TransformSpec(5, "word16le-delta-shuffle", 2, "little", "delta", True),
    TransformSpec(6, "word32le-delta-shuffle", 4, "little", "delta", True),
    TransformSpec(7, "word64le-delta-shuffle", 8, "little", "delta", True),
    TransformSpec(8, "word16be-delta-shuffle", 2, "big", "delta", True),
    TransformSpec(9, "word32be-delta-shuffle", 4, "big", "delta", True),
    TransformSpec(10, "word64be-delta-shuffle", 8, "big", "delta", True),
    TransformSpec(11, "word16le-delta2-shuffle", 2, "little", "delta2", True),
    TransformSpec(12, "word32le-delta2-shuffle", 4, "little", "delta2", True),
    TransformSpec(13, "word64le-delta2-shuffle", 8, "little", "delta2", True),
    TransformSpec(14, "word16be-delta2-shuffle", 2, "big", "delta2", True),
    TransformSpec(15, "word32be-delta2-shuffle", 4, "big", "delta2", True),
    TransformSpec(16, "word64be-delta2-shuffle", 8, "big", "delta2", True),
    TransformSpec(17, "word32le-xor-shuffle", 4, "little", "xor", True),
    TransformSpec(18, "word64le-xor-shuffle", 8, "little", "xor", True),
    TransformSpec(19, "byte-xor-8", 8, "little", "xor", False),
    TransformSpec(20, "byte-xor-12", 12, "little", "xor", False),
    TransformSpec(21, "byte-xor-16", 16, "little", "xor", False),
    TransformSpec(22, "byte-xor-24", 24, "little", "xor", False),
    TransformSpec(23, "byte-xor-32", 32, "little", "xor", False),
    TransformSpec(24, "byte-xor-64", 64, "little", "xor", False),
    TransformSpec(25, "byte-sub-2", 2, "little", "delta", False),
    TransformSpec(26, "byte-sub-4", 4, "little", "delta", False),
    TransformSpec(27, "byte-sub-8", 8, "little", "delta", False),
    TransformSpec(28, "byte-sub-16", 16, "little", "delta", False),
    TransformSpec(29, "word32le-delta2zz-shuffle", 4, "little", "delta2zz", True),
    TransformSpec(30, "word64le-delta2zz-shuffle", 8, "little", "delta2zz", True),
    TransformSpec(31, "word64be-delta2zz-shuffle", 8, "big", "delta2zz", True),
    TransformSpec(32, "x86-e8e9", 1, "little", "e8e9", False),
    TransformSpec(33, "matchxor4", 1, "little", "matchxor", False),
    TransformSpec(34, "sparc-pc", 4, "big", "sparcpc", False),
    TransformSpec(35, "sparc-pc-shuffle", 4, "big", "sparcpc", True),
)

SPEC_BY_ID = {spec.id: spec for spec in SPECS}


def _signed(value: int, bits: int) -> int:
    half = 1 << (bits - 1)
    modulus = 1 << bits
    return value if value < half else value - modulus


def _zigzag(value: int) -> int:
    return (value << 1) if value >= 0 else ((-value << 1) - 1)


def _unzigzag(value: int) -> int:
    return (value >> 1) if not (value & 1) else -((value >> 1) + 1)


def _e8e9(data: bytes, inverse: bool = False) -> bytes:
    out = bytearray(data)
    pos = 0
    limit = len(out) - 4
    while pos < limit:
        opcode = out[pos]
        if opcode in (0xE8, 0xE9):
            value = int.from_bytes(out[pos + 1 : pos + 5], "little")
            if inverse:
                value = (value - pos) & 0xFFFFFFFF
            else:
                value = (value + pos) & 0xFFFFFFFF
            out[pos + 1 : pos + 5] = value.to_bytes(4, "little")
            pos += 5
        else:
            pos += 1
    return bytes(out)


def _sparc_pc(data: bytes, inverse: bool = False, shuffle: bool = False) -> bytes:
    """Normalize SPARC PC-relative CALL/branch fields by instruction word index.

    Format 1 CALL carries disp30. Format 2 Bicc/FBfcc/CBccc carry disp22.
    Adding the current instruction word index maps equal branch targets toward
    equal encoded fields. Subtracting the same index restores every original bit.
    """
    usable = (len(data) // 4) * 4
    out = bytearray(data[:usable])

    for offset in range(0, usable, 4):
        word = int.from_bytes(out[offset : offset + 4], "big")
        op = (word >> 30) & 0x3
        word_index = offset // 4

        if op == 1:  # CALL, disp30
            mask = (1 << 30) - 1
            disp = word & mask
            normalized = (
                (disp - word_index) if inverse else (disp + word_index)
            ) & mask
            word = (word & ~mask) | normalized

        elif op == 0:
            op2 = (word >> 22) & 0x7
            if op2 in (2, 6, 7):  # Bicc, FBfcc, CBccc: disp22
                mask = (1 << 22) - 1
                disp = word & mask
                normalized = (
                    (disp - word_index) if inverse else (disp + word_index)
                ) & mask
                word = (word & ~mask) | normalized

        out[offset : offset + 4] = word.to_bytes(4, "big")

    raw = bytes(out) + data[usable:]
    if shuffle:
        return _shuffle(raw, 4)
    return raw


def _matchxor_encode(data: bytes, key_len: int = 4) -> bytes:
    table: dict[bytes, int] = {}
    active: int | None = None
    out = bytearray()

    for pos, byte in enumerate(data):
        source = None
        if active is not None and active < pos:
            source = active
        elif pos >= key_len:
            source = table.get(data[pos - key_len : pos])

        prediction = data[source] if source is not None else 0
        out.append(byte ^ prediction)

        if pos >= key_len:
            table[data[pos - key_len : pos]] = pos
        active = source + 1 if source is not None and prediction == byte else None

    return bytes(out)


def _matchxor_decode(residual: bytes, key_len: int = 4) -> bytes:
    table: dict[bytes, int] = {}
    active: int | None = None
    out = bytearray()

    for pos, value in enumerate(residual):
        source = None
        if active is not None and active < pos:
            source = active
        elif pos >= key_len:
            source = table.get(bytes(out[pos - key_len : pos]))

        prediction = out[source] if source is not None else 0
        byte = value ^ prediction
        out.append(byte)

        if pos >= key_len:
            table[bytes(out[pos - key_len : pos])] = pos
        active = source + 1 if source is not None and prediction == byte else None

    return bytes(out)


def _words(data: bytes, width: int, endian: str) -> tuple[list[int], bytes]:
    usable = (len(data) // width) * width
    values = [
        int.from_bytes(data[pos : pos + width], endian)
        for pos in range(0, usable, width)
    ]
    return values, data[usable:]


def _shuffle(raw: bytes, width: int) -> bytes:
    usable = (len(raw) // width) * width
    return (
        b"".join(raw[:usable][lane::width] for lane in range(width))
        + raw[usable:]
    )


def _unshuffle(raw: bytes, width: int) -> bytes:
    usable = (len(raw) // width) * width
    words = usable // width
    result = bytearray(usable)
    for lane in range(width):
        result[lane::width] = raw[lane * words : (lane + 1) * words]
    return bytes(result) + raw[usable:]


def apply_transform(data: bytes, spec: TransformSpec) -> bytes:
    width = spec.width

    if spec.operation == "e8e9":
        return _e8e9(data)

    if spec.operation == "matchxor":
        return _matchxor_encode(data)

    if spec.operation == "sparcpc":
        return _sparc_pc(data, shuffle=spec.shuffle)

    if spec.name.startswith("byte-"):
        lag = int(spec.name.rsplit("-", 1)[1])
        if len(data) <= lag:
            return data
        if spec.operation == "xor":
            return data[:lag] + bytes(
                data[i] ^ data[i - lag] for i in range(lag, len(data))
            )
        if spec.operation == "delta":
            return data[:lag] + bytes(
                (data[i] - data[i - lag]) & 255
                for i in range(lag, len(data))
            )

    values, tail = _words(data, width, spec.endian)
    if not values:
        return data

    mod = 1 << (8 * width)
    transformed = [values[0]]

    if spec.operation == "xor":
        transformed.extend(
            values[index] ^ values[index - 1]
            for index in range(1, len(values))
        )

    elif spec.operation == "delta":
        transformed.extend(
            (values[index] - values[index - 1]) % mod
            for index in range(1, len(values))
        )

    elif spec.operation == "delta2":
        if len(values) > 1:
            previous_delta = (values[1] - values[0]) % mod
            transformed.append(previous_delta)
            for index in range(2, len(values)):
                delta = (values[index] - values[index - 1]) % mod
                transformed.append((delta - previous_delta) % mod)
                previous_delta = delta

    elif spec.operation == "delta2zz":
        bits = 8 * width
        mask = mod - 1
        if len(values) > 1:
            previous_delta = _signed((values[1] - values[0]) & mask, bits)
            transformed.append(_zigzag(previous_delta))
            for index in range(2, len(values)):
                delta = _signed((values[index] - values[index - 1]) & mask, bits)
                delta_delta = _signed((delta - previous_delta) & mask, bits)
                transformed.append(_zigzag(delta_delta))
                previous_delta = delta

    else:
        raise ValueError("unknown transform operation")

    raw = b"".join(value.to_bytes(width, spec.endian) for value in transformed)
    raw += tail
    return _shuffle(raw, width) if spec.shuffle else raw


def invert_transform(data: bytes, spec: TransformSpec) -> bytes:
    width = spec.width

    if spec.operation == "e8e9":
        return _e8e9(data, inverse=True)

    if spec.operation == "matchxor":
        return _matchxor_decode(data)

    if spec.operation == "sparcpc":
        raw = _unshuffle(data, 4) if spec.shuffle else data
        return _sparc_pc(raw, inverse=True, shuffle=False)

    raw = _unshuffle(data, width) if spec.shuffle else data

    if spec.name.startswith("byte-"):
        lag = int(spec.name.rsplit("-", 1)[1])
        out = bytearray(raw)
        if spec.operation == "xor":
            for i in range(lag, len(out)):
                out[i] ^= out[i - lag]
            return bytes(out)
        if spec.operation == "delta":
            for i in range(lag, len(out)):
                out[i] = (out[i] + out[i - lag]) & 255
            return bytes(out)

    values, tail = _words(raw, width, spec.endian)
    if not values:
        return raw

    mod = 1 << (8 * width)
    restored = [values[0]]

    if spec.operation == "xor":
        for encoded in values[1:]:
            restored.append(restored[-1] ^ encoded)

    elif spec.operation == "delta":
        for delta in values[1:]:
            restored.append((restored[-1] + delta) % mod)

    elif spec.operation == "delta2":
        if len(values) > 1:
            previous_delta = values[1]
            restored.append((restored[-1] + previous_delta) % mod)
            for delta_delta in values[2:]:
                previous_delta = (previous_delta + delta_delta) % mod
                restored.append((restored[-1] + previous_delta) % mod)

    elif spec.operation == "delta2zz":
        bits = 8 * width
        mask = mod - 1
        if len(values) > 1:
            previous_delta = _unzigzag(values[1])
            restored.append((restored[-1] + previous_delta) % mod)
            for encoded_delta_delta in values[2:]:
                delta_delta = _unzigzag(encoded_delta_delta)
                previous_delta = _signed((previous_delta + delta_delta) & mask, bits)
                restored.append((restored[-1] + previous_delta) % mod)

    else:
        raise ValueError("unknown transform operation")

    return (
        b"".join(value.to_bytes(width, spec.endian) for value in restored)
        + tail
    )


def _typeclass_estimate(data: bytes) -> float:
    n = len(data)
    if not n:
        return 1.0
    counts = Counter(data)
    m = len(counts)
    bits = 8.0
    if m < 256:
        bits += math.log2(math.comb(256, m))
    if m > 1:
        bits += math.log2(math.comb(n - 1, m - 1))
    bits += (
        math.lgamma(n + 1)
        - sum(math.lgamma(count + 1) for count in counts.values())
    ) / math.log(2.0)
    return bits / 8.0


def encode_transform_block(data: bytes, beam: int = 6) -> tuple[bytes, str]:
    profiled = []

    for spec in SPECS:
        if len(data) < max(2, spec.width * 2):
            continue
        transformed = apply_transform(data, spec)
        profiled.append((_typeclass_estimate(transformed), spec, transformed))

    if not profiled:
        raise ValueError("no transform candidates")

    candidates = []
    for _, spec, transformed in sorted(profiled, key=lambda item: item[0])[:beam]:
        payload = bytes((TRANSFORM_VERSION, spec.id))
        payload += encode_type_class_known_n(transformed)
        candidates.append((payload, spec.name))

    return min(candidates, key=lambda item: len(item[0]))


def decode_transform_block(blob: bytes, *, source_length: int) -> bytes:
    if len(blob) < 2 or blob[0] != TRANSFORM_VERSION:
        raise ValueError("unknown transform block version")

    spec = SPEC_BY_ID.get(blob[1])
    if spec is None:
        raise ValueError("unknown transform ID")

    transformed, pos = decode_type_class_known_n(blob, 2, source_length)
    if pos != len(blob):
        raise ValueError("unused transform block bytes")

    restored = invert_transform(transformed, spec)
    if len(restored) != source_length:
        raise ValueError("transform source length mismatch")
    return restored
