#!/usr/bin/env python3
"""Bounded, byte-exact Wikipedia structural representations.

These are Hutter-specific pre-entropy frames.  They do not parse or reserialize
XML: every source byte remains in an explicitly ordered stream, and incomplete
or outside-page material stays literal.  Frames are self-contained so a decoder
needs no source, filename, dictionary or article order.
"""

from __future__ import annotations

from benchmarks.markup_columns import TOKEN
from cix.multinomial import vdecode, vencode


MAGIC = b"HSTR1"
CONTROL, TYPED_STREAMS, PAGE_SKELETONS = 0, 1, 2
MODE = {"control": CONTROL, "C": TYPED_STREAMS, "D": PAGE_SKELETONS}


def _frame(mode: int, original: int, descriptor: bytes, streams: list[bytes]) -> bytes:
    return MAGIC + bytes((mode,)) + vencode(original) + vencode(len(descriptor)) + descriptor + vencode(len(streams)) + b"".join(vencode(len(stream)) + stream for stream in streams)


def _unframe(frame: bytes) -> tuple[int, int, bytes, list[bytes]]:
    if not frame.startswith(MAGIC) or len(frame) <= len(MAGIC):
        raise ValueError("invalid structural frame")
    mode = frame[len(MAGIC)]
    original, position = vdecode(frame, len(MAGIC) + 1)
    descriptor_bytes, position = vdecode(frame, position)
    if position + descriptor_bytes > len(frame):
        raise ValueError("truncated structural descriptor")
    descriptor = frame[position : position + descriptor_bytes]
    position += descriptor_bytes
    count, position = vdecode(frame, position)
    if count > 4:
        raise ValueError("invalid structural stream count")
    streams = []
    for _ in range(count):
        size, position = vdecode(frame, position)
        if position + size > len(frame):
            raise ValueError("truncated structural stream")
        streams.append(frame[position : position + size])
        position += size
    if position != len(frame):
        raise ValueError("trailing structural frame bytes")
    return mode, original, descriptor, streams


def _costs(frame: bytes, descriptor: bytes, components: dict[str, int], **extra: int) -> dict[str, int]:
    accounted = len(descriptor) + sum(components.values())
    result = {"physical_bytes": len(frame), "descriptor_bytes": len(descriptor), **components,
              "framing_bytes": len(frame) - accounted, **extra}
    if result["framing_bytes"] < 0 or sum(result[k] for k in ("descriptor_bytes", *components, "framing_bytes")) != len(frame):
        raise AssertionError("structural physical accounting mismatch")
    return result


def _typed_parts(data: bytes) -> tuple[bytes, bytes, bytes, int]:
    descriptor = bytearray()
    tags = bytearray()
    text = bytearray()
    at = 0
    records = 0

    def add(kind: int, value: bytes) -> None:
        nonlocal records
        if not value:
            return
        descriptor.append(kind)
        descriptor.extend(vencode(len(value)))
        (tags if kind else text).extend(value)
        records += 1

    for match in TOKEN.finditer(data):
        add(0, data[at : match.start()])
        add(1, match.group())
        at = match.end()
    add(0, data[at:])
    return bytes(descriptor), bytes(tags), bytes(text), records


def _decode_typed(descriptor: bytes, tags: bytes, text: bytes) -> bytes:
    output = bytearray()
    position = tag_position = text_position = 0
    while position < len(descriptor):
        kind = descriptor[position]
        position += 1
        if kind not in (0, 1):
            raise ValueError("invalid typed-stream record")
        size, position = vdecode(descriptor, position)
        stream, current = (tags, tag_position) if kind else (text, text_position)
        if current + size > len(stream):
            raise ValueError("typed stream exhausted")
        output.extend(stream[current : current + size])
        if kind:
            tag_position += size
        else:
            text_position += size
    if tag_position != len(tags) or text_position != len(text):
        raise ValueError("unused typed stream bytes")
    return bytes(output)


def _page_skeleton(page: bytes) -> tuple[bytes, list[bytes]]:
    skeleton = bytearray()
    values: list[bytes] = []
    at = 0
    for match in TOKEN.finditer(page):
        values.append(page[at : match.start()])
        skeleton.extend(b"\0\1")
        skeleton.extend(match.group().replace(b"\0", b"\0\0"))
        at = match.end()
    values.append(page[at:])
    skeleton.extend(b"\0\1")
    return bytes(skeleton), values


def _restore_page(skeleton: bytes, values: list[bytes]) -> bytes:
    output = bytearray()
    position = value_position = 0
    while position < len(skeleton):
        byte = skeleton[position]
        position += 1
        if byte:
            output.append(byte)
            continue
        if position == len(skeleton):
            raise ValueError("truncated page skeleton escape")
        kind = skeleton[position]
        position += 1
        if kind == 0:
            output.append(0)
        elif kind == 1:
            if value_position == len(values):
                raise ValueError("page value underflow")
            output.extend(values[value_position])
            value_position += 1
        else:
            raise ValueError("invalid page skeleton escape")
    if value_position != len(values):
        raise ValueError("unused page values")
    return bytes(output)


def _placeholder_count(skeleton: bytes) -> int:
    """Count placeholders using the same escaping grammar as the inverse."""
    position = count = 0
    while position < len(skeleton):
        byte = skeleton[position]
        position += 1
        if byte:
            continue
        if position == len(skeleton):
            raise ValueError("truncated page skeleton escape")
        kind = skeleton[position]
        position += 1
        if kind == 0:
            continue
        if kind == 1:
            count += 1
            continue
        raise ValueError("invalid page skeleton escape")
    return count


