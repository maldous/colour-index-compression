"""Native BWT/MTF/run transform feeding CIX substreams."""

from __future__ import annotations

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import decode_bytes, decode_uints, encode_bytes, encode_uints

BWT_VERSION = 3


def _bwt_transform_python(data: bytes) -> tuple[int, bytes]:
    """Pure-Python libdivsufsort-compatible BWT fallback.

    libdivsufsort uses a slightly different physical convention from the usual cyclic
    BWT: the final source byte is emitted first and the primary index is 1-based.
    """
    n = len(data)
    if n == 0:
        return 0, b""

    # Slow fallback used only when pydivsufsort is unavailable.
    suffix_array = sorted(range(n), key=lambda index: data[index:])
    transformed = bytearray((data[-1],))
    primary = None
    for rank, source_index in enumerate(suffix_array):
        if source_index == 0:
            primary = rank + 1
        else:
            transformed.append(data[source_index - 1])

    if primary is None or len(transformed) != n:
        raise AssertionError("invalid fallback BWT")
    return primary, bytes(transformed)


def bwt_transform(data: bytes) -> tuple[int, bytes]:
    """Use a suffix-array accelerator when available, otherwise pure Python."""
    try:
        from pydivsufsort import bw_transform  # type: ignore

        primary, transformed = bw_transform(data)
        return int(primary), bytes(transformed)
    except Exception:
        return _bwt_transform_python(data)


def bwt_inverse(primary: int, transformed: bytes) -> bytes:
    """Inverse libdivsufsort's BWT convention.

    This mirrors pydivsufsort's reference iBWT implementation and therefore decodes
    payloads identically whether or not the optional accelerator is installed.
    """
    n = len(transformed)
    if n == 0:
        if primary not in (0, 1):
            raise ValueError("invalid empty BWT primary index")
        return b""
    if not 1 <= primary <= n:
        raise ValueError("invalid BWT primary index")

    last = [(byte, index) for index, byte in enumerate(transformed)]
    inverse_last = {
        item: index + (index >= primary)
        for index, item in enumerate(last)
    }
    first = sorted(last)

    current = first[primary - 1]
    out = bytearray()
    for _ in range(n):
        out.append(current[0])
        current = first[inverse_last[current] - 1]

    return bytes(out)


def mtf_encode(data: bytes) -> bytes:
    symbols = list(range(256))
    positions = list(range(256))
    out = bytearray()

    for byte in data:
        index = positions[byte]
        out.append(index)
        if index:
            moved = symbols[index]
            for pos in range(index, 0, -1):
                symbols[pos] = symbols[pos - 1]
                positions[symbols[pos]] = pos
            symbols[0] = moved
            positions[moved] = 0

    return bytes(out)


def mtf_decode(data: bytes) -> bytes:
    symbols = list(range(256))
    out = bytearray()

    for index in data:
        byte = symbols[index]
        out.append(byte)
        if index:
            symbols.pop(index)
            symbols.insert(0, byte)

    return bytes(out)


def _split_zero_runs(data: bytes) -> tuple[bytes, bytes, list[int]]:
    tags = bytearray()
    nonzero = bytearray()
    runs = []
    position = 0

    while position < len(data):
        if data[position]:
            tags.append(1)
            nonzero.append(data[position])
            position += 1
            continue

        stop = position + 1
        while stop < len(data) and data[stop] == 0:
            stop += 1
        tags.append(0)
        runs.append(stop - position - 1)
        position = stop

    return bytes(tags), bytes(nonzero), runs


def _join_zero_runs(tags: bytes, nonzero: bytes, runs: list[int]) -> bytes:
    out = bytearray()
    nonzero_pos = 0
    run_pos = 0

    for tag in tags:
        if tag:
            if nonzero_pos >= len(nonzero):
                raise ValueError("nonzero MTF stream exhausted")
            out.append(nonzero[nonzero_pos])
            nonzero_pos += 1
        else:
            if run_pos >= len(runs):
                raise ValueError("zero-run stream exhausted")
            out.extend(b"\x00" * (runs[run_pos] + 1))
            run_pos += 1

    if nonzero_pos != len(nonzero) or run_pos != len(runs):
        raise ValueError("unused BWT substream symbols")
    return bytes(out)


def encode_bwt_block(data: bytes) -> tuple[bytes, str]:
    primary, transformed = bwt_transform(data)
    mtf = mtf_encode(transformed)
    tags, nonzero, runs = _split_zero_runs(mtf)

    tag_blob = encode_bytes(tags)

    nonzero_candidates = [
        bytes((0,)) + encode_bytes(nonzero),
        bytes((1,)) + encode_uints([value - 1 for value in nonzero]),
    ]
    nonzero_blob = min(nonzero_candidates, key=len)
    run_blob = encode_uints(runs)

    out = bytearray((BWT_VERSION,))
    out += vencode(primary)
    out += vencode(len(tags))
    out += vencode(len(nonzero))
    out += vencode(len(runs))
    for stream in (tag_blob, nonzero_blob, run_blob):
        out += vencode(len(stream))
        out += stream

    return bytes(out), "bwt-mtf-runs"


def decode_bwt_block(blob: bytes, *, source_length: int) -> bytes:
    if not blob or blob[0] not in (1, 2, BWT_VERSION):
        raise ValueError("unknown BWT block version")

    version = blob[0]
    pos = 1
    primary, pos = vdecode(blob, pos)
    tag_count, pos = vdecode(blob, pos)
    nonzero_count, pos = vdecode(blob, pos)
    run_count, pos = vdecode(blob, pos)

    streams = []
    for _ in range(3):
        length, pos = vdecode(blob, pos)
        end = pos + length
        if end > len(blob):
            raise ValueError("truncated BWT substream")
        streams.append(blob[pos:end])
        pos = end
    if pos != len(blob):
        raise ValueError("trailing BWT bytes")

    if version == 1:
        tags, used = decode_type_class_known_n(streams[0], 0, tag_count)
        if used != len(streams[0]):
            raise ValueError("unused BWT tag bytes")
        nonzero, used = decode_type_class_known_n(streams[1], 0, nonzero_count)
        if used != len(streams[1]):
            raise ValueError("unused BWT nonzero bytes")
    else:
        tags = decode_bytes(streams[0], tag_count)
        if version == 2:
            nonzero = decode_bytes(streams[1], nonzero_count)
        else:
            if not streams[1]:
                raise ValueError("missing BWT nonzero stream mode")
            if streams[1][0] == 0:
                nonzero = decode_bytes(streams[1][1:], nonzero_count)
            elif streams[1][0] == 1:
                values = decode_uints(streams[1][1:], nonzero_count)
                if any(value > 254 for value in values):
                    raise ValueError("BWT MTF rank outside byte range")
                nonzero = bytes(value + 1 for value in values)
            else:
                raise ValueError("unknown BWT nonzero stream mode")
    runs = decode_uints(streams[2], run_count)

    mtf = _join_zero_runs(tags, nonzero, runs)
    if len(mtf) != source_length:
        raise ValueError("BWT transformed length mismatch")

    restored = bwt_inverse(primary, mtf_decode(mtf))
    if len(restored) != source_length:
        raise ValueError("BWT source length mismatch")
    return restored
