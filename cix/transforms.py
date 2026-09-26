"""Reversible structured-data transforms for CIX."""

from __future__ import annotations

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
)

SPEC_BY_ID = {spec.id: spec for spec in SPECS}


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

    if width == 1 and spec.name.startswith("byte-"):
        if len(data) <= width:
            return data
        if spec.operation == "xor":
            return data[:width] + bytes(
                data[i] ^ data[i - width] for i in range(width, len(data))
            )
        if spec.operation == "delta":
            return data[:width] + bytes(
                (data[i] - data[i - width]) & 255
                for i in range(width, len(data))
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

    else:
        raise ValueError("unknown transform operation")

    raw = b"".join(value.to_bytes(width, spec.endian) for value in transformed)
    raw += tail
    return _shuffle(raw, width) if spec.shuffle else raw


def invert_transform(data: bytes, spec: TransformSpec) -> bytes:
    width = spec.width
    raw = _unshuffle(data, width) if spec.shuffle else data

    if width == 1 and spec.name.startswith("byte-"):
        out = bytearray(raw)
        if spec.operation == "xor":
            for i in range(width, len(out)):
                out[i] ^= out[i - width]
            return bytes(out)
        if spec.operation == "delta":
            for i in range(width, len(out)):
                out[i] = (out[i] + out[i - width]) & 255
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

    else:
        raise ValueError("unknown transform operation")

    return (
        b"".join(value.to_bytes(width, spec.endian) for value in restored)
        + tail
    )


def encode_transform_block(data: bytes) -> tuple[bytes, str]:
    candidates = []

    for spec in SPECS:
        if len(data) < spec.width * 2:
            continue
        transformed = apply_transform(data, spec)
        payload = bytes((TRANSFORM_VERSION, spec.id))
        payload += encode_type_class_known_n(transformed)
        candidates.append((payload, spec.name))

    if not candidates:
        raise ValueError("no transform candidates")
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
