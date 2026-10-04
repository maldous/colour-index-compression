"""Restrict relocated data pointers using transmitted symbol definitions.

Relocation symbol indices identify a small candidate alphabet; definitions in
other objects add candidates without an external dictionary. Every exception is
literal, and all field positions remain fixed for the parent PAQ/Brotli models.
"""
from collections import Counter, defaultdict
import struct
from . import ecoff_got as parent

MAGIC = b'ECRP1'


def _definitions(parsed, shared):
    definitions = defaultdict(Counter)
    if shared:
        for _, _, _, symbols in parsed:
            for name, value in symbols:
                if value:
                    definitions[name][value] += 1
    return definitions


def _regions(blob):
    regions = []
    for index in range(struct.unpack_from("<H", blob, 2)[0]):
        name, _, virtual, size, pointer, _, _, _, _, _ = struct.unpack_from("<8sQQQQQQHHI", blob, 104 + index * 64)
        if name.rstrip(b"\0") in (b".rdata", b".data", b".sdata") and pointer:
            regions.append((virtual, size, pointer))
    return regions


def _location(address, regions):
    matches = [pointer + address - virtual for virtual, size, pointer in regions
               if virtual <= address and address + 8 <= virtual + size]
    return matches[0] if len(matches) == 1 else None


def _object_candidates(offset, blob, sections, symbols, definitions, shared):
    if b".rel.dyn" not in sections:
        return []
    regions = _regions(blob)
    start, size = sections[b".rel.dyn"]
    alphabets = {}
    result = []
    for position in range(start, start + size // 16 * 16, 16):
        address, info, _ = struct.unpack_from("<QII", blob, position)
        symbol = info >> 8
        if info & 255 != 2 or symbol >= len(symbols):
            continue
        location = _location(address, regions)
        if location is None:
            continue
        if symbol not in alphabets:
            name, value = symbols[symbol]
            alternatives = sorted(definitions[name], key=lambda candidate, symbol_name=name: (-definitions[symbol_name][candidate], candidate)) if shared else []
            alphabets[symbol] = [value] + [candidate for candidate in alternatives if candidate != value]
        result.append((offset + location, alphabets[symbol], int(symbols[symbol][1] == 0)))
    return result


def _without_overlaps(fields):
    fields.sort(key=lambda field: field[0])
    blocked = set()
    for index, (left, right) in enumerate(zip(fields, fields[1:])):
        if left[0] + 8 > right[0]:
            blocked.update((index, index + 1))
    return [field for index, field in enumerate(fields) if index not in blocked]


def candidates(data, shared=True):
    parsed = parent.objects(data)
    definitions = _definitions(parsed, shared)
    fields = []
    for offset, blob, sections, symbols in parsed:
        fields.extend(_object_candidates(offset, blob, sections, symbols, definitions, shared))
    return _without_overlaps(fields)

def transform(data, mode=1, shared=True):
    if mode not in range(6): raise ValueError('invalid relocated-pointer representation')
    fields=candidates(data,shared);out=bytearray(data);flags=bytearray((len(fields)+7)//8) if mode==1 else bytearray()
    digits=[];alphabets=[];contexts=[];exceptions=bytearray();hits=0
    for i,(where,options,context) in enumerate(fields):
        value=struct.unpack_from('<Q',data,where)[0];digit=options.index(value) if value in options else len(options);hits+=digit<len(options)
        if mode==1 and digit<len(options):
            flags[i//8]|=1<<(i%8);struct.pack_into('<Q',out,where,digit)
        elif mode>=2:
            out[where:where+8]=bytes(8);digits.append(digit);alphabets.append(len(options)+1);contexts.append(context)
            if digit==len(options):exceptions.extend(data[where:where+8])
    if mode>=2:choices,uncertainty,model_bits=parent.encode_choices(digits,alphabets,contexts,mode-2)
    else:choices=b'';uncertainty=0.;model_bits=None
    skeleton,_=parent.transform(bytes(out),3)
    metadata=bytes([mode,int(shared)])+parent.pack(bytes(flags))+parent.pack(choices)+bytes(exceptions)
    raw=skeleton+metadata+len(metadata).to_bytes(8,'little')+MAGIC
    return raw, {
        "mode": mode, "shared": shared, "original_bytes": len(data),
        "transformed_bytes": len(raw), "mapped_pointers": len(fields),
        "in_candidates": hits, "membership_bytes": len(flags),
        "choice_bytes": len(choices), "exception_bytes": len(exceptions),
        "candidate_combinatorial_bits": uncertainty, "choice_model_bits": model_bits,
    }


def _restore_member(out, where, options, mode, flags, index, digits, event, metadata, position):
    if mode == 1 and flags[index // 8] & (1 << (index % 8)):
        digit = struct.unpack_from("<Q", out, where)[0]
        if digit >= len(options):
            raise ValueError("pointer index outside alphabet")
        struct.pack_into("<Q", out, where, options[digit])
        return event, position
    if mode < 2:
        return event, position
    if any(out[where:where + 8]):
        raise ValueError("pointer skeleton is not zero")
    digit = digits[index]
    if digit == len(options):
        if position + 8 > len(metadata):
            raise ValueError("truncated pointer exception")
        out[where:where + 8] = metadata[position:position + 8]
        return event, position + 8
    struct.pack_into("<Q", out, where, options[digit])
    return event, position


def inverse(raw):
    if len(raw) < 17 or raw[-5:] != MAGIC:
        raise ValueError("invalid relocated-pointer trailer")
    size = int.from_bytes(raw[-13:-5], "little")
    start = len(raw) - 13 - size
    if start < 0 or size < 4:
        raise ValueError("invalid pointer metadata size")
    metadata = raw[start:-13]
    mode, shared = metadata[:2]
    if mode not in range(6) or shared not in (0, 1):
        raise ValueError("invalid pointer model")
    data = parent.inverse(raw[:start])
    fields = candidates(data, bool(shared))
    flags, position = parent.read(metadata, 2)
    choices, position = parent.read(metadata, position)
    if len(flags) != ((len(fields) + 7) // 8 if mode == 1 else 0):
        raise ValueError("pointer membership length mismatch")
    if mode < 2 and choices:
        raise ValueError("unexpected pointer choices")
    digits = parent.decode_choices(choices, [len(options) + 1 for _, options, _ in fields], [context for _, _, context in fields], mode - 2) if mode >= 2 else []
    out = bytearray(data)
    event = 0
    for index, (where, options, _) in enumerate(fields):
        event, position = _restore_member(out, where, options, mode, flags, index, digits, event, metadata, position)
    if position != len(metadata):
        raise ValueError("unused pointer metadata")
    return bytes(out)
