"""Causal coordinate-conditioned correction predictors, with paid model tags.

No predictor table is transmitted or read from the source during decoding.
Each field carries the selected predictor ID; counts learn only from corrections
already reconstructed. Coordinate streams retain the existing bounded codec.
"""
from collections import Counter
import zlib
import brotli
from . import grid_interval as bounded
from . import grid_feedback as feedback
from . import record_float_grid as grid
from .multinomial import vencode, vdecode

RAW = b'SGCC1'
MAGIC = b'CIXB\x1f'


def modal(counts):
    if not counts:
        return 0
    return min(counts, key=lambda x: (-counts[x], abs(x), x))


def _context_key(coordinate):
    return (int(coordinate < 0), abs(coordinate).bit_length(), coordinate % 16)


def _guess(mode, coordinate, key, last, counts, contexts):
    context_guess = modal(contexts.get(key))
    if mode == 0:
        return last.get(coordinate, 0)
    if mode == 1:
        return modal(counts.get(coordinate))
    if mode == 2:
        return last.get(coordinate, context_guess)
    if mode == 3:
        return modal(counts[coordinate]) if coordinate in counts else context_guess
    return context_guess


def _observe(mode, coordinate, key, actual, counts, contexts):
    if mode in (1, 3):
        counts.setdefault(coordinate, Counter())[actual] += 1
    if mode < 2:
        return
    table = contexts.setdefault(key, Counter())
    table[actual] += 1
    if sum(table.values()) >= 1024:
        for symbol in table:
            table[symbol] = (table[symbol] + 1) // 2


def predict(q, values, width, mode, reverse=False):
    if mode not in range(5):
        raise ValueError('invalid correction predictor')
    last, counts, contexts = {}, {}, {}
    out = []
    modulus = 1 << (8 * width)
    half = modulus // 2
    for coordinate, value in zip(q, values):
        key = _context_key(coordinate)
        guess = _guess(mode, coordinate, key, last, counts, contexts)
        actual = (value + guess + half) % modulus - half if reverse else value
        out.append(actual if reverse else (actual - guess + half) % modulus - half)
        last[coordinate] = actual
        _observe(mode, coordinate, key, actual, counts, contexts)
    return out


def transform(data, mode):
    base, _ = grid.transform(data, 1)
    n, pos = feedback.prefix(base)
    out = bytearray(RAW + bytes([mode]) + base[:pos])
    rows = []
    for offset, width, _ in grid.FIELDS:
        q, values, prefix, pos = feedback.read_field(base, pos, n, width, 1)
        encoded = predict(q, values, width, mode)
        integers, _ = bounded.encode_integers(q, 2, 4096)
        corrections, stats = feedback.write_field(encoded, width, 1)
        out.extend(prefix[:8] + vencode(len(integers)) + integers + corrections)
        rows.append({'offset': offset, 'zeros': encoded.count(0), **stats})
    if pos != len(base):
        raise ValueError('unused grid bytes')
    return bytes(out), {'mode': mode, 'records': n, 'fields': rows}


def inverse(raw):
    if raw[:5] != RAW or len(raw) < 7 or raw[5] not in range(5):
        raise ValueError('invalid correction context stream')
    mode, inner = raw[5], raw[6:]
    n, pos = feedback.prefix(inner)
    out = bytearray(inner[:pos])
    for _, width, _ in grid.FIELDS:
        scale = inner[pos:pos+8]
        pos += 8
        length, pos = vdecode(inner, pos)
        q = bounded.decode_integers(inner[pos:pos+length], n)
        pos += length
        qb = b''.join(grid.signed(x - (q[i-1] if i else 0)) for i, x in enumerate(q))
        prefix = scale + vencode(len(qb)) + qb
        _, values, _, used = feedback.read_field(prefix + inner[pos:], 0, n, width, 1)
        pos += used-len(prefix)
        residues = predict(q, values, width, mode, True)
        out.extend(prefix + feedback.write_field(residues, width, 1)[0])
    if pos != len(inner):
        raise ValueError('trailing correction context bytes')
    return grid.inverse(bytes(out))


def encode(data, mode):
    raw, stats = transform(data, mode)
    frame = MAGIC + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + brotli.compress(raw, quality=11)
    return frame, {**stats, 'transformed_bytes': len(raw), 'physical_bytes': len(frame)}


def decode(frame):
    if frame[:5] != MAGIC:
        raise ValueError('invalid correction context frame')
    n, pos = vdecode(frame, 5)
    crc = int.from_bytes(frame[pos:pos+4], 'big')
    data = inverse(brotli.decompress(frame[pos+4:]))
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('correction context checksum mismatch')
    return data
