"""Section/function alphabets followed by causal pointer-residual prediction."""
from math import log2
import struct

from . import ecoff_call_entries as uniform, ecoff_pointer_deltas as parent

MAGIC = b"ECSP1"
WORD_MASK = (1 << 64) - 1
CODE_SECTIONS = (b".text", b".init", b".fini")


def _sections(blob):
    result = {}
    for index in range(struct.unpack_from("<H", blob, 2)[0]):
        name, _, virtual, size, pointer, _, _, _, _, _ = struct.unpack_from("<8sQQQQQQHHI", blob, 104 + 64 * index)
        if virtual + size <= 1 << 64:
            result[name.rstrip(b"\0")] = (virtual, size, pointer)
    return result


def _functions(blob, sections, symbols):
    values = {value for _, value in symbols}
    pdata = sections.get(b".pdata")
    if pdata and pdata[2]:
        virtual, size, pointer = pdata
        for position in range(pointer, pointer + size // 8 * 8, 8):
            values.add((virtual + (struct.unpack_from("<i", blob, position)[0] & ~3)) & WORD_MASK)
    return values


def _pools(sections, functions):
    pools = {}
    for name, (virtual, size, _) in sections.items():
        if name not in CODE_SECTIONS:
            continue
        pool = tuple(sorted(value for value in functions if virtual <= value < virtual + size and (value - virtual) % 4 == 0))
        if 0 < len(pool) <= 65535:
            pools[name] = pool
    return pools


def _data_location(address, sections):
    positions = [pointer + address - virtual for name, (virtual, size, pointer) in sections.items()
                 if name in (b".rdata", b".data", b".sdata") and pointer and virtual <= address and address + 8 <= virtual + size]
    return positions[0] if len(positions) == 1 else None


def _descriptor(address, info, symbols, sections, pools, mode):
    symbol = info >> 8
    if info & 255 != 2 or symbol >= len(symbols):
        return None
    name, declared = symbols[symbol]
    if name not in sections or (mode in (0, 1, 2, 5, 6) and name not in CODE_SECTIONS):
        return None
    location = _data_location(address, sections)
    if location is None:
        return None
    virtual, size, _ = sections[name]
    use_functions = mode in (0, 1, 5, 6) or (mode == 4 and name in CODE_SECTIONS)
    pool = pools.get(name)
    if use_functions and pool is None:
        return None
    alphabet = pool if use_functions else (virtual, (size + 3) // 4)
    if not alphabet or (not use_functions and not alphabet[1]):
        return None
    return location, declared, use_functions, alphabet


def _object_fields(offset, blob, section_map, symbols, mode):
    if b".rel.dyn" not in section_map:
        return []
    sections = _sections(blob)
    pools = _pools(sections, _functions(blob, sections, symbols))
    relocation_offset, relocation_size = section_map[b".rel.dyn"]
    result = []
    for position in range(relocation_offset, relocation_offset + relocation_size // 16 * 16, 16):
        address, info, _ = struct.unpack_from("<QII", blob, position)
        descriptor = _descriptor(address, info, symbols, sections, pools, mode)
        if descriptor is not None:
            location, declared, use_functions, alphabet = descriptor
            result.append((offset + location, declared, use_functions, alphabet))
    return result

def _without_overlaps(rows):
    rows.sort(key=lambda row: row[0])
    blocked = set()
    for index, (left, right) in enumerate(zip(rows, rows[1:])):
        if left[0] + 8 > right[0]:
            blocked.update((index, index + 1))
    return [row for index, row in enumerate(rows) if index not in blocked]


def fields(data, mode):
    rows = []
    for offset, blob, section_map, symbols in parent.parent.objects(data):
        rows.extend(_object_fields(offset, blob, section_map, symbols, mode))
    return _without_overlaps(rows)


def _digit(value, is_function, pool, indices):
    if is_function:
        return indices[id(pool)].get(value), len(pool)
    virtual, count = pool
    valid = virtual <= value and (value - virtual) % 4 == 0 and (value - virtual) // 4 < count
    return ((value - virtual) // 4 if valid else None), count


def _encode_descriptor(out, flags, digits, alphabets, index, descriptor, value, mode, indices):
    where, declared, is_function, pool = descriptor
    digit, count = _digit(value, is_function, pool, indices)
    if digit is None:
        return False, 0.0
    if mode:
        flags[index // 8] |= 1 << (index % 8)
        if mode in (5, 6):
            struct.pack_into("<Q", out, where, declared)
            digits.append(digit)
            alphabets.append(count)
        else:
            struct.pack_into("<Q", out, where, (declared + digit) & WORD_MASK)
    return True, log2(count)


def transform(data, mode=1):
    if mode not in range(7):
        raise ValueError("invalid section-pointer model")
    descriptors = fields(data, mode)
    flags = bytearray((len(descriptors) + 7) // 8) if mode else bytearray()
    out = bytearray(data)
    indices = {id(pool): {value: index for index, value in enumerate(pool)}
               for _, _, is_function, pool in descriptors if is_function}
    digits = []
    alphabets = []
    matches = 0
    restricted_bits = 0.0
    for index, descriptor in enumerate(descriptors):
        value = struct.unpack_from("<Q", data, descriptor[0])[0]
        matched, bits = _encode_descriptor(out, flags, digits, alphabets, index, descriptor, value, mode, indices)
        matches += matched
        restricted_bits += bits
    if mode == 5:
        choices, _, model_bits = parent.parent.encode_choices(digits, alphabets, [0] * len(digits), 1)
    elif mode == 6:
        choices, model_bits = uniform.arithmetic(digits, alphabets, [0] * len(digits), False)
    else:
        choices = b""
        model_bits = None
    skeleton, _ = parent.transform(bytes(out), 5)
    metadata = bytes([mode]) + parent.parent.pack(bytes(flags)) + parent.parent.pack(choices)
    raw = skeleton + metadata + len(metadata).to_bytes(8, "little") + MAGIC
    return raw, {"mode": mode, "original_bytes": len(data), "transformed_bytes": len(raw),
                 "eligible_pointers": len(descriptors), "in_candidates": matches,
                 "membership_bytes": len(flags), "choice_bytes": len(choices),
                 "unrestricted_word_bits": 64 * matches, "candidate_combinatorial_bits": restricted_bits,
                 "choice_model_bits": model_bits}


def _digits(metadata, mode, descriptors, flags):
    alphabets = [len(pool) for index, (_, _, _, pool) in enumerate(descriptors)
                 if mode in (5, 6) and flags[index // 8] & (1 << (index % 8))]
    if mode == 5:
        return parent.parent.decode_choices(metadata, alphabets, [0] * len(alphabets), 1)
    if mode == 6:
        return uniform.arithmetic(None, alphabets, [0] * len(alphabets), False, metadata)[0]
    return []


def _restore_descriptor(out, descriptor, mode, flag, digits, event):
    if not mode or not flag:
        return event
    where, declared, is_function, pool = descriptor
    encoded = struct.unpack_from("<Q", out, where)[0]
    if mode in (5, 6):
        if encoded != declared:
            raise ValueError("section-pointer skeleton differs from declared base")
        digit = digits[event]
        event += 1
    else:
        digit = (encoded - declared) & WORD_MASK
    if is_function:
        if digit >= len(pool):
            raise ValueError("function index outside alphabet")
        value = pool[digit]
    else:
        virtual, count = pool
        if digit >= count:
            raise ValueError("section index outside interval")
        value = virtual + digit * 4
    struct.pack_into("<Q", out, where, value)
    return event


def inverse(raw):
    if len(raw) < 16 or raw[-5:] != MAGIC:
        raise ValueError("invalid section-pointer trailer")
    size = int.from_bytes(raw[-13:-5], "little")
    start = len(raw) - 13 - size
    if start < 0 or size < 3:
        raise ValueError("invalid section-pointer metadata size")
    metadata = raw[start:-13]
    mode = metadata[0]
    if mode not in range(7):
        raise ValueError("invalid section-pointer model")
    flags, position = parent.parent.read(metadata, 1)
    choices, position = parent.parent.read(metadata, position)
    if position != len(metadata):
        raise ValueError("unused section-pointer metadata")
    data = parent.inverse(raw[:start])
    descriptors = fields(data, mode)
    if len(flags) != ((len(descriptors) + 7) // 8 if mode else 0):
        raise ValueError("section-pointer membership mismatch")
    if mode not in (5, 6) and choices:
        raise ValueError("unexpected section choices")
    digits = _digits(choices, mode, descriptors, flags)
    out = bytearray(data)
    event = 0
    for index, descriptor in enumerate(descriptors):
        event = _restore_descriptor(out, descriptor, mode, flags[index // 8] & (1 << (index % 8)), digits, event)
    return bytes(out)
