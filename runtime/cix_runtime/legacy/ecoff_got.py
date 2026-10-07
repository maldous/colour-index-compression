"""Restricted address alphabets from symbols transmitted in the same archive.

All definitions are carried in the unchanged symbol tables. No external library,
filename, source-byte dictionary or saved prediction trace is used by decoding.
"""
from collections import Counter, defaultdict
from math import log2
import struct
from .multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder
from . import ecoff_fields as parent

MAGIC = b'ECGT1'
BLOCK = 1024


def pack(blob):
    return vencode(len(blob)) + blob


def read(blob, pos):
    size, pos = vdecode(blob, pos)
    if pos + size > len(blob):
        raise ValueError('truncated GOT substream')
    return blob[pos:pos + size], pos + size


def _object_symbols(data, offset, size):
    d = data[offset:offset + size]
    sec = parent.base.sections(d)
    required = (b'.dynsym', b'.dynstr', b'.hash')
    if not all(name in sec for name in required):
        return None
    symbol_offset, symbol_size = sec[b'.dynsym']
    text_offset, text_size = sec[b'.dynstr']
    hash_offset, hash_size = sec[b'.hash']
    if hash_size < 8:
        return None
    count = struct.unpack_from('<I', d, hash_offset + 4)[0]
    if count * 24 > symbol_size:
        return None
    symbols = []
    for index in range(count):
        start = struct.unpack_from('<I', d, symbol_offset + index * 24)[0]
        end = d.find(b'\0', text_offset + start, text_offset + text_size) if start < text_size else -1
        if end < 0:
            return None
        value = struct.unpack_from('<Q', d, symbol_offset + index * 24 + 8)[0]
        symbols.append((d[text_offset + start:end], value))
    return d, sec, symbols


def objects(data):
    out = []
    for offset, size in parent.base.objects(data):
        parsed = _object_symbols(data, offset, size)
        if parsed is not None:
            d, sec, symbols = parsed
            out.append((offset, d, sec, symbols))
    return out


def _global_index(parsed):
    index = defaultdict(Counter)
    for _, _, _, symbols in parsed:
        for name, value in symbols:
            if value:
                index[name][value] += 1
    return index


