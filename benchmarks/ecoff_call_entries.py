"""Constrain Alpha calls to transmitted function addresses and +16-byte entries.

The instructions keep their opcodes. In-place indices are offset to account for
PAQ's existing absolute-call transform over contiguous text/init/fini sections.
Unlisted targets always have an explicit literal escape or unchanged field.
"""
import struct
from math import log2
from cix.multinomial import vencode, vdecode, Fenwick, _ArithmeticEncoder, _ArithmeticDecoder
from benchmarks import ecoff_got as parent

MAGIC = b'ECBR2'
MASK = (1 << 21) - 1
CALL = (0x34 << 5) + 26


def groups(data):
    out = []
    for off, d, sec, symbols in parent.objects(data):
        count = struct.unpack_from('<H', d, 2)[0]
        if count > 24 or b'.pdata' not in sec:
            continue
        sections = {}
        for i in range(count):
            name, _, virtual, size, pointer, _, _, _, _, _ = struct.unpack_from('<8sQQQQQQHHI', d, 104 + i * 64)
            sections[name.rstrip(b'\0')] = (virtual, size, pointer)
        if not all(k in sections for k in (b'.text', b'.init', b'.fini')):
            continue
        virtual, length, start = sections[b'.text']; valid = bool(start)
        for name in (b'.init', b'.fini'):
            v, n, p = sections[name]
            valid &= p == start + length and v == virtual + length
            length += n
        if not valid or length % 4:
            continue
        pv, pn, pp = sections[b'.pdata']
        functions = {value for _, value in symbols}
        for p in range(pp, pp + pn // 8 * 8, 8):
            functions.add((pv + (struct.unpack_from('<i', d, p)[0] & ~3)) & ((1 << 64) - 1))
        functions = sorted({v + entry for v in functions for entry in (0, 16)
                            if virtual <= v + entry < virtual + length and (v + entry - virtual) % 4 == 0})
        if not functions or len(functions) > 65535:
            continue
        calls = []
        for word, (instruction,) in enumerate(struct.iter_unpack('<I', d[start:start + length])):
            if instruction >> 21 == CALL:
                calls.append((off + start + word * 4, word, virtual + word * 4 + 4))
        if calls:
            out.append((functions, calls))
    return out


def arithmetic(digits, alphabets, contexts, adaptive, payload=None):
    if payload is None:
        coder = _ArithmeticEncoder()
    else:
        bits, pos = vdecode(payload, 0)
        if pos + (bits + 7) // 8 != len(payload):
            raise ValueError('invalid call arithmetic framing')
        coder = _ArithmeticDecoder(payload[pos:], bits)
    models = {}; decoded = []; uncertainty = 0.0
    for i, (k, context) in enumerate(zip(alphabets, contexts)):
        if adaptive:
            if context not in models:
                counts = [1] * k; models[context] = [counts, Fenwick(counts), k]
            counts, tree, total = models[context]
            digit = digits[i] if payload is None else tree.select(coder.target(total))
            low, width = tree.prefix(digit), counts[digit]
        else:
            total = k; digit = digits[i] if payload is None else coder.target(k); low, width = digit, 1
        if payload is None:
            coder.encode(low, low + width, total)
        else:
            coder.update(low, low + width, total); decoded.append(digit)
        uncertainty += log2(total / width)
        if adaptive:
            counts[digit] += 1; tree.add(digit, 1); total += 1
            if total > max(65536, k * 2):
                counts = [(x + 1) // 2 for x in counts]; tree = Fenwick(counts); total = sum(counts)
            models[context] = [counts, tree, total]
    if payload is not None:
        return decoded, uncertainty
    packed, bits = coder.finish()
    return vencode(bits) + packed, uncertainty


def transform(data, mode=1):
    if mode not in range(6):
        raise ValueError('invalid call representation')
    objects = groups(data); count = sum(len(calls) for _, calls in objects)
    flags = bytearray((count + 7) // 8) if mode == 1 else bytearray()
    out = bytearray(data); digits = []; alphabets = []; contexts = []; exceptions = bytearray(); hit = 0; event = 0
    for context, (functions, calls) in enumerate(objects):
        index = {v: i for i, v in enumerate(functions)}
        for where, word, pc in calls:
            instruction = struct.unpack_from('<I', data, where)[0]; displacement = instruction & MASK
            signed = displacement - (1 << 21) if displacement & (1 << 20) else displacement
            target = (pc + signed * 4) & ((1 << 64) - 1); digit = index.get(target, len(functions)); matches = digit < len(functions)
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
    model_bits = None
    if mode in (2, 3):
        choices, uniform_bits, model_bits = parent.encode_choices(digits, alphabets, contexts, mode - 2)
    elif mode >= 4:
        choices, model_bits = arithmetic(digits, alphabets, contexts, mode == 5); uniform_bits = sum(log2(k) for k in alphabets)
    else:
        choices = b''; uniform_bits = 0.0
    skeleton, _ = parent.transform(bytes(out), 3)
    metadata = bytes([mode]) + parent.pack(bytes(flags)) + parent.pack(choices) + bytes(exceptions)
    raw = skeleton + metadata + len(metadata).to_bytes(8, 'little') + MAGIC
    return raw, dict(mode=mode, original_bytes=len(data), transformed_bytes=len(raw), objects=len(objects), calls=count,
                     targets_in_candidates=hit, membership_bytes=len(flags), choice_bytes=len(choices), exception_bytes=len(exceptions),
                     candidate_combinatorial_bits=uniform_bits, choice_model_bits=model_bits)


def inverse(raw):
    if len(raw) < 16 or raw[-5:] != MAGIC:
        raise ValueError('invalid call trailer')
    size = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - size - 13
    if start < 0 or size < 3:
        raise ValueError('invalid call metadata size')
    data = parent.inverse(raw[:start]); meta = raw[start:-13]; mode = meta[0]
    if mode not in range(6):
        raise ValueError('invalid call mode')
    flags, pos = parent.read(meta, 1); choices, pos = parent.read(meta, pos); objects = groups(data)
    count = sum(len(calls) for _, calls in objects)
    if len(flags) != ((count + 7) // 8 if mode == 1 else 0):
        raise ValueError('call membership length mismatch')
    if mode < 2 and choices:
        raise ValueError('unexpected call choices')
    alphabets = []; contexts = []
    for context, (functions, calls) in enumerate(objects):
        alphabets.extend([len(functions) + 1] * len(calls)); contexts.extend([context] * len(calls))
    if mode in (2, 3):
        digits = parent.decode_choices(choices, alphabets, contexts, mode - 2)
    elif mode >= 4:
        digits, _ = arithmetic(None, alphabets, contexts, mode == 5, choices)
    else:
        digits = []
    out = bytearray(data); event = 0
    for functions, calls in objects:
        for where, word, pc in calls:
            instruction = struct.unpack_from('<I', out, where)[0]
            restore = mode >= 2 or mode == 1 and bool(flags[event // 8] & (1 << (event % 8)))
            if restore:
                digit = ((instruction & MASK) + word) & MASK if mode == 1 else digits[event]
                if mode >= 2 and ((instruction & MASK) + word) & MASK:
                    raise ValueError('call skeleton displacement is not normalized zero')
                if mode >= 2 and digit == len(functions):
                    displacement, pos = vdecode(meta, pos)
                    if displacement > MASK:
                        raise ValueError('call exception outside field')
                else:
                    if digit >= len(functions):
                        raise ValueError('call index outside function alphabet')
                    delta = functions[digit] - pc
                    if delta % 4 or not -(1 << 20) <= delta // 4 < (1 << 20):
                        raise ValueError('call target outside branch range')
                    displacement = (delta // 4) & MASK
                struct.pack_into('<I', out, where, (CALL << 21) | displacement)
            event += 1
    if pos != len(meta):
        raise ValueError('unused call exceptions')
    return bytes(out)
