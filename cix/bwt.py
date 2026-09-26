"""Native BWT/MTF/run transform feeding CIX substreams."""

from __future__ import annotations

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import BitReader, BitWriter, decode_bytes, decode_uints, encode_bytes, encode_uints

BWT_VERSION = 5


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


def _encode_binary_tags(tags: bytes) -> bytes:
    local = bytes((0,)) + encode_bytes(tags)
    if not tags:
        return local

    runs = []
    current = tags[0]
    length = 1
    for tag in tags[1:]:
        if tag == current:
            length += 1
        else:
            runs.append(length - 1)
            current = tag
            length = 1
    runs.append(length - 1)

    run_blob = encode_uints(runs)
    encoded_runs = bytes((1, tags[0])) + vencode(len(runs)) + run_blob
    return min((local, encoded_runs), key=len)


def _decode_binary_tags(blob: bytes, count: int) -> bytes:
    if not blob:
        raise ValueError("empty BWT tag stream")
    mode = blob[0]
    if mode == 0:
        return decode_bytes(blob[1:], count)
    if mode == 1:
        if len(blob) < 2 or blob[1] not in (0, 1):
            raise ValueError("invalid BWT run-tag stream")
        run_count, pos = vdecode(blob, 2)
        runs = decode_uints(blob[pos:], run_count)
        out = bytearray()
        tag = blob[1]
        for encoded_length in runs:
            out.extend(bytes((tag,)) * (encoded_length + 1))
            tag ^= 1
        if len(out) != count:
            raise ValueError("BWT run-tag length mismatch")
        return bytes(out)
    raise ValueError("unknown BWT tag stream mode")


def _encode_bwt_v4(primary: int, mtf: bytes) -> bytes:
    tags, nonzero, runs = _split_zero_runs(mtf)
    tag_blob = _encode_binary_tags(tags)

    nonzero_candidates = [
        bytes((0,)) + encode_bytes(nonzero),
        bytes((1,)) + encode_uints([value - 1 for value in nonzero]),
    ]
    nonzero_blob = min(nonzero_candidates, key=len)
    run_blob = encode_uints(runs)

    out = bytearray((4,))
    out += vencode(primary)
    out += vencode(len(tags))
    out += vencode(len(nonzero))
    out += vencode(len(runs))
    for stream in (tag_blob, nonzero_blob, run_blob):
        out += vencode(len(stream))
        out += stream
    return bytes(out)


def _runa_runb_tokens(mtf: bytes) -> tuple[bytes, list[int]]:
    tokens = bytearray()
    side_bits: list[int] = []
    pos = 0

    while pos < len(mtf):
        if mtf[pos] == 0:
            stop = pos + 1
            while stop < len(mtf) and mtf[stop] == 0:
                stop += 1

            # bzip2-style RUNA/RUNB: encode run_length-1 in a bijective
            # binary alphabet whose symbols are 0 and 1.
            value = stop - pos - 1
            while True:
                tokens.append(0 if (value & 1) == 0 else 1)
                if value < 2:
                    break
                value = (value - 2) // 2
            pos = stop
            continue

        rank = mtf[pos]
        if rank <= 253:
            tokens.append(rank + 1)  # token alphabet 2..254
        else:
            tokens.append(255)
            side_bits.append(rank - 254)  # exactly one bit: rank 254/255
        pos += 1

    return bytes(tokens), side_bits


def _runa_runb_decode(tokens: bytes, side_bits: list[int]) -> bytes:
    out = bytearray()
    pos = 0
    side_pos = 0

    while pos < len(tokens):
        token = tokens[pos]

        if token <= 1:
            value = -1
            weight = 1
            while pos < len(tokens) and tokens[pos] <= 1:
                if tokens[pos] == 0:
                    value += weight
                else:
                    value += 2 * weight
                weight <<= 1
                pos += 1
            out.extend(b"\x00" * (value + 1))
            continue

        if token < 255:
            out.append(token - 1)
        else:
            if side_pos >= len(side_bits):
                raise ValueError("BWT RUNA/RUNB side stream exhausted")
            out.append(254 + side_bits[side_pos])
            side_pos += 1
        pos += 1

    if side_pos != len(side_bits):
        raise ValueError("unused BWT RUNA/RUNB side bits")
    return bytes(out)


def _encode_bwt_v5(primary: int, mtf: bytes) -> bytes:
    tokens, side_bits = _runa_runb_tokens(mtf)
    token_blob = encode_bytes(tokens)

    writer = BitWriter()
    for bit in side_bits:
        writer.bit(bit)
    side_blob = writer.finish()

    out = bytearray((BWT_VERSION,))
    out += vencode(primary)
    out += vencode(len(tokens))
    out += vencode(len(side_bits))
    out += vencode(len(token_blob))
    out += token_blob
    out += side_blob
    return bytes(out)


def encode_bwt_block(data: bytes) -> tuple[bytes, str]:
    primary, transformed = bwt_transform(data)
    mtf = mtf_encode(transformed)

    old = _encode_bwt_v4(primary, mtf)
    runa_runb = _encode_bwt_v5(primary, mtf)

    if len(runa_runb) < len(old):
        return runa_runb, "bwt-mtf-runa-runb"
    return old, "bwt-mtf-runs"


def decode_bwt_block(blob: bytes, *, source_length: int) -> bytes:
    if not blob or blob[0] not in (1, 2, 3, 4, BWT_VERSION):
        raise ValueError("unknown BWT block version")

    version = blob[0]
    pos = 1
    primary, pos = vdecode(blob, pos)

    if version == 5:
        token_count, pos = vdecode(blob, pos)
        side_count, pos = vdecode(blob, pos)
        token_len, pos = vdecode(blob, pos)
        token_end = pos + token_len
        if token_end > len(blob):
            raise ValueError("truncated BWT RUNA/RUNB token stream")

        tokens = decode_bytes(blob[pos:token_end], token_count)
        pos = token_end

        side_bytes = (side_count + 7) // 8
        if pos + side_bytes != len(blob):
            raise ValueError("BWT RUNA/RUNB side length mismatch")
        reader = BitReader(blob[pos:])
        side_bits = [reader.bit() for _ in range(side_count)]

        mtf = _runa_runb_decode(tokens, side_bits)
        if len(mtf) != source_length:
            raise ValueError("BWT RUNA/RUNB transformed length mismatch")
        restored = bwt_inverse(primary, mtf_decode(mtf))
        if len(restored) != source_length:
            raise ValueError("BWT source length mismatch")
        return restored
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
        tags = (
            _decode_binary_tags(streams[0], tag_count)
            if version >= 4
            else decode_bytes(streams[0], tag_count)
        )
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
