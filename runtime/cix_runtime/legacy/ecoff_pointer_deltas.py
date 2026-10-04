"""Causal pointer predictions keyed by relocation-derived candidate alphabets."""
import struct

from . import ecoff_got as parent, ecoff_relocated_pointers as locator
from .multinomial import vdecode, vencode

MAGIC = b"ECRD1"


def _prediction(mode, last, by_key, key, options):
    if mode in (2, 5):
        return by_key.get(key, options[0])
    if mode == 3:
        return options[0]
    return last


def _decode_residual(out, where, mode, residuals, position):
    if mode < 4:
        return struct.unpack_from("<Q", out, where)[0], position
    if any(out[where:where + 8]):
        raise ValueError("pointer-delta skeleton is not zero")
    residual, position = vdecode(residuals, position)
    if residual >= 1 << 64:
        raise ValueError("pointer residual outside word")
    return residual, position


def _encode_residual(out, where, mode, residual, side):
    if mode >= 4:
        out[where:where + 8] = bytes(8)
        side.extend(vencode(residual))
    elif mode:
        struct.pack_into("<Q", out, where, residual)


def process(data, mode, inverse=False, residuals=b""):
    if mode not in range(6):
        raise ValueError("invalid pointer-delta model")
    out = bytearray(data)
    fields = locator.candidates(data)
    keys = {id(options): tuple(options) for _, options, _ in fields}
    last = 0
    by_key = {}
    side = bytearray()
    position = exact = small = 0
    for where, options, _ in fields:
        key = keys[id(options)]
        prediction = _prediction(mode, last, by_key, key, options)
        if inverse:
            residual, position = _decode_residual(out, where, mode, residuals, position)
            value = parent.parent.delta(residual, prediction, 64, True) if mode else residual
            struct.pack_into("<Q", out, where, value)
        else:
            value = struct.unpack_from("<Q", data, where)[0]
            residual = parent.parent.delta(value, prediction, 64) if mode else value
            _encode_residual(out, where, mode, residual, side)
        exact += value == prediction
        small += residual < 16384
        last = value
        by_key[key] = value
    if inverse and position != len(residuals):
        raise ValueError("unused pointer delta bytes")
    return bytes(out), bytes(side), {"mapped_pointers": len(fields), "exact_predictions": exact,
                                     "small_residuals": small, "residual_bytes": len(side)}


def transform(data, mode=2):
    raw, side, stats = process(data, mode)
    skeleton, _ = parent.transform(raw, 3)
    metadata = bytes([mode]) + parent.pack(side)
    frame = skeleton + metadata + len(metadata).to_bytes(8, "little") + MAGIC
    return frame, {**stats, "mode": mode, "original_bytes": len(data), "transformed_bytes": len(frame)}


def inverse(raw):
    if len(raw) < 15 or raw[-5:] != MAGIC:
        raise ValueError("invalid pointer-delta trailer")
    size = int.from_bytes(raw[-13:-5], "little")
    start = len(raw) - 13 - size
    if start < 0 or size < 2:
        raise ValueError("invalid pointer-delta metadata")
    metadata = raw[start:-13]
    mode = metadata[0]
    side, position = parent.read(metadata, 1)
    if position != len(metadata) or (mode < 4 and side):
        raise ValueError("invalid residual substream")
    data = parent.inverse(raw[:start])
    return process(data, mode, True, side)[0]
