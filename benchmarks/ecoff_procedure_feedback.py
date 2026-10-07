"""Causal procedure-length prediction from already decoded unwind descriptors.

Compare ordinary differences, the last length for a descriptor, its running
mean, and the preceding length. Descriptor words themselves remain literal.
No target length, future table, dictionary or probability trace is supplied.
"""
import struct
from benchmarks import ecoff_pdata_symbols as parent

MAGIC = b'ECPF1'
MASK = (1 << 32) - 1


def predictor(mode, context, history, last):
    if mode == 0: return 0
    if mode == 3: return last
    total, count, recent = history.get(context, (0, 0, 0))
    return recent if mode == 1 else total // count if count else 0


def process(raw, mode, inverse=False):
    out = bytearray(raw); exact = 0; events = 0
    for where, n in parent.procedure.tables(raw):
        history = {}; context = None; previous = 0; last = 0
        for i in range(n):
            word, descriptor = struct.unpack_from('<II', raw, where + 8 * i)
            predicted = predictor(mode, context, history, last)
            if inverse:
                residual = ((word >> 1) ^ -(word & 1)) if mode else word
                delta = (predicted + residual) & MASK
                restored = (previous + delta) & MASK
                struct.pack_into('<I', out, where + 8 * i, restored)
                previous = restored
            else:
                delta = (word - previous) & MASK; residual = (delta - predicted) & MASK
                if mode:
                    signed = residual - (1 << 32) if residual >= 1 << 31 else residual
                    residual = ((signed << 1) ^ (signed >> 31)) & MASK
                struct.pack_into('<I', out, where + 8 * i, residual); previous = word
            exact += delta == predicted; events += 1
            total, count, _ = history.get(context, (0, 0, 0))
            history[context] = (total + delta, count + 1, delta)
            context = descriptor; last = delta
    return bytes(out), dict(predicted_addresses=events, exact_predictions=exact)


def transform(data, mode=1):
    if mode not in range(4): raise ValueError('invalid procedure feedback mode')
    raw, _ = parent.transform(data, 0)
    raw, stats = process(raw, mode)
    return raw + bytes([mode]) + MAGIC, dict(stats, mode=mode, original_bytes=len(data), transformed_bytes=len(raw) + 6)


def inverse(raw):
    if len(raw) < 6 or raw[-5:] != MAGIC or raw[-6] not in range(4):
        raise ValueError('invalid procedure feedback trailer')
    restored, _ = process(raw[:-6], raw[-6], True)
    return parent.inverse(restored)
