"""Normalize Alpha GP-relative loads using transmitted symbol identities.

The header GP and dynamic GOT mapping define a reversible reference coordinate
system. This is a byte transform, not an assumption that every instruction uses
that GP at runtime. Ambiguous slots, unknown names and unsupported inputs remain
literal. Global ordering depends only on transmitted symbol-table frequencies.
Layout: HP Tru64 Object File Specification (2002), sections 2.2.2 and 14.
"""
from collections import Counter, defaultdict
import struct
from . import ecoff_section_pointers as parent, ecoff_got as symbols

MAGIC = b'ECSL1'


def _global_index(parsed, mode):
    frequency = Counter(name for _, _, _, table in parsed for name, _ in table if name)
    limit = 65536 if mode == 4 else 8192
    pool = sorted(frequency) if mode == 3 else sorted(frequency, key=lambda name: (-frequency[name], name))
    return {name: index for index, name in enumerate(pool[:limit])}, limit


def _got_virtual(blob):
    for index in range(struct.unpack_from("<H", blob, 2)[0]):
        name, _, virtual = struct.unpack_from("<8sQQ", blob, 104 + index * 64)
        if name.rstrip(b"\0") == b".got":
            return virtual
    return None


def _dynamic_tags(blob, sections):
    offset, size = sections[b".dynamic"]
    tags = defaultdict(list)
    for position in range(offset, offset + size // 16 * 16, 16):
        tag, _, value = struct.unpack_from("<IIQ", blob, position)
        if not tag:
            break
        tags[tag].append(value & 0xffffffff)
    starts, symbol_starts = tags[0x7000000a], tags[0x70000013]
    return tags, starts, symbol_starts


def _slot_rows(starts, symbol_starts, table, got_size):
    if (not starts or len(starts) != len(symbol_starts) or symbol_starts != sorted(set(symbol_starts))
            or starts != sorted(set(starts))):
        return None
    previous = -1
    rows = []
    for index, (got_start, symbol_start) in enumerate(zip(starts, symbol_starts)):
        end = symbol_starts[index + 1] if index + 1 < len(starts) else len(table)
        if symbol_start > end or end > len(table):
            return None
        for symbol in range(symbol_start, end):
            got_index = got_start + symbol - symbol_start
            if got_index <= previous or got_index * 8 + 8 > got_size:
                return None
            previous = got_index
            rows.append((got_index, symbol))
    return rows


def _dynamic_slots(blob, sections, table, got_virtual):
    _, got_size = sections[b".got"]
    tags, starts, symbol_starts = _dynamic_tags(blob, sections)
    if tags[0x70000011] != [len(table)]:
        return None
    rows = _slot_rows(starts, symbol_starts, table, got_size)
    if rows is None:
        return None
    gp = struct.unpack_from("<Q", blob, 96)[0]
    slots = {}
    for got_index, symbol in rows:
        displacement = got_virtual + got_index * 8 - gp
        if -32768 <= displacement <= 32767:
            slots[displacement & 65535] = table[symbol][0]
    return slots

def _maps(slots, mode, global_index, limit):
    by_name = defaultdict(list)
    for displacement, name in slots.items():
        if name:
            by_name[name].append(displacement)
    index = {name: position for position, name in enumerate(sorted(by_name)[:limit])} if mode == 1 else global_index
    scale = 1 if mode == 4 else 8
    forward = {values[0]: index[name] * scale for name, values in by_name.items() if len(values) == 1 and name in index}
    return forward, {encoded: original for original, encoded in forward.items()}


def _object_fields(offset, blob, sections, table, mode, global_index, limit):
    if not all(name in sections for name in (b".text", b".got", b".dynamic")):
        return []
    got_virtual = _got_virtual(blob)
    if got_virtual is None:
        return []
    slots = _dynamic_slots(blob, sections, table, got_virtual)
    if slots is None:
        return []
    forward, reverse = _maps(slots, mode, global_index, limit)
    text_offset, text_size = sections[b".text"]
    rows = []
    for position in range(text_offset, text_offset + text_size // 4 * 4, 4):
        word = struct.unpack_from("<I", blob, position)[0]
        if word >> 26 == 0x29 and (word >> 16) & 31 == 29:
            rows.append((offset + position, forward, reverse))
    return rows


def fields(data, mode):
    parsed = symbols.objects(data)
    global_index, limit = _global_index(parsed, mode)
    rows = []
    for offset, blob, sections, table in parsed:
        rows.extend(_object_fields(offset, blob, sections, table, mode, global_index, limit))
    return rows

def transform(data, mode=2):
    if mode not in range(5):
        raise ValueError('invalid symbol-load mode')
    descriptors = fields(data, mode); flags = bytearray((len(descriptors) + 7) // 8) if mode else bytearray()
    out = bytearray(data); hits = 0
    for i, (where, forward, _) in enumerate(descriptors):
        value = struct.unpack_from('<H', data, where)[0]
        if value not in forward:
            continue
        hits += 1
        if mode:
            flags[i // 8] |= 1 << (i % 8)
            struct.pack_into('<H', out, where, forward[value])
    skeleton, _ = parent.transform(bytes(out), 4)
    metadata = bytes([mode]) + symbols.pack(bytes(flags))
    if mode == 1:
        ordering = "local lexical"
    elif mode == 3:
        ordering = "global lexical"
    else:
        ordering = "global symbol frequency"
    alignment = 1 if mode == 4 else 8
    return skeleton + metadata + len(metadata).to_bytes(8, "little") + MAGIC, {
        "mode": mode, "original_bytes": len(data), "eligible_loads": len(descriptors),
        "normalized_loads": hits, "membership_bytes": len(flags),
        "metadata_bytes": len(metadata) + 13, "ordering": ordering, "alignment": alignment,
    }


def inverse(raw):
    if len(raw) < 15 or raw[-5:] != MAGIC:
        raise ValueError('invalid symbol-load trailer')
    size = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - 13 - size
    if start < 0 or size < 2:
        raise ValueError('invalid symbol-load metadata')
    metadata = raw[start:-13]; mode = metadata[0]
    if mode not in range(5):
        raise ValueError('invalid symbol-load mode')
    flags, pos = symbols.read(metadata, 1)
    if pos != len(metadata):
        raise ValueError('unused symbol-load metadata')
    data = parent.inverse(raw[:start]); descriptors = fields(data, mode)
    if len(flags) != ((len(descriptors) + 7) // 8 if mode else 0):
        raise ValueError('symbol-load flag count mismatch')
    out = bytearray(data)
    for i, (where, _, reverse) in enumerate(descriptors):
        if mode and flags[i // 8] & (1 << (i % 8)):
            encoded = struct.unpack_from('<H', out, where)[0]
            if encoded not in reverse:
                raise ValueError('symbol outside reachable load alphabet')
            struct.pack_into('<H', out, where, reverse[encoded])
    return bytes(out)
