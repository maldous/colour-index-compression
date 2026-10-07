"""Reversible CSV-record adapter with literal syntax preservation.

This deliberately does not pretend CSV is MyISAM.  It preserves every raw
field token (including quotes), delimiter, record terminator and header byte.
Only the reusable mechanism is borrowed from the OSDB winner: a transmitted
palette, transmitted counts, then remaining-count arithmetic for field-token
orders within a repeated raw-record template.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from benchmarks.mysql_record_constraints import order_decode, order_encode
from cix.multinomial import vdecode, vencode

MAGIC = b"DBCSV1"
LITERAL, DICTIONARY_REMAINING = 0, 1
VARIANTS = {"literal": LITERAL, "dictionary_remaining": DICTIONARY_REMAINING}


def _pack(value: bytes) -> bytes:
    return vencode(len(value)) + value


def _read(blob: bytes, position: int) -> tuple[bytes, int]:
    size, position = vdecode(blob, position)
    if position + size > len(blob): raise ValueError("truncated CSV frame")
    return blob[position:position + size], position + size


def _record(raw: bytes) -> tuple[tuple[bytes, ...], tuple[bytes, ...]]:
    """Split one physical CSV record into literal pieces and raw field tokens.

    RFC4180 embedded newlines are intentionally unsupported here: callers must
    retain the whole input literal rather than risk changing source syntax.
    """
    if raw.endswith(b"\r\n"): body, ending = raw[:-2], b"\r\n"
    elif raw.endswith(b"\n"): body, ending = raw[:-1], b"\n"
    else: body, ending = raw, b""
    fields, pieces, start, quoted, position = [], [], 0, False, 0
    while position < len(body):
        value = body[position]
        if value == 34:
            if quoted and position + 1 < len(body) and body[position + 1] == 34:
                position += 2; continue
            quoted = not quoted
        elif value == 44 and not quoted:
            fields.append(body[start:position]); pieces.append(b","); start = position + 1
        position += 1
    if quoted: raise ValueError("unterminated CSV quote")
    fields.append(body[start:]); pieces.append(ending)
    # pieces are separators after every field; retaining raw tokens means both
    # commas and quote spelling reconstruct exactly.
    return tuple(pieces), tuple(fields)


def _rows(data: bytes) -> list[tuple[tuple[bytes, ...], tuple[bytes, ...]]]:
    rows = []
    for raw in data.splitlines(keepends=True):
        rows.append(_record(raw))
    if data and not rows: raise ValueError("CSV record discovery failed")
    # splitlines omits a zero-length final record, which is already implicit in
    # the final terminator and must not be invented.
    return rows


def _column(values: list[bytes]) -> bytes:
    palette = sorted(set(values)); counts = [values.count(value) for value in palette]
    lookup = {value: index for index, value in enumerate(palette)}; ids = [lookup[value] for value in values]
    ordering = order_encode(ids, counts, 3)  # mode 3 = dynamic remaining-count arithmetic
    out = bytearray(vencode(len(palette)))
    for value, count in zip(palette, counts): out.extend(_pack(value)); out.extend(vencode(count))
    out.extend(_pack(ordering)); return bytes(out)


def _decode_column(blob: bytes, n: int) -> list[bytes]:
    count, position = vdecode(blob, 0); palette = []; counts = []
    for _ in range(count):
        value, position = _read(blob, position); amount, position = vdecode(blob, position)
        if not amount: raise ValueError("zero CSV palette count")
        palette.append(value); counts.append(amount)
    ordering, position = _read(blob, position)
    if position != len(blob) or sum(counts) != n: raise ValueError("invalid CSV column composition")
    return [palette[index] for index in order_decode(ordering, counts)]


def encode(data: bytes, variant: str) -> bytes:
    if variant not in VARIANTS: raise ValueError("unknown database CSV variant")
    if variant == "literal": return MAGIC + bytes((LITERAL,)) + _pack(data)
    try: rows = _rows(data)
    except ValueError: return MAGIC + bytes((LITERAL,)) + _pack(data)
    templates: list[tuple[bytes, ...]] = []; mapping = {}; sequence = []; columns: dict[tuple[int, int], list[bytes]] = defaultdict(list)
    for pieces, fields in rows:
        key = (pieces, len(fields)); identifier = mapping.get(key)
        if identifier is None: identifier = len(templates); mapping[key] = identifier; templates.append(pieces)
        sequence.append(identifier)
        for slot, value in enumerate(fields): columns[identifier, slot].append(value)
    out = bytearray(MAGIC + bytes((DICTIONARY_REMAINING,)) + vencode(len(templates)))
    for pieces in templates:
        out.extend(vencode(len(pieces)))
        for piece in pieces: out.extend(_pack(piece))
    out.extend(vencode(len(sequence)))
    for identifier in sequence: out.extend(vencode(identifier))
    for identifier, pieces in enumerate(templates):
        for slot in range(len(pieces)):
            out.extend(_pack(_column(columns[identifier, slot])))
    return bytes(out)


def decode(frame: bytes) -> bytes:
    if not frame.startswith(MAGIC) or len(frame) == len(MAGIC): raise ValueError("invalid database CSV frame")
    mode = frame[len(MAGIC)]; position = len(MAGIC) + 1
    if mode == LITERAL:
        data, position = _read(frame, position)
        if position != len(frame): raise ValueError("trailing literal CSV bytes")
        return data
    if mode != DICTIONARY_REMAINING: raise ValueError("unknown database CSV mode")
    template_count, position = vdecode(frame, position); templates = []
    for _ in range(template_count):
        pieces_count, position = vdecode(frame, position); pieces = []
        if not pieces_count: raise ValueError("empty CSV template")
        for _ in range(pieces_count): piece, position = _read(frame, position); pieces.append(piece)
        templates.append(tuple(pieces))
    row_count, position = vdecode(frame, position); sequence = []
    counts = [0] * len(templates)
    for _ in range(row_count):
        identifier, position = vdecode(frame, position)
        if identifier >= len(templates): raise ValueError("invalid CSV template sequence")
        sequence.append(identifier); counts[identifier] += 1
    columns = {}
    for identifier, pieces in enumerate(templates):
        for slot in range(len(pieces)):
            blob, position = _read(frame, position); columns[identifier, slot] = iter(_decode_column(blob, counts[identifier]))
    if position != len(frame): raise ValueError("trailing database CSV frame")
    output = bytearray()
    for identifier in sequence:
        for slot, piece in enumerate(templates[identifier]): output.extend(next(columns[identifier, slot])); output.extend(piece)
    return bytes(output)


def inspect(data: bytes) -> dict:
    try: rows = _rows(data)
    except ValueError as error: return {"eligible": False, "reason": str(error), "raw_bytes": len(data)}
    templates = Counter((pieces, len(fields)) for pieces, fields in rows)
    termination = Counter(piece[-1:] for pieces, _fields in rows for piece in pieces[-1:])
    values = [value for _pieces, fields in rows for value in fields]
    return {"eligible": True, "raw_bytes": len(data), "record_count": len(rows), "template_count": len(templates),
            "repeated_template_records": sum(count - 1 for count in templates.values()), "field_token_count": len(values),
            "distinct_field_tokens": len(set(values)), "repeated_field_tokens": len(values) - len(set(values)),
            "termination_bytes": {key.hex(): value for key, value in termination.items()}, "packing": {"alignment_padding_bytes": 0,
            "record_terminators_preserved_in_template_pieces": True, "capacity_sharing": "not claimed; remaining-count arithmetic and downstream PAQ may overlap"},
            "variants": {name: len(encode(data, name)) for name in VARIANTS}}
