"""Run decomposition for CIX.

The byte identity sequence and run-length sequence have very different distributions, so
they are kept as separate substreams.
"""

from __future__ import annotations

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import decode_uints, encode_uints

RUN_VERSION = 1


def encode_run_block(data: bytes) -> tuple[bytes, str]:
    if not data:
        raise ValueError("empty run block")

    symbols = bytearray()
    lengths = []
    current = data[0]
    run = 1

    for byte in data[1:]:
        if byte == current:
            run += 1
        else:
            symbols.append(current)
            lengths.append(run - 1)
            current = byte
            run = 1

    symbols.append(current)
    lengths.append(run - 1)

    symbol_blob = encode_type_class_known_n(bytes(symbols))
    length_blob = encode_uints(lengths)

    out = bytearray((RUN_VERSION,))
    out += vencode(len(symbols))
    out += vencode(len(symbol_blob))
    out += symbol_blob
    out += length_blob
    return bytes(out), f"runs-{len(symbols)}"


def decode_run_block(blob: bytes, *, source_length: int) -> bytes:
    if not blob or blob[0] != RUN_VERSION:
        raise ValueError("unknown run block version")

    run_count, pos = vdecode(blob, 1)
    symbol_len, pos = vdecode(blob, pos)
    end = pos + symbol_len
    if end > len(blob):
        raise ValueError("truncated run symbols")

    symbols, used = decode_type_class_known_n(blob[pos:end], 0, run_count)
    if used != symbol_len:
        raise ValueError("unused run-symbol bytes")
    lengths = decode_uints(blob[end:], run_count)

    out = bytearray()
    for symbol, length_minus_one in zip(symbols, lengths):
        out.extend(bytes((symbol,)) * (length_minus_one + 1))
        if len(out) > source_length:
            raise ValueError("run stream expands beyond source length")

    if len(out) != source_length:
        raise ValueError("run stream source length mismatch")
    return bytes(out)
