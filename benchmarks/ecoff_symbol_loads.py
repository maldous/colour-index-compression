"""Normalize Alpha GP-relative loads using transmitted symbol identities.

The header GP and dynamic GOT mapping define a reversible reference coordinate
system. This is a byte transform, not an assumption that every instruction uses
that GP at runtime. Ambiguous slots, unknown names and unsupported inputs remain
literal. Global ordering depends only on transmitted symbol-table frequencies.
Layout: HP Tru64 Object File Specification (2002), sections 2.2.2 and 14.
"""
from collections import Counter, defaultdict
import struct
from benchmarks import ecoff_section_pointers as parent, ecoff_got as symbols

MAGIC = b'ECSL1'


def fields(data, mode):
    parsed = symbols.objects(data)
    frequency = Counter(name for _, _, _, table in parsed for name, _ in table if name)
    limit = 65536 if mode == 4 else 8192
    global_pool = (sorted(frequency) if mode == 3 else sorted(frequency, key=lambda n: (-frequency[n], n)))[:limit]
    global_index = {name: i for i, name in enumerate(global_pool)}
    rows = []
    for off, d, sec, table in parsed:
        if not all(name in sec for name in (b'.text', b'.got', b'.dynamic')):
            continue
        got_virtual = None
        for i in range(struct.unpack_from('<H', d, 2)[0]):
            name, _, virtual = struct.unpack_from('<8sQQ', d, 104 + i * 64)
            if name.rstrip(b'\0') == b'.got':
                got_virtual = virtual
        if got_virtual is None:
            continue
        gp = struct.unpack_from('<Q', d, 96)[0]
        _, got_size = sec[b'.got']; do, ds = sec[b'.dynamic']; tags = defaultdict(list)
        for pos in range(do, do + ds // 16 * 16, 16):
            tag, _, value = struct.unpack_from('<IIQ', d, pos)
            if not tag:
                break
            tags[tag].append(value & 0xffffffff)
        starts, symstarts = tags[0x7000000a], tags[0x70000013]
        if (not starts or len(starts) != len(symstarts) or tags[0x70000011] != [len(table)]
                or starts != sorted(set(starts)) or symstarts != sorted(set(symstarts))):
            continue
        slots = {}; valid = True; previous = -1
        for j, (g0, s0) in enumerate(zip(starts, symstarts)):
            end = symstarts[j + 1] if j + 1 < len(starts) else len(table)
            if s0 > end or end > len(table):
                valid = False; break
            for si in range(s0, end):
                gi = g0 + si - s0
                if gi <= previous or gi * 8 + 8 > got_size:
                    valid = False; break
                previous = gi; displacement = got_virtual + gi * 8 - gp
                if -32768 <= displacement <= 32767:
                    slots[displacement & 65535] = table[si][0]
            if not valid:
                break
        if not valid:
            continue
        by_name = defaultdict(list)
        for displacement, name in slots.items():
            if name:
                by_name[name].append(displacement)
        index = {name: i for i, name in enumerate(sorted(by_name)[:limit])} if mode == 1 else global_index
        scale = 1 if mode == 4 else 8
        forward = {values[0]: index[name] * scale for name, values in by_name.items() if len(values) == 1 and name in index}
        reverse = {encoded: original for original, encoded in forward.items()}
        to, ts = sec[b'.text']
        for pos in range(to, to + ts // 4 * 4, 4):
            word = struct.unpack_from('<I', d, pos)[0]
            if word >> 26 == 0x29 and (word >> 16) & 31 == 29:
                rows.append((off + pos, forward, reverse))
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
    return skeleton + metadata + len(metadata).to_bytes(8, 'little') + MAGIC, dict(
        mode=mode, original_bytes=len(data), eligible_loads=len(descriptors), normalized_loads=hits,
        membership_bytes=len(flags), metadata_bytes=len(metadata) + 13,
        ordering='local lexical' if mode == 1 else 'global lexical' if mode == 3 else 'global symbol frequency',
        alignment=1 if mode == 4 else 8)


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
