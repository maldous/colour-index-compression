#!/usr/bin/env python3
"""D2: page-skeleton-relative raw value columns for bounded Hutter research.

Unlike D1's one serial page-value stream, D2 emits every value in the shared
logical column identified by ``(page skeleton id, placeholder slot)``.  It is a
byte transform only: no numeric, dictionary, count, or entropy model is hidden
inside it.  Every page order record, literal exception, value length and column
boundary lives in the frame.
"""

from __future__ import annotations

from collections import defaultdict

from benchmarks import hutter_structure as d1
from benchmarks import markup_columns


MAGIC = b"HSC2\x01"
MAX_SKELETONS = 65536
MAX_COLUMNS = 1_000_000


def _pack_stream(value: bytes) -> bytes:
    return d1.vencode(len(value)) + value


def _read_stream(blob: bytes, position: int) -> tuple[bytes, int]:
    size, position = d1.vdecode(blob, position)
    if position + size > len(blob):
        raise ValueError("truncated D2 stream")
    return blob[position : position + size], position + size


def _frame(original: int, descriptor: bytes, dictionary: bytes, literal: bytes, columns: bytes) -> bytes:
    return MAGIC + d1.vencode(original) + _pack_stream(descriptor) + _pack_stream(dictionary) + _pack_stream(literal) + _pack_stream(columns)


def _unframe(frame: bytes) -> tuple[int, bytes, bytes, bytes, bytes]:
    if not frame.startswith(MAGIC):
        raise ValueError("invalid D2 frame magic/version")
    original, position = d1.vdecode(frame, len(MAGIC))
    descriptor, position = _read_stream(frame, position)
    dictionary, position = _read_stream(frame, position)
    literal, position = _read_stream(frame, position)
    columns, position = _read_stream(frame, position)
    if position != len(frame):
        raise ValueError("trailing D2 frame bytes")
    return original, descriptor, dictionary, literal, columns


def _parts(data: bytes) -> tuple[bytes, bytes, bytes, bytes, int, int, int]:
    """Reproduce D1 complete-page discovery while columnizing only values."""
    descriptor = bytearray()
    literal = bytearray()
    skeletons: list[bytes] = []
    skeleton_ids: dict[bytes, int] = {}
    columns: dict[tuple[int, int], list[bytes]] = defaultdict(list)
    position = 0
    pages = literal_records = 0

    def add_literal(value: bytes) -> None:
        nonlocal literal_records
        if value:
            descriptor.append(0)
            descriptor.extend(d1.vencode(len(value)))
            literal.extend(value)
            literal_records += 1

    while True:
        start = data.find(b"<page>", position)
        if start < 0:
            add_literal(data[position:])
            break
        end = data.find(b"</page>", start + 6)
        if end < 0:
            add_literal(data[position:])
            break
        add_literal(data[position:start])
        page = data[start : end + 7]
        skeleton, values = d1._page_skeleton(page)
        identifier = skeleton_ids.get(skeleton)
        if identifier is None:
            if len(skeletons) == MAX_SKELETONS:
                # Exact fallback: do not consume a page when the bounded table is full.
                add_literal(page)
                position = end + 7
                continue
            identifier = len(skeletons)
            skeleton_ids[skeleton] = identifier
            skeletons.append(skeleton)
        descriptor.append(1)
        descriptor.extend(d1.vencode(identifier))
        for slot, value in enumerate(values):
            columns[identifier, slot].append(value)
        pages += 1
        position = end + 7

    dictionary = d1._serialize_skeletons(skeletons)
    if len(columns) > MAX_COLUMNS:
        raise ValueError("D2 slot column limit exceeded")
    encoded_columns = bytearray(d1.vencode(len(columns)))
    for (identifier, slot), values in sorted(columns.items()):
        stream = bytearray()
        for value in values:
            stream.extend(_pack_stream(value))
        encoded_columns.extend(d1.vencode(identifier))
        encoded_columns.extend(d1.vencode(slot))
        encoded_columns.extend(d1.vencode(len(values)))
        encoded_columns.extend(_pack_stream(bytes(stream)))
    return bytes(descriptor), dictionary, bytes(literal), bytes(encoded_columns), pages, literal_records, len(columns)


