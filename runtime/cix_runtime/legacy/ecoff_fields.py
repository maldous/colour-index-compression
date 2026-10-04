"""Causal symbol/relocation residuals after exact ECOFF derived-table removal.

Name offsets predict the end of the previous transmitted name. Symbol values
predict the previous value with the same binding/section. No source constants
or external symbol dictionary are used. Every residual remains unrestricted.
"""
import struct
from .multinomial import vencode, vdecode
from . import ecoff_constraints as base

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


def _symbol_row(out, where, string_offset, string_size, previous_name_end, values, mode, inverse):
    name, padding, value, size, info, other, shndx = struct.unpack_from("<IIQIBBH", out, where)
    if inverse:
        name = delta(name, previous_name_end, 32, True)
    if name >= string_size:
        raise ValueError("symbol name outside strings")
    end = out.find(b"\0", string_offset + name, string_offset + string_size)
    if end < 0:
        raise ValueError("unterminated symbol name")
    exact = name == previous_name_end
    encoded_name = name if inverse else delta(name, previous_name_end, 32)
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
    struct.pack_into("<IIQIBBH", out, where, encoded_name, padding, encoded_value, size, info, other, shndx)
    return end - string_offset + 1, exact


def _symbol_fields(out, symbol_offset, string_offset, string_size, count, mode, inverse):
    if inverse and mode >= 2:
        out[symbol_offset:symbol_offset + 24 * count] = transpose(out[symbol_offset:symbol_offset + 24 * count], 24, True)
    previous_name_end = 0
    values = {}
    exact = 0
    for index in range(count):
        where = symbol_offset + 24 * index
        previous_name_end, matched = _symbol_row(out, where, string_offset, string_size,
                                                  previous_name_end, values, mode, inverse)
        exact += matched
    if not inverse and mode >= 2:
        out[symbol_offset:symbol_offset + 24 * count] = transpose(out[symbol_offset:symbol_offset + 24 * count], 24)
    return exact

def _relocation_fields(out, sections, mode, inverse):
    if mode < 3 or b".rel.dyn" not in sections:
        return 0
    offset, size = sections[b".rel.dyn"]
    length = size // 16 * 16
    if inverse:
        out[offset:offset + length] = transpose(out[offset:offset + length], 16, True)
    previous_address = 0
    symbols = {}
    for position in range(offset, offset + length, 16):
        address, info, reserved = struct.unpack_from("<QII", out, position)
        kind, symbol = info & 255, info >> 8
        old = symbols.get(kind, 0)
        if inverse:
            address = delta(address, previous_address, 64, True)
            symbol = delta(symbol, old, 24, True)
        encoded_address = address if inverse else delta(address, previous_address, 64)
        encoded_symbol = symbol if inverse else delta(symbol, old, 24)
        struct.pack_into("<QII", out, position, encoded_address, (encoded_symbol << 8) | kind, reserved)
        previous_address = address
        symbols[kind] = symbol
    if not inverse:
        out[offset:offset + length] = transpose(out[offset:offset + length], 16)
    return length // 16


def fields(data, mode, inverse=False):
    sections = base.sections(data)
    if not all(key in sections for key in (b".dynsym", b".dynstr", b".hash")):
        raise ValueError("missing symbol dependencies")
    symbol_offset, symbol_size = sections[b".dynsym"]
    string_offset, string_size = sections[b".dynstr"]
    hash_offset, hash_size = sections[b".hash"]
    if hash_size < 8:
        raise ValueError("short hash header")
    count = struct.unpack_from("<I", data, hash_offset + 4)[0]
    if not count or count * 24 > symbol_size:
        raise ValueError("symbol count outside table")
    out = bytearray(data)
    exact = _symbol_fields(out, symbol_offset, string_offset, string_size, count, mode, inverse)
    relocations = _relocation_fields(out, sections, mode, inverse)
    return bytes(out), {"symbols": count, "exact_name_predictions": exact, "relocation_rows": relocations}

def _transform_object(raw, offset, size, mode):
    try:
        return fields(raw[offset:offset + size], mode)
    except (ValueError, struct.error):
        return None


def _field_changes(data, raw, mode):
    out = bytearray(raw)
    changes = []
    totals = {"symbols": 0, "exact_name_predictions": 0, "relocation_rows": 0}
    if not mode:
        return out, changes, totals
    for offset, size in base.objects(data):
        result = _transform_object(raw, offset, size, mode)
        if result is None:
            continue
        transformed, row = result
        out[offset:offset + size] = transformed
        changes.append((offset, size))
        for key, value in row.items():
            totals[key] += value
    return out, changes, totals


def _metadata(mode, changes):
    metadata = bytearray([mode]) + vencode(len(changes))
    previous_end = 0
    for offset, size in changes:
        metadata.extend(vencode(offset - previous_end))
        metadata.extend(vencode(size))
        previous_end = offset + size
    return metadata


def transform(data, mode=1):
    if mode not in range(4):
        raise ValueError("invalid field mode")
    raw, stats = base.transform(data, 3)
    out, changes, totals = _field_changes(data, raw, mode)
    metadata = _metadata(mode, changes)
    out.extend(metadata)
    out.extend(len(metadata).to_bytes(8, "little"))
    out.extend(TRAILER)
    return bytes(out), {**stats, "field_mode": mode, "field_objects": len(changes),
                        "field_metadata_bytes": len(metadata) + 13,
                        "final_transformed_bytes": len(out), **totals}

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
