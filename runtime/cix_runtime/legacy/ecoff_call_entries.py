"""Constrain Alpha calls to transmitted function addresses and +16-byte entries.

The instructions keep their opcodes. In-place indices are offset to account for
PAQ's existing absolute-call transform over contiguous text/init/fini sections.
Unlisted targets always have an explicit literal escape or unchanged field.
"""
import struct
from math import log2
from .multinomial import vencode, vdecode, Fenwick, _ArithmeticEncoder, _ArithmeticDecoder
from . import ecoff_got as parent

MAGIC = b'ECBR2'
MASK = (1 << 21) - 1
CALL = (0x34 << 5) + 26


def _sections(data, count):
    return {
        values[0].rstrip(b'\0'): values[2:5]
        for index in range(count)
        for values in (struct.unpack_from('<8sQQQQQQHHI', data, 104 + index * 64),)
    }


def _text_extent(sections):
    if not all(name in sections for name in (b'.text', b'.init', b'.fini')):
        return None
    virtual, length, start = sections[b'.text']
    for name in (b'.init', b'.fini'):
        current, size, pointer = sections[name]
        if pointer != start + length or current != virtual + length:
            return None
        length += size
    return (virtual, length, start) if start and length % 4 == 0 else None


def _function_targets(data, symbols, pdata, virtual, length):
    pv, pn, pp = pdata
    targets = {value for _, value in symbols}
    targets.update((pv + (struct.unpack_from('<i', data, pos)[0] & ~3)) & ((1 << 64) - 1)
                   for pos in range(pp, pp + pn // 8 * 8, 8))
    return sorted({value + entry for value in targets for entry in (0, 16)
                   if virtual <= value + entry < virtual + length and (value + entry - virtual) % 4 == 0})


def _calls(data, offset, start, length, virtual):
    return [(offset + start + word * 4, word, virtual + word * 4 + 4)
            for word, (instruction,) in enumerate(struct.iter_unpack('<I', data[start:start + length]))
            if instruction >> 21 == CALL]


def groups(data):
    result = []
    for offset, member, sections_hint, symbols in parent.objects(data):
        count = struct.unpack_from('<H', member, 2)[0]
        if count > 24 or b'.pdata' not in sections_hint:
            continue
        sections = _sections(member, count)
        extent = _text_extent(sections)
        if extent is None:
            continue
        virtual, length, start = extent
        functions = _function_targets(member, symbols, sections[b'.pdata'], virtual, length)
        calls = _calls(member, offset, start, length, virtual)
        if calls and 0 < len(functions) <= 65535:
            result.append((functions, calls))
    return result


def _arithmetic_coder(payload):
    if payload is None:
        return _ArithmeticEncoder()
    bits, pos = vdecode(payload, 0)
    if pos + (bits + 7) // 8 != len(payload):
        raise ValueError('invalid call arithmetic framing')
    return _ArithmeticDecoder(payload[pos:], bits)


def _model(models, context, alphabet):
    if context not in models:
        counts = [1] * alphabet
        models[context] = [counts, Fenwick(counts), alphabet]
    return models[context]


def _update_model(models, context, alphabet, digit):
    counts, tree, total = _model(models, context, alphabet)
    counts[digit] += 1
    tree.add(digit, 1)
    total += 1
    if total > max(65536, alphabet * 2):
        counts = [(value + 1) // 2 for value in counts]
        tree, total = Fenwick(counts), sum(counts)
    models[context] = [counts, tree, total]


def _interval(coder, digit, alphabet, context, models, adaptive, decoding):
    if not adaptive:
        selected = coder.target(alphabet) if decoding else digit
        return selected, selected, 1, alphabet
    counts, tree, total = _model(models, context, alphabet)
    selected = tree.select(coder.target(total)) if decoding else digit
    return selected, tree.prefix(selected), counts[selected], total


def arithmetic(digits, alphabets, contexts, adaptive, payload=None):
    coder, models, decoded, uncertainty = _arithmetic_coder(payload), {}, [], 0.0
    decoding = payload is not None
    for index, (alphabet, context) in enumerate(zip(alphabets, contexts)):
        digit, low, width, total = _interval(coder, None if decoding else digits[index], alphabet, context, models, adaptive, decoding)
        if decoding:
            coder.update(low, low + width, total)
            decoded.append(digit)
        else:
            coder.encode(low, low + width, total)
        uncertainty += log2(total / width)
        if adaptive:
            _update_model(models, context, alphabet, digit)
    if decoding:
        return decoded, uncertainty
    packed, bits = coder.finish()
    return vencode(bits) + packed, uncertainty


def _rewrite_calls(data, objects, mode, flags):
    out, digits, alphabets, contexts, exceptions = bytearray(data), [], [], [], bytearray()
    hit = event = 0
    for context, (functions, calls) in enumerate(objects):
        index = {value: position for position, value in enumerate(functions)}
        for where, word, pc in calls:
            instruction = struct.unpack_from('<I', data, where)[0]
            displacement = instruction & MASK
            signed = displacement - (1 << 21) if displacement & (1 << 20) else displacement
            digit = index.get((pc + signed * 4) & ((1 << 64) - 1), len(functions))
            matches = digit < len(functions)
            hit += matches
            if mode == 1 and matches:
                flags[event // 8] |= 1 << (event % 8)
                struct.pack_into('<I', out, where, (CALL << 21) | ((digit - word) & MASK))
            elif mode >= 2:
                struct.pack_into('<I', out, where, (CALL << 21) | ((-word) & MASK))
                digits.append(digit); alphabets.append(len(functions) + 1); contexts.append(context)
                if not matches:
                    exceptions.extend(vencode(displacement))
            event += 1
    return out, digits, alphabets, contexts, exceptions, hit


def _encode_call_choices(mode, digits, alphabets, contexts):
    if mode in (2, 3):
        return parent.encode_choices(digits, alphabets, contexts, mode - 2)
    if mode >= 4:
        choices, bits = arithmetic(digits, alphabets, contexts, mode == 5)
        return choices, sum(log2(alphabet) for alphabet in alphabets), bits
    return b'', 0.0, None


def transform(data, mode=1):
    if mode not in range(6):
        raise ValueError('invalid call representation')
    objects = groups(data); count = sum(len(calls) for _, calls in objects)
    flags = bytearray((count + 7) // 8) if mode == 1 else bytearray()
    out, digits, alphabets, contexts, exceptions, hit = _rewrite_calls(data, objects, mode, flags)
    choices, uniform_bits, model_bits = _encode_call_choices(mode, digits, alphabets, contexts)
    skeleton, _ = parent.transform(bytes(out), 3)
    metadata = bytes((mode,)) + parent.pack(bytes(flags)) + parent.pack(choices) + bytes(exceptions)
    raw = skeleton + metadata + len(metadata).to_bytes(8, 'little') + MAGIC
    return raw, {"mode": mode, "original_bytes": len(data), "transformed_bytes": len(raw), "objects": len(objects), "calls": count,
                     "targets_in_candidates": hit, "membership_bytes": len(flags), "choice_bytes": len(choices), "exception_bytes": len(exceptions),
                     "candidate_combinatorial_bits": uniform_bits, "choice_model_bits": model_bits}


def _call_alphabets(objects):
    alphabets = []; contexts = []
    for context, (functions, calls) in enumerate(objects):
        alphabets.extend([len(functions) + 1] * len(calls))
        contexts.extend([context] * len(calls))
    return alphabets, contexts


def _call_digits(mode, choices, alphabets, contexts):
    if mode in (2, 3):
        return parent.decode_choices(choices, alphabets, contexts, mode - 2)
    if mode >= 4:
        return arithmetic(None, alphabets, contexts, mode == 5, choices)[0]
    return []


def _target_displacement(functions, digit, pc):
    if digit >= len(functions):
        raise ValueError('call index outside function alphabet')
    delta = functions[digit] - pc
    if delta % 4 or not -(1 << 20) <= delta // 4 < (1 << 20):
        raise ValueError('call target outside branch range')
    return (delta // 4) & MASK


def _restore_displacement(instruction, word, pc, functions, mode, digits, event, meta, position):
    digit = ((instruction & MASK) + word) & MASK if mode == 1 else digits[event]
    if mode >= 2 and ((instruction & MASK) + word) & MASK:
        raise ValueError('call skeleton displacement is not normalized zero')
    if mode >= 2 and digit == len(functions):
        displacement, position = vdecode(meta, position)
        if displacement > MASK:
            raise ValueError('call exception outside field')
    else:
        displacement = _target_displacement(functions, digit, pc)
    return displacement, position


def _restore_call(out, where, word, pc, functions, mode, flags, event, digits, meta, position):
    instruction = struct.unpack_from('<I', out, where)[0]
    if not (mode >= 2 or mode == 1 and bool(flags[event // 8] & (1 << (event % 8)))):
        return position
    displacement, position = _restore_displacement(
        instruction, word, pc, functions, mode, digits, event, meta, position,
    )
    struct.pack_into('<I', out, where, (CALL << 21) | displacement)
    return position


def _inverse_metadata(raw):
    if len(raw) < 16 or raw[-5:] != MAGIC:
        raise ValueError('invalid call trailer')
    size = int.from_bytes(raw[-13:-5], 'little')
    start = len(raw) - size - 13
    if start < 0 or size < 3:
        raise ValueError('invalid call metadata size')
    data, meta = parent.inverse(raw[:start]), raw[start:-13]
    if meta[0] not in range(6):
        raise ValueError('invalid call mode')
    flags, position = parent.read(meta, 1)
    choices, position = parent.read(meta, position)
    return data, meta, meta[0], flags, choices, position


def _restore_calls(data, objects, mode, flags, digits, meta, position):
    out, event = bytearray(data), 0
    for functions, calls in objects:
        for where, word, pc in calls:
            position = _restore_call(out, where, word, pc, functions, mode, flags, event, digits, meta, position)
            event += 1
    return out, position


def inverse(raw):
    data, meta, mode, flags, choices, position = _inverse_metadata(raw)
    objects = groups(data)
    count = sum(len(calls) for _, calls in objects)
    if len(flags) != ((count + 7) // 8 if mode == 1 else 0):
        raise ValueError('call membership length mismatch')
    if mode < 2 and choices:
        raise ValueError('unexpected call choices')
    alphabets, contexts = _call_alphabets(objects); digits = _call_digits(mode, choices, alphabets, contexts)
    out, position = _restore_calls(data, objects, mode, flags, digits, meta, position)
    if position != len(meta):
        raise ValueError('unused call exceptions')
    return bytes(out)
