"""Coordinate-conditioned correction groups with paid compositions and controls.

Group membership is reconstructed from decoded quantized coordinates. Raw IDs,
exact type-class ranks and same-count arithmetic share that predictive input.
All palettes, histograms, termination and partition-selector bytes are counted.
"""
from collections import Counter, defaultdict
import math
import zlib
import brotli
from . import grid_interval as bounded
from . import grid_feedback as feedback
from . import record_float_grid as grid
from .multinomial import vencode, vdecode, decode_type_class

RAW = b'SGCC2'
MAGIC = b'CIXB\x20'
BLOCK = 1024


def groups(q, context):
    if context not in range(4):
        raise ValueError('invalid coordinate partition')
    result = defaultdict(list)
    for i, value in enumerate(q):
        if context == 0:
            key = (0,)
        elif context == 1:
            key = (int(value < 0), abs(value).bit_length())
        elif context == 2:
            key = (int(value < 0), abs(value).bit_length(), value % 16)
        else:
            key = (value,)
        result[key].append(i)
    return [result[k] for k in sorted(result)]


def pack(blob):
    return vencode(len(blob)) + blob


def read(blob, pos):
    n, pos = vdecode(blob, pos)
    if pos+n > len(blob):
        raise ValueError('truncated conditional field')
    return blob[pos:pos+n], pos+n


def encode_corrections(q, residual, width, context, coding):
    counts = Counter(residual)
    palette = sorted(counts, key=lambda x: (-counts[x], x))
    if len(palette) > 256:
        return b'\0' + feedback.write_field(residual, width, 1)[0], {'raw_fallback': True}
    out = bytearray(b'\1' + vencode(len(palette)))
    for value in palette:
        out.extend(grid.signed(value))
    ids = {value:i for i,value in enumerate(palette)}
    uncertainty = 0.0
    partitions = groups(q, context)
    for partition in partitions:
        symbols = bytes(ids[residual[i]] for i in partition)
        if coding == 0:
            out.extend(symbols)
        else:
            for at in range(0, len(symbols), BLOCK):
                block = symbols[at:at+BLOCK]
                counts = Counter(block)
                uncertainty += (math.lgamma(len(block)+1)-sum(math.lgamma(c+1) for c in counts.values()))/math.log(2)
                out.extend(pack(grid.type_frame(block, coding == 2)))
    return bytes(out), {
        'raw_fallback': False,
        'groups': len(partitions),
        'alphabet': len(palette),
        'conditional_log_cardinality_bits': uncertainty if coding else None,
        'correction_stream_bytes': len(out),
    }


def _fallback_corrections(blob, q, width):
    qb = b''.join(grid.signed(x-(q[i-1] if i else 0)) for i, x in enumerate(q))
    prefix = bytes(8) + pack(qb)
    _, values, _, used = feedback.read_field(prefix + blob, 0, len(q), width, 1)
    if used != len(prefix) + len(blob):
        raise ValueError('trailing fallback')
    return values


def _read_palette(blob):
    n, pos = vdecode(blob, 1)
    if n > 256:
        raise ValueError('invalid conditional palette')
    palette = []
    for _ in range(n):
        value, pos = grid.read_signed(blob, pos)
        palette.append(value)
    return palette, pos


def _read_partition_ids(blob, pos, count, coding):
    if coding == 0:
        return blob[pos:pos + count], pos + count
    ids = bytearray()
    for at in range(0, count, BLOCK):
        frame, pos = read(blob, pos)
        symbols, used = decode_type_class(frame)
        if used != len(frame) or len(symbols) != min(BLOCK, count - at):
            raise ValueError('invalid conditional type class')
        ids.extend(symbols)
    return ids, pos


def decode_corrections(blob, q, width, context, coding):
    if not blob:
        raise ValueError('missing conditional corrections')
    if blob[0] == 0:
        return _fallback_corrections(blob[1:], q, width)
    if blob[0] != 1:
        raise ValueError('invalid correction representation')
    palette, pos = _read_palette(blob)
    if not palette and q:
        raise ValueError('invalid conditional palette')
    out = [0]*len(q)
    for partition in groups(q, context):
        ids, pos = _read_partition_ids(blob, pos, len(partition), coding)
        if len(ids) != len(partition) or any(x >= len(palette) for x in ids):
            raise ValueError('invalid conditional correction IDs')
        for index, symbol in zip(partition, ids):
            out[index] = palette[symbol]
    if pos != len(blob):
        raise ValueError('trailing correction groups')
    return out


def transform(data, context, coding):
    if coding not in range(3):
        raise ValueError('invalid correction coding')
    base, _ = grid.transform(data, 1)
    n, pos = feedback.prefix(base)
    out = bytearray(RAW + bytes([context, coding]) + base[:pos])
    rows = []
    for offset, width, _ in grid.FIELDS:
        q, values, prefix, pos = feedback.read_field(base, pos, n, width, 1)
        residual = feedback.feedback(q, values, width)
        integers, _ = bounded.encode_integers(q, 2, 4096)
        corrections, stats = encode_corrections(q, residual, width, context, coding)
        out.extend(prefix[:8] + pack(integers) + pack(corrections))
        rows.append({'offset': offset, **stats})
    return bytes(out), {'context': context, 'coding': coding, 'records': n, 'fields': rows}


def inverse(raw):
    if raw[:5] != RAW or len(raw) < 8 or raw[5] not in range(4) or raw[6] not in range(3):
        raise ValueError('invalid conditional grid stream')
    context, coding = raw[5:7]
    inner = raw[7:]
    n, pos = feedback.prefix(inner)
    out = bytearray(inner[:pos])
    for _, width, _ in grid.FIELDS:
        scale = inner[pos:pos+8]
        pos += 8
        integers, pos = read(inner, pos)
        q = bounded.decode_integers(integers, n)
        corrections, pos = read(inner, pos)
        residual = decode_corrections(corrections, q, width, context, coding)
        values = feedback.feedback(q, residual, width, True)
        qb = b''.join(grid.signed(x-(q[i-1] if i else 0)) for i,x in enumerate(q))
        out.extend(scale + pack(qb) + feedback.write_field(values, width, 1)[0])
    if pos != len(inner):
        raise ValueError('trailing conditional grid fields')
    return grid.inverse(bytes(out))


def encode(data, context, coding):
    raw, stats = transform(data, context, coding)
    frame = MAGIC + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + brotli.compress(raw, quality=11)
    return frame, {**stats, 'transformed_bytes': len(raw), 'physical_bytes': len(frame)}


def decode(frame):
    if frame[:5] != MAGIC:
        raise ValueError('invalid conditional grid frame')
    n, pos = vdecode(frame, 5)
    crc = int.from_bytes(frame[pos:pos+4], 'big')
    data = inverse(brotli.decompress(frame[pos+4:]))
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('conditional grid checksum mismatch')
    return data