def _dynamic_tags(data, section):
    offset, size = section
    tags = defaultdict(list)
    for position in range(offset, offset + size // 16 * 16, 16):
        tag, _, value = struct.unpack_from('<IIQ', data, position)
        if not tag:
            break
        tags[tag].append(value & 0xffffffff)
    return tags


def _tag_ranges(tags, symbol_count):
    starts = tags[0x7000000a]
    symstarts = tags[0x70000013]
    counts = tags[0x70000011]
    valid = starts and len(starts) == len(symstarts) and counts == [symbol_count]
    if not valid or starts != sorted(set(starts)) or symstarts != sorted(set(symstarts)):
        return None
    return starts, symstarts


def _group_fields(offset, got_offset, got_size, symbols, starts, symstarts, index, global_symbols):
    local = []; previous = -1
    for group, (got_start, symbol_start) in enumerate(zip(starts, symstarts)):
        end = symstarts[group + 1] if group + 1 < len(starts) else len(symbols)
        if symbol_start > end or end > len(symbols):
            return None
        for symbol_index in range(symbol_start, end):
            got_index = got_start + symbol_index - symbol_start
            if got_index <= previous or got_index * 8 + 8 > got_size:
                return None
            previous = got_index; name, value = symbols[symbol_index]
            ranked = sorted(index[name], key=lambda item, name=name: (-index[name][item], item)) if global_symbols else []
            options = [value] + [item for item in ranked if item != value]
            local.append((offset + got_offset + got_index * 8, options, int(value == 0)))
    return local


def _candidate_fields(parsed, index, global_symbols):
    result = []
    for offset, data, sections, symbols in parsed:
        if b'.dynamic' not in sections or b'.got' not in sections:
            continue
        ranges = _tag_ranges(_dynamic_tags(data, sections[b'.dynamic']), len(symbols))
        if ranges is None:
            continue
        got_offset, got_size = sections[b'.got']
        local = _group_fields(offset, got_offset, got_size, symbols, *ranges, index, global_symbols)
        if local is not None:
            result.extend(local)
    return result


def candidates(data, global_symbols=True):
    parsed = objects(data)
    index = _global_index(parsed) if global_symbols else defaultdict(Counter)
    result = _candidate_fields(parsed, index, global_symbols)
    result.sort(key=lambda item: item[0])
    if any(left[0] + 8 > right[0] for left, right in zip(result, result[1:])):
        raise ValueError('overlapping GOT fields')
    return result


def encode_choices(digits, alphabets, contexts, mode):
    uncertainty = sum(log2(k) for k in alphabets)
    if mode == 0:
        return b''.join(vencode(d) for d in digits), uncertainty, None
    if mode == 1:
        out = bytearray()
        for start in range(0, len(digits), BLOCK):
            rank = 0; product = 1
            for digit, k in zip(digits[start:start + BLOCK], alphabets[start:start + BLOCK]):
                rank += digit * product; product *= k
            out.extend(rank.to_bytes(((product - 1).bit_length() + 7) // 8, 'little'))
        return bytes(out), uncertainty, uncertainty
    encoder = _ArithmeticEncoder(); frequencies = {}; bits = 0.0
    for digit, k, context in zip(digits, alphabets, contexts):
        counts = frequencies.setdefault((k, context), [1] * k)
        low = sum(counts[:digit]); total = sum(counts)
        encoder.encode(low, low + counts[digit], total); bits += log2(total / counts[digit])
        if mode == 3:
            counts[digit] += 1
            if sum(counts) > 4096:
                counts[:] = [(x + 1) // 2 for x in counts]
    payload, length = encoder.finish()
    return vencode(length) + payload, uncertainty, bits


def _decode_varints(payload, alphabets):
    out = []; pos = 0
    for alphabet in alphabets:
        digit, pos = vdecode(payload, pos)
        if digit >= alphabet:
            raise ValueError('GOT choice outside alphabet')
        out.append(digit)
    return out, pos


def _decode_ranks(payload, alphabets):
    out = []; pos = 0
    for start in range(0, len(alphabets), BLOCK):
        block = alphabets[start:start + BLOCK]; product = 1
        for alphabet in block:
            product *= alphabet
        size = ((product - 1).bit_length() + 7) // 8
        if pos + size > len(payload):
            raise ValueError('truncated GOT rank')
        rank = int.from_bytes(payload[pos:pos + size], 'little'); pos += size
        if rank >= product:
            raise ValueError('GOT rank outside state space')
        for alphabet in block:
            out.append(rank % alphabet); rank //= alphabet
    return out, pos


def _decode_arithmetic(payload, alphabets, contexts, adaptive):
    bits, pos = vdecode(payload, 0)
    if pos + (bits + 7) // 8 != len(payload):
        raise ValueError('invalid GOT arithmetic framing')
    decoder = _ArithmeticDecoder(payload[pos:], bits); frequencies = {}; out = []
    for alphabet, context in zip(alphabets, contexts):
        counts = frequencies.setdefault((alphabet, context), [1] * alphabet); total = sum(counts)
        target = decoder.target(total); low = 0
        for digit, count in enumerate(counts):
            if target < low + count:
                decoder.update(low, low + count, total); break
            low += count
        else:
            raise ValueError('invalid GOT arithmetic symbol')
        out.append(digit)
        if adaptive:
            counts[digit] += 1
            if sum(counts) > 4096:
                counts[:] = [(count + 1) // 2 for count in counts]
    return out, len(payload)


def decode_choices(payload, alphabets, contexts, mode):
    if mode == 0:
        out, pos = _decode_varints(payload, alphabets)
    elif mode == 1:
        out, pos = _decode_ranks(payload, alphabets)
    else:
        out, pos = _decode_arithmetic(payload, alphabets, contexts, mode == 3)
    if pos != len(payload):
        raise ValueError('unused GOT choice bytes')
    return out


def transform(data, mode=3, global_symbols=True):
    if mode not in range(4):
        raise ValueError('invalid GOT representation')
    fields = candidates(data, global_symbols); out = bytearray(data); digits = []; alphabets = []; contexts = []; escapes = bytearray()
    for where, options, context in fields:
        value = struct.unpack_from('<Q', data, where)[0]
        digit = options.index(value) if value in options else len(options)
        if digit == len(options):
            escapes.extend(data[where:where + 8])
        out[where:where + 8] = bytes(8); digits.append(digit); alphabets.append(len(options) + 1); contexts.append(context)
    choices, uncertainty, model_bits = encode_choices(digits, alphabets, contexts, mode)
    skeleton, _ = parent.transform(bytes(out), 1)
    metadata = bytes([mode, int(global_symbols)]) + pack(choices) + escapes
    raw = skeleton + metadata + len(metadata).to_bytes(8, 'little') + MAGIC
    return raw, {"mode": mode, "global_symbols": global_symbols, "original_bytes": len(data), "transformed_bytes": len(raw),
                     "mapped_addresses": len(fields), "in_candidates": len(fields) - len(escapes) // 8, "exception_bytes": len(escapes),
                     "candidate_combinatorial_bits": uncertainty, "choice_model_bits": model_bits, "choice_bytes": len(choices)}


def _restore_field(out, where, options, digit, raw, position):
    if any(out[where:where + 8]):
        raise ValueError('GOT skeleton field is not zero')
    if digit == len(options):
        if position + 8 > len(raw):
            raise ValueError('truncated GOT exception')
        out[where:where + 8] = raw[position:position + 8]
        return position + 8
    struct.pack_into('<Q', out, where, options[digit])
    return position


def _inverse_metadata(raw):
    if len(raw) < 16 or raw[-5:] != MAGIC:
        raise ValueError('invalid GOT constraint frame')
    size = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - 13 - size
    if start < 0 or size < 3:
        raise ValueError('invalid GOT metadata length')
    skeleton, metadata = raw[:start], raw[start:-13]
    mode, global_symbols = metadata[:2]
    if mode not in range(4) or global_symbols not in (0, 1):
        raise ValueError('invalid GOT representation')
    return skeleton, metadata, mode, global_symbols


def inverse(raw):
    skeleton, raw, mode, global_symbols = _inverse_metadata(raw)
    choices, position = read(raw, 2)
    data = parent.inverse(skeleton); fields = candidates(data, bool(global_symbols))
    alphabets = [len(options) + 1 for _, options, _ in fields]
    contexts = [context for _, _, context in fields]
    digits = decode_choices(choices, alphabets, contexts, mode)
    out = bytearray(data)
    for (where, options, _), digit in zip(fields, digits):
        position = _restore_field(out, where, options, digit, raw, position)
    if position != len(raw):
        raise ValueError('unused GOT exceptions')
    return bytes(out)