def _decode_columns(blob: bytes, skeletons: list[bytes], page_counts: dict[int, int]) -> dict[tuple[int, int], list[bytes]]:
    count, position = d1.vdecode(blob, 0)
    if count > MAX_COLUMNS:
        raise ValueError("D2 oversized column table")
    result: dict[tuple[int, int], list[bytes]] = {}
    expected = {(identifier, slot): occurrences
                for identifier, occurrences in page_counts.items()
                for slot in range(d1._placeholder_count(skeletons[identifier]))}
    if count != len(expected):
        raise ValueError("D2 column count does not match page descriptors")
    for _ in range(count):
        identifier, position = d1.vdecode(blob, position)
        slot, position = d1.vdecode(blob, position)
        values_count, position = d1.vdecode(blob, position)
        stream, position = _read_stream(blob, position)
        key = (identifier, slot)
        if key not in expected or key in result or values_count != expected[key]:
            raise ValueError("invalid D2 column declaration")
        values = []
        value_position = 0
        for _ in range(values_count):
            value, value_position = _read_stream(stream, value_position)
            values.append(value)
        if value_position != len(stream):
            raise ValueError("trailing D2 column value bytes")
        result[key] = values
    if position != len(blob) or set(result) != set(expected):
        raise ValueError("incomplete D2 column table")
    return result


