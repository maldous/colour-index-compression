"""Fixed-width and restricted-alphabet refinement of the database constraints."""
import collections
import zlib
from .multinomial import vencode, vdecode
from . import mysql_record_constraints as base
from .mysql_record_constraints import _bounded_brotli


def signed(value):
    value = int(value)
    return vencode(2 * value if value >= 0 else -2 * value - 1)


def read_signed(blob, pos):
    value, pos = vdecode(blob, pos)
    return (value // 2 if not value & 1 else -(value // 2) - 1), pos


MAGIC = b'CIXD\x02'
RAW = b'MYCC1'


def pack_ids(ids, width):
    out = bytearray(); acc = 0; bits = 0
    for value in ids:
        acc = (acc << width) | value; bits += width
        while bits >= 8:
            bits -= 8; out.append((acc >> bits) & 255)
        acc &= (1 << bits) - 1
    if bits:
        out.append(acc << (8 - bits))
    return bytes(out)


def unpack_ids(blob, n, width):
    if len(blob) != (n * width + 7) // 8:
        raise ValueError('fixed alphabet payload length')
    out = []; acc = 0; bits = 0; at = 0; mask = (1 << width) - 1
    for _ in range(n):
        while bits < width:
            acc = (acc << 8) | blob[at]; at += 1; bits += 8
        bits -= width; out.append((acc >> bits) & mask); acc &= (1 << bits) - 1
    if acc:
        raise ValueError('nonzero alphabet padding')
    return out


def _encoded_content(content, width, mode):
    replacement = bytes([mode]) + vencode(width)
    if mode == 1:
        return replacement + content
    palette = sorted(set(content)); lookup = {value: index for index, value in enumerate(palette)}
    ids = [lookup[value] for value in content]
    replacement += vencode(len(palette)) + bytes(palette)
    if mode == 2:
        return replacement + pack_ids(ids, (len(palette) - 1).bit_length())
    counts = collections.Counter(ids); average = len(content) // max(1, len(palette))
    profile = [counts[index] for index in range(len(palette))]
    return replacement + b''.join(signed(count - average) for count in profile) + base.order_encode(ids, profile, 3 if mode == 3 else 2)


def _replacement(column, n, mode, index):
    replacement = b'\0' + column
    if column[0] != 0 or not n:
        return replacement, None
    values = base.column_decode(column, n); width = len(values[0])
    if not all(len(value) == width for value in values):
        return replacement, None
    replacement = _encoded_content(b''.join(values), width, mode)
    return replacement, {
        'index': index, 'width': width, 'original_column_bytes': len(column), 'new_column_bytes': len(replacement),
    }


def transform(data, mode=1):
    if mode not in (1, 2, 3, 4):
        raise ValueError('invalid fixed-column policy')
    raw, _ = base.transform(data, 3); nr, pos = vdecode(raw, 5); size = (nr + 7) // 8
    flags = raw[pos:pos + size]; pos += size; n = sum((flags[index // 8] >> (index % 8)) & 1 for index in range(nr))
    _, pos = base.read(raw, pos); out = bytearray(RAW + raw[5:pos]); changed = []
    for index in range(9):
        column, pos = base.read(raw, pos); replacement, measurement = _replacement(column, n, mode, index)
        if measurement is not None:
            changed.append(measurement)
        out.extend(base.pack(replacement))
    if pos != len(raw):
        raise ValueError('trailing database transform')
    return bytes(out), {'mode': mode, 'original_bytes': len(data), 'transformed_bytes': len(out), 'parsed_records': n, 'refined_columns': changed}


def _palette_content(column, at, length, mode):
    k, at = vdecode(column, at); palette = column[at:at + k]; at += k
    if k > 256 or len(palette) != k or (not k and length):
        raise ValueError('invalid fixed-column alphabet')
    if mode == 2:
        ids = unpack_ids(column[at:], length, (k - 1).bit_length() if k else 0)
    else:
        counts = []; average = length // max(1, k)
        for _ in range(k):
            delta, at = read_signed(column, at); counts.append(average + delta)
        if any(count <= 0 for count in counts) or sum(counts) != length:
            raise ValueError('invalid fixed-column composition')
        ids = base.order_decode(column[at:], counts)
    if any(index >= k for index in ids):
        raise ValueError('fixed-column symbol outside alphabet')
    return bytes(palette[index] for index in ids)


def _decode_column(column, n):
    if not column:
        raise ValueError('missing fixed-column mode')
    mode = column[0]
    if mode == 0:
        return column[1:]
    width, at = vdecode(column, 1); length = width * n
    if mode == 1:
        content = column[at:]
    elif mode in (2, 3, 4):
        content = _palette_content(column, at, length, mode)
    else:
        raise ValueError('invalid fixed-column coding')
    if len(content) != length:
        raise ValueError('fixed column length mismatch')
    return b'\0' + b''.join(base.pack(content[index * width:(index + 1) * width]) for index in range(n))


def inverse(blob):
    if blob[:5] != RAW:
        raise ValueError('invalid fixed-column transform')
    nr, pos = vdecode(blob, 5); size = (nr + 7) // 8; flags = blob[pos:pos + size]; pos += size
    if len(flags) != size:
        raise ValueError('truncated flags')
    n = sum((flags[index // 8] >> (index % 8)) & 1 for index in range(nr)); _, pos = base.read(blob, pos)
    out = bytearray(base.RAW + blob[5:pos])
    for _ in range(9):
        column, pos = base.read(blob, pos); out.extend(base.pack(_decode_column(column, n)))
    if pos != len(blob):
        raise ValueError('trailing fixed columns')
    return base.inverse(bytes(out))


def encode(data, mode=1):
    import brotli
    raw, stats = transform(data, mode)
    frame = MAGIC + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + brotli.compress(raw, quality=11)
    return frame, {**stats, 'physical_bytes': len(frame)}


def decode(frame, max_output_bytes=None, memory_bytes=None):
    if len(frame) < 5 or frame[:5] != MAGIC:
        raise ValueError('invalid fixed-column frame')
    n, pos = vdecode(frame, 5)
    if max_output_bytes is not None and n > max_output_bytes:
        raise ValueError('fixed-column output limit')
    if memory_bytes is not None and n > memory_bytes:
        raise ValueError('fixed-column memory admission limit')
    if pos + 4 > len(frame):
        raise ValueError('truncated fixed-column frame')
    crc = int.from_bytes(frame[pos:pos + 4], 'big')
    data = inverse(_bounded_brotli(frame[pos + 4:], memory_bytes if memory_bytes is not None else n))
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('fixed-column checksum mismatch')
    return data
