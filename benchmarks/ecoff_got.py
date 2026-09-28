"""Restricted address alphabets from symbols transmitted in the same archive.

All definitions are carried in the unchanged symbol tables. No external library,
filename, source-byte dictionary or saved prediction trace is used by decoding.
"""
from collections import Counter, defaultdict
from math import log2
import struct
from cix.multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder
from benchmarks import ecoff_fields as parent

MAGIC = b'ECGT1'
BLOCK = 1024


def pack(blob):
    return vencode(len(blob)) + blob


def read(blob, pos):
    size, pos = vdecode(blob, pos)
    if pos + size > len(blob):
        raise ValueError('truncated GOT substream')
    return blob[pos:pos + size], pos + size


def objects(data):
    out = []
    for off, size in parent.base.objects(data):
        d = data[off:off + size]; sec = parent.base.sections(d)
        if not all(k in sec for k in (b'.dynsym', b'.dynstr', b'.hash')):
            continue
        so, ss = sec[b'.dynsym']; to, ts = sec[b'.dynstr']; ho, hs = sec[b'.hash']
        if hs < 8:
            continue
        n = struct.unpack_from('<I', d, ho + 4)[0]
        if n * 24 > ss:
            continue
        symbols = []
        for i in range(n):
            start = struct.unpack_from('<I', d, so + i * 24)[0]
            end = d.find(b'\0', to + start, to + ts) if start < ts else -1
            if end < 0:
                break
            value = struct.unpack_from('<Q', d, so + i * 24 + 8)[0]
            symbols.append((d[to + start:end], value))
        if len(symbols) == n:
            out.append((off, d, sec, symbols))
    return out


def candidates(data, global_symbols=True):
    parsed = objects(data); index = defaultdict(Counter)
    if global_symbols:
        for _, _, _, symbols in parsed:
            for name, value in symbols:
                if value:
                    index[name][value] += 1
    result = []
    for off, d, sec, symbols in parsed:
        if not all(k in sec for k in (b'.dynamic', b'.got')):
            continue
        do, ds = sec[b'.dynamic']; go, gs = sec[b'.got']; tags = defaultdict(list)
        for p in range(do, do + ds // 16 * 16, 16):
            tag, _, value = struct.unpack_from('<IIQ', d, p)
            if not tag:
                break
            # These tags use the 32-bit d_val union member. Its high word is
            # padding and can contain arbitrary bytes in otherwise valid files.
            tags[tag].append(value & 0xffffffff)
        starts, symstarts, counts = tags[0x7000000a], tags[0x70000013], tags[0x70000011]
        if (not starts or len(starts) != len(symstarts) or counts != [len(symbols)]
                or starts != sorted(set(starts)) or symstarts != sorted(set(symstarts))):
            continue
        local = []; previous = -1; valid = True
        for j, (g0, s0) in enumerate(zip(starts, symstarts)):
            end = symstarts[j + 1] if j + 1 < len(starts) else len(symbols)
            if s0 > end or end > len(symbols):
                valid = False; break
            for si in range(s0, end):
                gi = g0 + si - s0
                if gi <= previous or gi * 8 + 8 > gs:
                    valid = False; break
                previous = gi; name, value = symbols[si]
                rest = sorted(index[name], key=lambda x: (-index[name][x], x)) if global_symbols else []
                options = [value] + [x for x in rest if x != value]
                local.append((off + go + gi * 8, options, int(value == 0)))
            if not valid:
                break
        if valid:
            result.extend(local)
    result.sort(key=lambda x: x[0])
    if any(a[0] + 8 > b[0] for a, b in zip(result, result[1:])):
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


def decode_choices(payload, alphabets, contexts, mode):
    out = []; pos = 0
    if mode == 0:
        for k in alphabets:
            digit, pos = vdecode(payload, pos)
            if digit >= k:
                raise ValueError('GOT choice outside alphabet')
            out.append(digit)
    elif mode == 1:
        for start in range(0, len(alphabets), BLOCK):
            block = alphabets[start:start + BLOCK]; product = 1
            for k in block:
                product *= k
            size = ((product - 1).bit_length() + 7) // 8
            if pos + size > len(payload):
                raise ValueError('truncated GOT rank')
            rank = int.from_bytes(payload[pos:pos + size], 'little'); pos += size
            if rank >= product:
                raise ValueError('GOT rank outside state space')
            for k in block:
                out.append(rank % k); rank //= k
    else:
        bits, pos = vdecode(payload, 0)
        if pos + (bits + 7) // 8 != len(payload):
            raise ValueError('invalid GOT arithmetic framing')
        decoder = _ArithmeticDecoder(payload[pos:], bits); frequencies = {}
        for k, context in zip(alphabets, contexts):
            counts = frequencies.setdefault((k, context), [1] * k); total = sum(counts)
            target = decoder.target(total); low = 0
            for digit, count in enumerate(counts):
                if target < low + count:
                    decoder.update(low, low + count, total); break
                low += count
            else:
                raise ValueError('invalid GOT arithmetic symbol')
            out.append(digit)
            if mode == 3:
                counts[digit] += 1
                if sum(counts) > 4096:
                    counts[:] = [(x + 1) // 2 for x in counts]
        pos = len(payload)
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
    return raw, dict(mode=mode, global_symbols=global_symbols, original_bytes=len(data), transformed_bytes=len(raw),
                     mapped_addresses=len(fields), in_candidates=len(fields) - len(escapes) // 8, exception_bytes=len(escapes),
                     candidate_combinatorial_bits=uncertainty, choice_model_bits=model_bits, choice_bytes=len(choices))


def inverse(raw):
    if len(raw) < 16 or raw[-5:] != MAGIC:
        raise ValueError('invalid GOT constraint frame')
    size = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - 13 - size
    if start < 0 or size < 3:
        raise ValueError('invalid GOT metadata length')
    skeleton, raw = raw[:start], raw[start:-13]
    mode, global_symbols = raw[:2]
    if mode not in range(4) or global_symbols not in (0, 1):
        raise ValueError('invalid GOT representation')
    choices, pos = read(raw, 2)
    data = parent.inverse(skeleton); fields = candidates(data, bool(global_symbols))
    digits = decode_choices(choices, [len(v) + 1 for _, v, _ in fields], [c for _, _, c in fields], mode)
    out = bytearray(data)
    for (where, options, _), digit in zip(fields, digits):
        if any(out[where:where + 8]):
            raise ValueError('GOT skeleton field is not zero')
        if digit == len(options):
            if pos + 8 > len(raw):
                raise ValueError('truncated GOT exception')
            out[where:where + 8] = raw[pos:pos + 8]; pos += 8
        else:
            struct.pack_into('<Q', out, where, options[digit])
    if pos != len(raw):
        raise ValueError('unused GOT exceptions')
    return bytes(out)
