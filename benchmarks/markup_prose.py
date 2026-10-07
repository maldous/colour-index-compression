"""Keep prose order while encoding markup identities in a separate stream.

Each recognized tag becomes a tab. Original tabs are explicit identity-zero
events. The transmitted dictionary defines every other identity; unknown tags
and arbitrary bytes remain literal. This preserves bytes, not a parsed DOM.
"""
from collections import Counter
from cix.multinomial import vencode, vdecode
from benchmarks.markup_columns import TOKEN
from benchmarks.ecoff_got import pack, read

MAGIC = b'MPRO1'


def transform(data, mode=1):
    if mode not in (0, 1, 2):
        raise ValueError('invalid prose/markup mode')
    counts = Counter(m.group() for m in TOKEN.finditer(data) if len(m.group()) <= 256) if mode else Counter()
    dictionary = sorted(counts, key=lambda token: (-counts[token], token))[:4096]
    ids = {token: i + 1 for i, token in enumerate(dictionary)}
    skeleton = bytearray(); events = []; at = 0
    def literal(value):
        skeleton.extend(value); events.extend([0] * value.count(b'\t'))
    if mode:
        for match in TOKEN.finditer(data):
            token = match.group()
            if token not in ids:
                continue
            literal(data[at:match.start()]); skeleton.append(9); events.append(ids[token]); at = match.end()
        literal(data[at:])
    else:
        skeleton.extend(data)
    dictionary_blob = vencode(len(dictionary)) + b''.join(pack(token) for token in dictionary)
    codes = b''.join(vencode(i) for i in events) if mode == 1 else b' '.join(str(i).encode('ascii') for i in events) if mode == 2 else b''
    metadata = bytes([mode]) + vencode(len(data)) + pack(dictionary_blob) + pack(codes)
    raw = bytes(skeleton) + metadata + len(metadata).to_bytes(8, 'little') + MAGIC
    return raw, dict(mode=mode, original_bytes=len(data), transformed_bytes=len(raw),
                     skeleton_bytes=len(skeleton), dictionary_entries=len(dictionary),
                     dictionary_bytes=len(dictionary_blob), events=len(events), identity_bytes=len(codes),
                     removed_tag_bytes=sum((len(token)-1)*counts[token] for token in dictionary))


def inverse(raw):
    if len(raw) < 18 or raw[-5:] != MAGIC:
        raise ValueError('invalid prose trailer')
    size = int.from_bytes(raw[-13:-5], 'little'); start = len(raw)-13-size
    if start < 0 or size < 5:
        raise ValueError('invalid prose metadata length')
    metadata = raw[start:-13]; mode = metadata[0]
    if mode not in (0, 1, 2):
        raise ValueError('invalid prose mode')
    n, pos = vdecode(metadata, 1); table, pos = read(metadata, pos); codes, pos = read(metadata, pos)
    if pos != len(metadata):
        raise ValueError('unused prose metadata')
    count, pos = vdecode(table, 0); dictionary = [b'\t']
    if count > 4096:
        raise ValueError('oversized tag dictionary')
    for _ in range(count):
        token, pos = read(table, pos)
        if not token or len(token) > 256:
            raise ValueError('invalid tag dictionary member')
        dictionary.append(token)
    if pos != len(table):
        raise ValueError('unused tag dictionary bytes')
    if not mode:
        if count or codes:
            raise ValueError('control has unexpected identities')
        output = raw[:start]
    else:
        out = bytearray(); at = 0; pos = 0
        # Parse text IDs incrementally to avoid millions of temporary strings.
        for where, byte in enumerate(raw[:start]):
            if byte != 9:
                continue
            out.extend(raw[at:where]); at = where+1
            if mode == 1:
                digit, pos = vdecode(codes, pos)
            else:
                end = codes.find(b' ', pos)
                if end < 0:
                    end = len(codes)
                text = codes[pos:end]
                if not text or len(text) > 4 or not text.isdigit():
                    raise ValueError('invalid printable tag identity')
                digit = int(text); pos = end + (end < len(codes))
            if digit >= len(dictionary):
                raise ValueError('tag identity outside dictionary')
            out.extend(dictionary[digit])
        out.extend(raw[at:start]); output = bytes(out)
        if pos != len(codes):
            raise ValueError('unused tag identities')
    if len(output) != n:
        raise ValueError('prose restoration length mismatch')
    return output
