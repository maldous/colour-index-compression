"""Small generic pair-substitution tournament; experimental, limited to 64 KiB.

Pairs are selected solely by byte/token frequency. Rule and token metadata are
fully materialized using the existing exact integer-stream portfolio. No corpus
or format labels enter the codec.
"""
from collections import Counter
import zlib
from cix.multinomial import vencode, vdecode
from cix.substreams import encode_uints, decode_uints

MAGIC = b'CIXG\x01'
MAX_INPUT = 65536
MAX_RULES = 256


def _pack(data, rules, tokens, token_ppm=False):
    dictionary = encode_uints([symbol for pair in rules for symbol in pair])
    payload = encode_uints(tokens)
    best = (MAGIC + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + b'\x01'
            + vencode(len(rules)) + vencode(len(tokens)) + vencode(len(dictionary))
            + dictionary + payload)
    if token_ppm:
        from cix.ppm import encode_ppm
        raw = b''.join(vencode(t) for t in tokens)
        prefix = (b'CIXG\x02' + best[5:len(best)-len(payload)])
        for order in (3, 5):
            candidate = prefix + vencode(len(raw)) + encode_ppm(raw, max_order=order)
            if len(candidate) < len(best):
                best = candidate
    return best


def encode(data, *, token_ppm=False):
    if len(data) > MAX_INPUT:
        raise ValueError('experimental input limit exceeded')
    best = MAGIC + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + b'\x00' + data
    tokens, rules = list(data), []
    checkpoints = []
    for step in range(MAX_RULES):
        counts = Counter(zip(tokens, tokens[1:]))
        if not counts:
            break
        pair, frequency = min(counts.items(), key=lambda item: (-item[1], item[0]))
        if frequency < 3:
            break
        replacement = 256 + len(rules)
        updated = []
        i = 0
        while i < len(tokens):
            if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) == pair:
                updated.append(replacement)
                i += 2
            else:
                updated.append(tokens[i])
                i += 1
        rules.append(pair)
        tokens = updated
        if len(rules) & (len(rules) - 1) == 0:
            candidate = _pack(data, rules, tokens, token_ppm)
            checkpoints.append(dict(rules=len(rules), tokens=len(tokens), size=len(candidate)))
            if len(candidate) < len(best):
                best = candidate
    if rules and len(rules) & (len(rules) - 1):
        candidate = _pack(data, rules, tokens, token_ppm)
        checkpoints.append(dict(rules=len(rules), tokens=len(tokens), size=len(candidate)))
        if len(candidate) < len(best):
            best = candidate
    return best, checkpoints


def decode(frame):
    if frame[:5] not in (MAGIC, b'CIXG\x02'):
        raise ValueError('invalid experimental grammar frame')
    length, pos = vdecode(frame, 5)
    if length > MAX_INPUT or pos + 5 > len(frame):
        raise ValueError('invalid or truncated header')
    checksum = int.from_bytes(frame[pos:pos + 4], 'big')
    mode = frame[pos + 4]
    pos += 5
    if mode == 0:
        output = frame[pos:]
    elif mode == 1:
        nrules, pos = vdecode(frame, pos)
        ntokens, pos = vdecode(frame, pos)
        size, pos = vdecode(frame, pos)
        if not 1 <= nrules <= MAX_RULES or ntokens > length or pos + size > len(frame):
            raise ValueError('invalid grammar sizes')
        values = decode_uints(frame[pos:pos + size], nrules * 2)
        rules = list(zip(values[::2], values[1::2]))
        for index, pair in enumerate(rules):
            if any(symbol >= 256 + index for symbol in pair):
                raise ValueError('cyclic or forward grammar reference')
        if frame[:5] == MAGIC:
            tokens = decode_uints(frame[pos + size:], ntokens)
        else:
            from cix.ppm import decode_ppm
            raw_size, token_pos = vdecode(frame, pos + size)
            if not ntokens <= raw_size <= 2 * ntokens:
                raise ValueError('invalid token byte length')
            raw = decode_ppm(frame[token_pos:], source_length=raw_size)
            tokens, at = [], 0
            for _ in range(ntokens):
                token, at = vdecode(raw, at)
                tokens.append(token)
            if at != len(raw):
                raise ValueError('trailing token bytes')
        if any(symbol >= 256 + nrules for symbol in tokens):
            raise ValueError('invalid token')
        pending = list(reversed(tokens))
        output = bytearray()
        while pending:
            symbol = pending.pop()
            if symbol < 256:
                output.append(symbol)
                if len(output) > length:
                    raise ValueError('expansion exceeds original length')
            else:
                left, right = rules[symbol - 256]
                pending.extend((right, left))
        output = bytes(output)
    else:
        raise ValueError('unknown grammar mode')
    if len(output) != length or zlib.crc32(output) != checksum:
        raise ValueError('length or checksum mismatch')
    return output
