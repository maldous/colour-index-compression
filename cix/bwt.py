"""Native BWT/MTF/run transform feeding CIX substreams."""

from __future__ import annotations

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import decode_uints, encode_uints

BWT_VERSION = 1


def _bwt_transform_python(data: bytes) -> tuple[int, bytes]:
    n = len(data)
    if n == 0:
        return 0, b""

    suffixes = list(range(n))
    rank = list(data)
    work = [0] * n
    step = 1

    while step < n:
        suffixes.sort(key=lambda i: (rank[i], rank[(i + step) % n]))
        classes = 0
        work[suffixes[0]] = 0
        previous = (rank[suffixes[0]], rank[(suffixes[0] + step) % n])

        for index in suffixes[1:]:
            current = (rank[index], rank[(index + step) % n])
            if current != previous:
                classes += 1
                previous = current
            work[index] = classes

        rank, work = work, rank
        if classes == n - 1:
            break
        step <<= 1

    primary = suffixes.index(0)
    transformed = bytes(data[(index - 1) % n] for index in suffixes)
    return primary, transformed


def bwt_transform(data: bytes) -> tuple[int, bytes]:
    """Use a suffix-array accelerator when available, otherwise pure Python."""
    try:
        from pydivsufsort import bw_transform  # type: ignore

        primary, transformed = bw_transform(data)
        return int(primary), bytes(transformed)
    except Exception:
        return _bwt_transform_python(data)


def bwt_inverse(primary: int, transformed: bytes) -> bytes:
    n = len(transformed)
    if n == 0:
        return b""
    if not 0 <= primary < n:
        raise ValueError("invalid BWT primary index")

    counts = [0] * 256
    occurrence = []
    for byte in transformed:
        occurrence.append(counts[byte])
        counts[byte] += 1

    starts = [0] * 256
    total = 0
    for symbol, count in enumerate(counts):
        starts[symbol] = total
        total += count

    lf = [
        starts[byte] + occurrence_index
        for byte, occurrence_index in zip(transformed, occurrence)
    ]

    out = bytearray(n)
    row = primary
    for index in range(n - 1, -1, -1):
        byte = transformed[row]
        out[index] = byte
        row = lf[row]

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

    tag_blob = encode_type_class_known_n(tags)
    nonzero_blob = encode_type_class_known_n(nonzero)
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
    if not blob or blob[0] != BWT_VERSION:
        raise ValueError("unknown BWT block version")

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

    tags, used = decode_type_class_known_n(streams[0], 0, tag_count)
    if used != len(streams[0]):
        raise ValueError("unused BWT tag bytes")
    nonzero, used = decode_type_class_known_n(streams[1], 0, nonzero_count)
    if used != len(streams[1]):
        raise ValueError("unused BWT nonzero bytes")
    runs = decode_uints(streams[2], run_count)

    mtf = _join_zero_runs(tags, nonzero, runs)
    if len(mtf) != source_length:
        raise ValueError("BWT transformed length mismatch")

    restored = bwt_inverse(primary, mtf_decode(mtf))
    if len(restored) != source_length:
        raise ValueError("BWT source length mismatch")
    return restored