def _serialize_skeletons(skeletons: list[bytes]) -> bytes:
    return vencode(len(skeletons)) + b"".join(vencode(len(skeleton)) + skeleton for skeleton in skeletons)


def _deserialize_skeletons(blob: bytes) -> list[bytes]:
    count, position = vdecode(blob, 0)
    if count > 65536:
        raise ValueError("too many page skeletons")
    skeletons = []
    for _ in range(count):
        size, position = vdecode(blob, position)
        if position + size > len(blob):
            raise ValueError("truncated page skeleton")
        skeletons.append(blob[position : position + size])
        position += size
    if position != len(blob):
        raise ValueError("trailing page skeleton bytes")
    return skeletons


def _page_parts(data: bytes) -> tuple[bytes, bytes, bytes, bytes, int, int]:
    descriptor = bytearray()
    literal = bytearray()
    values = bytearray()
    skeletons: list[bytes] = []
    skeleton_ids: dict[bytes, int] = {}
    position = 0
    page_records = literal_records = 0

    def add_literal(value: bytes) -> None:
        nonlocal literal_records
        if value:
            descriptor.append(0)
            descriptor.extend(vencode(len(value)))
            literal.extend(value)
            literal_records += 1

    while True:
        start = data.find(b"<page>", position)
        if start < 0:
            add_literal(data[position:])
            break
        end = data.find(b"</page>", start + 6)
        if end < 0:
            add_literal(data[position:])  # truncated region: opaque literal fallback
            break
        add_literal(data[position:start])
        page = data[start : end + 7]
        skeleton, page_values = _page_skeleton(page)
        identifier = skeleton_ids.get(skeleton)
        if identifier is None:
            identifier = len(skeletons)
            skeleton_ids[skeleton] = identifier
            skeletons.append(skeleton)
        descriptor.append(1)
        descriptor.extend(vencode(identifier))
        for value in page_values:
            values.extend(vencode(len(value)))
            values.extend(value)
        page_records += 1
        position = end + 7
    return bytes(descriptor), _serialize_skeletons(skeletons), bytes(literal), bytes(values), page_records, literal_records


def _decode_pages(descriptor: bytes, dictionary: bytes, literal: bytes, values: bytes) -> bytes:
    skeletons = _deserialize_skeletons(dictionary)
    output = bytearray()
    position = literal_position = value_position = 0
    while position < len(descriptor):
        kind = descriptor[position]
        position += 1
        if kind == 0:
            size, position = vdecode(descriptor, position)
            if literal_position + size > len(literal):
                raise ValueError("literal stream exhausted")
            output.extend(literal[literal_position : literal_position + size])
            literal_position += size
        elif kind == 1:
            identifier, position = vdecode(descriptor, position)
            if identifier >= len(skeletons):
                raise ValueError("unknown page skeleton")
            count = _placeholder_count(skeletons[identifier])
            page_values = []
            for _ in range(count):
                size, value_position = vdecode(values, value_position)
                if value_position + size > len(values):
                    raise ValueError("page value stream exhausted")
                page_values.append(values[value_position : value_position + size])
                value_position += size
            output.extend(_restore_page(skeletons[identifier], page_values))
        else:
            raise ValueError("invalid page descriptor record")
    if literal_position != len(literal) or value_position != len(values):
        raise ValueError("unused page stream bytes")
    return bytes(output)


def encode(data: bytes, mode: str) -> tuple[bytes, dict[str, int]]:
    """Return a self-contained physical transform frame and exact component costs."""
    code = MODE.get(mode)
    if code is None:
        raise ValueError("mode must be control, C, or D")
    if code == CONTROL:
        frame = _frame(code, len(data), b"", [data])
        return frame, _costs(frame, b"", {"literal_bytes": len(data)}, records=1)
    if code == TYPED_STREAMS:
        descriptor, tags, text, records = _typed_parts(data)
        frame = _frame(code, len(data), descriptor, [tags, text])
        return frame, _costs(frame, descriptor, {"tag_bytes": len(tags), "text_bytes": len(text)}, records=records)
    descriptor, dictionary, literal, values, pages, literals = _page_parts(data)
    frame = _frame(code, len(data), descriptor, [dictionary, literal, values])
    return frame, _costs(frame, descriptor, {"dictionary_bytes": len(dictionary), "literal_bytes": len(literal), "value_bytes": len(values)}, page_records=pages, literal_records=literals)


def decode(frame: bytes, mode: str | None = None, accounting: dict | None = None) -> bytes:
    """Restore from the frame alone; optional adapter arguments are ignored."""
    del mode, accounting
    code, original, descriptor, streams = _unframe(frame)
    if code == CONTROL and len(streams) == 1 and not descriptor:
        restored = streams[0]
    elif code == TYPED_STREAMS and len(streams) == 2:
        restored = _decode_typed(descriptor, streams[0], streams[1])
    elif code == PAGE_SKELETONS and len(streams) == 3:
        restored = _decode_pages(descriptor, streams[0], streams[1], streams[2])
    else:
        raise ValueError("invalid structural mode/streams")
    if len(restored) != original:
        raise ValueError("structural restored length mismatch")
    return restored
