"""Ordered procedure-address constraints after the section-pointer transform."""
from math import log2
import struct

from . import ecoff_constraints as base, ecoff_section_pointers as parent, ordered_subset as subset
from .multinomial import vdecode, vencode

MAGIC = b"ECPD1"
BLOCK = 64


def tables(data):
    descriptors = []
    for offset, size in base.objects(data):
        section = base.sections(data[offset:offset + size]).get(b".pdata")
        if section and section[1] >= 8:
            start, length = section
            descriptors.append((offset + start, length // 8))
    return descriptors


def _encode_table(words, out, start, mode, metadata):
    if mode == 1:
        previous = 0
        for index, word in enumerate(words):
            struct.pack_into("<I", out, start + 8 * index, (word - previous) & 0xffffffff)
            previous = word
        return 0, 0, 0.0, 0
    if mode < 2:
        return 0, 0, 0.0, 0
    values = [word >> 2 for word in words]
    valid = all(left < right for left, right in zip(values, values[1:]))
    metadata.append(int(valid))
    if not valid:
        return 0, 0, 0.0, 0
    flags = bytearray((len(words) + 3) // 4)
    for index, word in enumerate(words):
        flags[index // 4] |= (word & 3) << (2 * (index % 4))
        struct.pack_into("<I", out, start + 8 * index, 0)
    metadata.extend(flags)
    metadata.extend(vencode(values[0]))
    previous = values[0]
    bits = 0.0
    for begin in range(1, len(values), BLOCK):
        block = values[begin:begin + BLOCK]
        delta = block[-1] - previous
        metadata.extend(vencode(delta))
        positions = [value - previous - 1 for value in block[:-1]]
        metadata.extend(subset.encode(positions, delta - 1, mode - 2))
        bits += log2(subset.choose(delta - 1, len(positions)))
        previous = block[-1]
    return 1, len(words), bits, 30 * len(words)


def transform(data, mode=2):
    if mode not in range(4):
        raise ValueError("invalid procedure constraint mode")
    skeleton, _ = parent.transform(data, 4)
    out = bytearray(skeleton)
    descriptors = tables(skeleton)
    metadata = bytearray([mode])
    selected = events = raw_bits = 0
    bits = 0.0
    for start, count in descriptors:
        words = [struct.unpack_from("<I", skeleton, start + 8 * index)[0] for index in range(count)]
        table_selected, table_events, table_bits, table_raw_bits = _encode_table(words, out, start, mode, metadata)
        selected += table_selected
        events += table_events
        bits += table_bits
        raw_bits += table_raw_bits
    raw = bytes(out) + metadata + len(metadata).to_bytes(8, "little") + MAGIC
    return raw, {"mode": mode, "original_bytes": len(data), "transformed_bytes": len(raw),
                 "tables": len(descriptors), "selected_tables": selected,
                 "constrained_addresses": events, "unrestricted_component_bits": raw_bits,
                 "subset_combinatorial_bits": bits, "paid_metadata_bytes": len(metadata) + 13}


def _restore_delta_table(out, start, count):
    previous = 0
    for index in range(count):
        value = (struct.unpack_from("<I", out, start + 8 * index)[0] + previous) & 0xffffffff
        struct.pack_into("<I", out, start + 8 * index, value)
        previous = value


def _restore_subset_table(out, start, count, metadata, position, mode):
    if position >= len(metadata) or metadata[position] > 1:
        raise ValueError("invalid procedure table selector")
    selected = metadata[position]
    position += 1
    if not selected:
        return position
    length = (count + 3) // 4
    flags = metadata[position:position + length]
    position += length
    if len(flags) != length:
        raise ValueError("truncated procedure flags")
    first, position = vdecode(metadata, position)
    if first >= 1 << 30:
        raise ValueError("procedure address outside field")
    values = [first]
    previous = first
    for begin in range(1, count, BLOCK):
        block_count = min(BLOCK, count - begin)
        delta, position = vdecode(metadata, position)
        if delta < block_count or previous + delta >= 1 << 30:
            raise ValueError("invalid procedure endpoint")
        positions, position = subset.decode(metadata, position, delta - 1, block_count - 1, mode - 2)
        values.extend(previous + value + 1 for value in positions)
        previous += delta
        values.append(previous)
    for index, value in enumerate(values):
        where = start + 8 * index
        if any(out[where:where + 4]):
            raise ValueError("procedure skeleton is not zero")
        word = (value << 2) | ((flags[index // 4] >> (2 * (index % 4))) & 3)
        struct.pack_into("<I", out, where, word)
    return position


def inverse(raw):
    if len(raw) < 14 or raw[-5:] != MAGIC:
        raise ValueError("invalid procedure constraint trailer")
    size = int.from_bytes(raw[-13:-5], "little")
    start = len(raw) - 13 - size
    if start < 0 or size < 1:
        raise ValueError("invalid procedure constraint metadata")
    metadata = raw[start:-13]
    mode = metadata[0]
    if mode not in range(4):
        raise ValueError("invalid procedure constraint mode")
    out = bytearray(raw[:start])
    position = 1
    for where, count in tables(out):
        if mode == 1:
            _restore_delta_table(out, where, count)
        elif mode >= 2:
            position = _restore_subset_table(out, where, count, metadata, position, mode)
    if position != len(metadata):
        raise ValueError("unused procedure metadata")
    return parent.inverse(bytes(out))
