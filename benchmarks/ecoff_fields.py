"""Causal symbol/relocation residuals after exact ECOFF derived-table removal.

Name offsets predict the end of the previous transmitted name. Symbol values
predict the previous value with the same binding/section. No source constants
or external symbol dictionary are used. Every residual remains unrestricted.
"""
import struct
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_constraints as base

TRAILER = b'ECFC1'


def delta(value, previous, bits, inverse=False):
    mask = (1 << bits) - 1
    if inverse:
        signed = -(value // 2) - 1 if value & 1 else value // 2
        return (previous + signed) & mask
    signed = (value - previous) & mask
    if signed >> (bits - 1):
        signed -= 1 << bits
    return signed * 2 if signed >= 0 else -signed * 2 - 1


def transpose(raw, width, inverse=False):
    if len(raw) % width:
        raise ValueError('partial field matrix')
    rows = len(raw) // width
    if inverse:
        out = bytearray(len(raw))
        for i in range(width):
            out[i::width] = raw[i * rows:(i + 1) * rows]
        return bytes(out)
    return b''.join(raw[i::width] for i in range(width))


def fields(data, mode, inverse=False):
    sec = base.sections(data)
    if not all(k in sec for k in (b'.dynsym', b'.dynstr', b'.hash')):
        raise ValueError('missing symbol dependencies')
    so, ssize = sec[b'.dynsym']; to, tsize = sec[b'.dynstr']; ho, hsize = sec[b'.hash']
    if hsize < 8:
        raise ValueError('short hash header')
    n = struct.unpack_from('<I', data, ho + 4)[0]
    if not n or n * 24 > ssize:
        raise ValueError('symbol count outside table')
    out = bytearray(data)
    if inverse and mode >= 2:
        out[so:so + 24 * n] = transpose(data[so:so + 24 * n], 24, True)
    previous_name_end = 0; values = {}; exact = 0
    for i in range(n):
        where = so + 24 * i
        name, padding, value, size, info, other, shndx = struct.unpack_from('<IIQIBBH', out, where)
        if inverse:
            name = delta(name, previous_name_end, 32, True)
        if name >= tsize:
            raise ValueError('symbol name outside strings')
        end = data.find(b'\0', to + name, to + tsize)
        if end < 0:
            raise ValueError('unterminated symbol name')
        exact += name == previous_name_end
        encoded_name = name if inverse else delta(name, previous_name_end, 32)
        previous_name_end = end - to + 1
        if mode >= 2:
            key = (info, shndx)
            old = values.get(key, 0)
            if inverse:
                value = delta(value, old, 64, True)
                encoded_value = value
            else:
                encoded_value = delta(value, old, 64)
            values[key] = value
        else:
            encoded_value = value
        struct.pack_into('<IIQIBBH', out, where, encoded_name, padding, encoded_value, size, info, other, shndx)
    if not inverse and mode >= 2:
        out[so:so + 24 * n] = transpose(out[so:so + 24 * n], 24)
    relocations = 0
    if mode >= 3 and b'.rel.dyn' in sec:
        ro, rsize = sec[b'.rel.dyn']; length = rsize // 16 * 16
        if inverse:
            out[ro:ro + length] = transpose(out[ro:ro + length], 16, True)
        previous_address = 0; symbols = {}
        for p in range(ro, ro + length, 16):
            address, info, reserved = struct.unpack_from('<QII', out, p)
            kind = info & 255; symbol = info >> 8; old = symbols.get(kind, 0)
            if inverse:
                address = delta(address, previous_address, 64, True)
                symbol = delta(symbol, old, 24, True)
                encoded_address, encoded_symbol = address, symbol
            else:
                encoded_address = delta(address, previous_address, 64)
                encoded_symbol = delta(symbol, old, 24)
            struct.pack_into('<QII', out, p, encoded_address, (encoded_symbol << 8) | kind, reserved)
            previous_address = address; symbols[kind] = symbol; relocations += 1
        if not inverse:
            out[ro:ro + length] = transpose(out[ro:ro + length], 16)
    return bytes(out), dict(symbols=n, exact_name_predictions=exact, relocation_rows=relocations)


def transform(data, mode=1):
    if mode not in range(4):
        raise ValueError('invalid field mode')
    raw, stats = base.transform(data, 3)
    out = bytearray(raw); changes = []
    totals = dict(symbols=0, exact_name_predictions=0, relocation_rows=0)
    if mode:
        for offset, size in base.objects(data):
            try:
                transformed, row = fields(raw[offset:offset + size], mode)
            except (ValueError, struct.error):
                continue
            out[offset:offset + size] = transformed
            changes.append((offset, size))
            for k, v in row.items():
                totals[k] += v
    metadata = bytearray([mode]) + vencode(len(changes)); previous_end = 0
    for offset, size in changes:
        metadata.extend(vencode(offset - previous_end)); metadata.extend(vencode(size)); previous_end = offset + size
    out.extend(metadata); out.extend(len(metadata).to_bytes(8, 'little')); out.extend(TRAILER)
    return bytes(out), dict(**stats, field_mode=mode, field_objects=len(changes), field_metadata_bytes=len(metadata) + 13,
                           final_transformed_bytes=len(out), **totals)


def inverse(raw):
    if len(raw) < 15 or raw[-5:] != TRAILER:
        raise ValueError('invalid ECOFF field trailer')
    length = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - 13 - length
    if start < 0 or length < 2:
        raise ValueError('invalid ECOFF field metadata length')
    meta = raw[start:-13]; mode = meta[0]; n, pos = vdecode(meta, 1)
    if mode not in range(4) or (not mode and n) or n > start // 104:
        raise ValueError('invalid ECOFF field policy')
    out = bytearray(raw[:start]); previous_end = 0
    for _ in range(n):
        gap, pos = vdecode(meta, pos); size, pos = vdecode(meta, pos); offset = previous_end + gap
        if offset + size > len(out):
            raise ValueError('ECOFF field object outside frame')
        restored, _ = fields(bytes(out[offset:offset + size]), mode, True)
        out[offset:offset + size] = restored; previous_end = offset + size
    if pos != len(meta):
        raise ValueError('unused ECOFF field metadata')
    return base.inverse(bytes(out))