def _page_counts(descriptor: bytes, skeletons: list[bytes]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    position = 0
    while position < len(descriptor):
        kind = descriptor[position]
        position += 1
        if kind == 0:
            _, position = d1.vdecode(descriptor, position)
        elif kind == 1:
            identifier, position = d1.vdecode(descriptor, position)
            if identifier >= len(skeletons):
                raise ValueError("unknown D2 page skeleton")
            counts[identifier] += 1
        else:
            raise ValueError("invalid D2 descriptor kind")
    return counts


def _slot_classes(skeleton: bytes, values_by_slot: list[list[bytes]]) -> list[str]:
    """Return stable tag-ancestry classes for every skeleton placeholder."""
    stack: list[bytes] = []
    raw = bytearray()
    labels: list[str] = []
    position = 0

    def update_raw() -> None:
        for match in d1.TOKEN.finditer(bytes(raw)):
            markup_columns.update_stack(stack, match.group())
        raw.clear()

    while position < len(skeleton):
        byte = skeleton[position]
        position += 1
        if byte:
            raw.append(byte)
            continue
        if position == len(skeleton):
            raise ValueError("truncated D2 skeleton escape")
        kind = skeleton[position]
        position += 1
        if kind == 0:
            raw.append(0)
            continue
        if kind != 1:
            raise ValueError("invalid D2 skeleton escape")
        update_raw()
        values = values_by_slot[len(labels)]
        current = stack[-1] if stack else b""
        # Text ancestry is an absolute guard: even an empty/whitespace text
        # value must never become eligible for a short-field order codec.
        if current == b"text": labels.append("articletext")
        elif values and all(not value.strip() for value in values): labels.append("whitespace")
        elif current == b"title": labels.append("title")
        elif current == b"timestamp": labels.append("timestamp")
        elif current in (b"username", b"ip") or b"contributor" in stack: labels.append("contributor")
        elif current == b"id": labels.append("revisionid" if b"revision" in stack else "pageid")
        else: labels.append("other")
    if len(labels) != len(values_by_slot):
        raise ValueError("D2 slot class/skeleton mismatch")
    return labels


def extract_columns(data: bytes, short_value_limit: int = 256) -> dict:
    """Expose D2 columns for a separately owned raw/count/rank coding layer.

    Article text is deliberately never eligible for pre-entropy order coding.
    The returned values are raw bytes and the literal exceptions remain separate.
    """
    if not 1 <= short_value_limit <= 1 << 20:
        raise ValueError("invalid D2 short-value limit")
    descriptor, dictionary, literal, column_blob, pages, literal_records, slot_columns = _parts(data)
    skeletons = d1._deserialize_skeletons(dictionary)
    columns = _decode_columns(column_blob, skeletons, _page_counts(descriptor, skeletons))
    profiles = []
    for identifier, skeleton in enumerate(skeletons):
        per_slot = [columns[identifier, slot] for slot in range(d1._placeholder_count(skeleton))]
        for slot, (field_class, values) in enumerate(zip(_slot_classes(skeleton, per_slot), per_slot)):
            raw_values = b"".join(_pack_stream(value) for value in values)
            table_cost = (len(d1.vencode(identifier)) + len(d1.vencode(slot)) + len(d1.vencode(len(values)))
                          + len(_pack_stream(raw_values)))
            profiles.append({"skeleton_id": identifier, "slot_ordinal": slot, "field_class": field_class,
                             "values": values, "value_count": len(values), "distinct_values": len(set(values)),
                             "repeated_occurrences": len(values) - len(set(values)), "raw_values_bytes": len(raw_values),
                             "raw_column_table_bytes": table_cost, "complete_page_values": True,
                             "eligible_short_field": field_class != "articletext" and all(len(value) <= short_value_limit for value in values)})
    return {"descriptor": descriptor, "dictionary": dictionary, "literal_exceptions": literal,
            "columns": profiles, "pages": pages, "literal_records": literal_records,
            "skeletoncount": len(skeletons), "slotcolumns": slot_columns}


def _decode_parts(descriptor: bytes, dictionary: bytes, literal: bytes, column_blob: bytes) -> bytes:
    skeletons = d1._deserialize_skeletons(dictionary)
    page_counts = _page_counts(descriptor, skeletons)
    position = 0
    columns = _decode_columns(column_blob, skeletons, page_counts)
    positions = defaultdict(int)
    literal_position = position = 0
    output = bytearray()
    while position < len(descriptor):
        kind = descriptor[position]
        position += 1
        if kind == 0:
            size, position = d1.vdecode(descriptor, position)
            if literal_position + size > len(literal):
                raise ValueError("D2 literal stream exhausted")
            output.extend(literal[literal_position : literal_position + size])
            literal_position += size
            continue
        identifier, position = d1.vdecode(descriptor, position)
        slots = d1._placeholder_count(skeletons[identifier])
        values = []
        for slot in range(slots):
            key = (identifier, slot)
            at = positions[key]
            if at == len(columns[key]):
                raise ValueError("D2 column exhausted")
            values.append(columns[key][at])
            positions[key] += 1
        output.extend(d1._restore_page(skeletons[identifier], values))
    if literal_position != len(literal) or any(positions[key] != len(values) for key, values in columns.items()):
        raise ValueError("unused D2 logical stream bytes")
    return bytes(output)


def encode(data: bytes) -> tuple[bytes, dict[str, int]]:
    descriptor, dictionary, literal, columns, pages, literal_records, slot_columns = _parts(data)
    frame = _frame(len(data), descriptor, dictionary, literal, columns)
    framing = len(frame) - len(descriptor) - len(dictionary) - len(literal) - len(columns)
    accounting = {"physical_bytes": len(frame), "descriptor_bytes": len(descriptor),
                  "dictionary_bytes": len(dictionary), "literal_bytes": len(literal),
                  "column_stream_bytes": len(columns), "framing_bytes": framing,
                  "skeletoncount": len(d1._deserialize_skeletons(dictionary)), "slotcolumns": slot_columns,
                  "pages": pages, "literal_records": literal_records}
    if framing < 0 or sum(accounting[key] for key in ("descriptor_bytes", "dictionary_bytes", "literal_bytes", "column_stream_bytes", "framing_bytes")) != len(frame):
        raise AssertionError("D2 physical accounting mismatch")
    return frame, accounting


def decode(frame: bytes) -> bytes:
    original, descriptor, dictionary, literal, columns = _unframe(frame)
    restored = _decode_parts(descriptor, dictionary, literal, columns)
    if len(restored) != original:
        raise ValueError("D2 restored length mismatch")
    return restored
