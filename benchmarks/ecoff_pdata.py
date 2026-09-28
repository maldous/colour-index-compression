"""Ordered procedure-address constraints after the section-pointer transform.

Only strictly increasing 30-bit address components use subset coding. Low bits,
all endpoints and exceptional tables are preserved. Arithmetic and rank modes
receive exactly the same subset bounds and occupancy counts. This is a known
combinadic representation, tested here as an executable structural constraint.
"""
from math import log2
import struct
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_section_pointers as parent, ecoff_constraints as base, ordered_subset as subset

MAGIC = b'ECPD1'
BLOCK = 64


def tables(data):
    out = []
    for offset, size in base.objects(data):
        section = base.sections(data[offset:offset + size]).get(b'.pdata')
        if section and section[1] >= 8:
            start, length = section; out.append((offset + start, length // 8))
    return out


def transform(data, mode=2):
    if mode not in range(4):
        raise ValueError('invalid procedure constraint mode')
    skeleton, _ = parent.transform(data, 4)
    out = bytearray(skeleton); descriptors = tables(skeleton)
    metadata = bytearray([mode]); selected = 0; events = 0; bits = 0.0; raw_bits = 0
    for start, n in descriptors:
        words = [struct.unpack_from('<I', skeleton, start + 8 * i)[0] for i in range(n)]
        if mode == 1:
            previous = 0
            for i, word in enumerate(words):
                struct.pack_into('<I', out, start + 8 * i, (word - previous) & 0xffffffff); previous = word
        elif mode >= 2:
            values = [word >> 2 for word in words]
            valid = all(a < b for a, b in zip(values, values[1:]))
            metadata.append(int(valid))
            if not valid:
                continue
            selected += 1; events += n; raw_bits += 30 * n
            flags = bytearray((n + 3) // 4)
            for i, word in enumerate(words):
                flags[i // 4] |= (word & 3) << (2 * (i % 4)); struct.pack_into('<I', out, start + 8 * i, 0)
            metadata.extend(flags); metadata.extend(vencode(values[0])); previous = values[0]
            for begin in range(1, n, BLOCK):
                block = values[begin:begin + BLOCK]; delta = block[-1] - previous
                metadata.extend(vencode(delta)); universe = delta - 1
                positions = [value - previous - 1 for value in block[:-1]]
                metadata.extend(subset.encode(positions, universe, mode - 2))
                bits += log2(subset.choose(universe, len(positions))); previous = block[-1]
    raw = bytes(out) + metadata + len(metadata).to_bytes(8, 'little') + MAGIC
    return raw, dict(mode=mode, original_bytes=len(data), transformed_bytes=len(raw), tables=len(descriptors),
                     selected_tables=selected, constrained_addresses=events, unrestricted_component_bits=raw_bits,
                     subset_combinatorial_bits=bits, paid_metadata_bytes=len(metadata) + 13)


def inverse(raw):
    if len(raw) < 14 or raw[-5:] != MAGIC:
        raise ValueError('invalid procedure constraint trailer')
    size = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - 13 - size
    if start < 0 or size < 1:
        raise ValueError('invalid procedure constraint metadata')
    meta = raw[start:-13]; mode = meta[0]; pos = 1
    if mode not in range(4):
        raise ValueError('invalid procedure constraint mode')
    out = bytearray(raw[:start])
    for where, n in tables(out):
        if mode == 1:
            previous = 0
            for i in range(n):
                value = (struct.unpack_from('<I', out, where + 8 * i)[0] + previous) & 0xffffffff
                struct.pack_into('<I', out, where + 8 * i, value); previous = value
        elif mode >= 2:
            if pos >= len(meta) or meta[pos] > 1:
                raise ValueError('invalid procedure table selector')
            selected = meta[pos]; pos += 1
            if not selected:
                continue
            length = (n + 3) // 4; flags = meta[pos:pos + length]; pos += length
            if len(flags) != length:
                raise ValueError('truncated procedure flags')
            first, pos = vdecode(meta, pos)
            if first >= 1 << 30:
                raise ValueError('procedure address outside field')
            values = [first]; previous = first
            for begin in range(1, n, BLOCK):
                count = min(BLOCK, n - begin); delta, pos = vdecode(meta, pos)
                if delta < count or previous + delta >= 1 << 30:
                    raise ValueError('invalid procedure endpoint')
                positions, pos = subset.decode(meta, pos, delta - 1, count - 1, mode - 2)
                values.extend(previous + value + 1 for value in positions); previous += delta; values.append(previous)
            for i, value in enumerate(values):
                if any(out[where + 8 * i:where + 8 * i + 4]):
                    raise ValueError('procedure skeleton is not zero')
                word = (value << 2) | ((flags[i // 4] >> (2 * (i % 4))) & 3)
                struct.pack_into('<I', out, where + 8 * i, word)
    if pos != len(meta):
        raise ValueError('unused procedure metadata')
    return parent.inverse(bytes(out))
