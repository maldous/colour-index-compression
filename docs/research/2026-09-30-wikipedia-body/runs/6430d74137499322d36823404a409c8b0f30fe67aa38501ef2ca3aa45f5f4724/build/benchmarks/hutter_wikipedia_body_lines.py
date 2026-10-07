#!/usr/bin/env python3
"""Byte-exact, bounded global body-line families for Hutter research.

This is deliberately a representation experiment, not a text parser.  Only
complete ``<text...>...</text>`` bodies and newline-terminated 48--512 byte
lines are examined.  The frame contains every rule, dictionary entry, member
order, replacement value, boundary and literal exception required by its
decoder.
"""

from __future__ import annotations

from collections import defaultdict
import re

from cix.multinomial import vdecode, vencode


MAGIC = b"HWBL1"
RULES = (b"complete-text-body;newline-line;48<=core<=512;literal>=24;"
         b"members>=3;bodies>=2;distinct-raw>=2;LINK|URL|NUMBER")
TEXT_OPEN = re.compile(br"<text(?:\s[^<>]*)?>")
LINK = re.compile(br"\[\[[^\]\n]{1,512}\]\]")
URL = re.compile(br"https?://[^/\s|}\]<>]+(?:/[^\s|}\]<>]*)?", re.I)
NUMBER = re.compile(br"(?<![A-Za-z0-9])[-+]?\d{1,18}(?:\.\d{1,12})?(?![A-Za-z0-9])")
TOKEN = re.compile(br"\[\[[^\]\n]{1,512}\]\]|https?://[^/\s|}\]<>]+(?:/[^\s|}\]<>]*)?|(?<![A-Za-z0-9])[-+]?\d{1,18}(?:\.\d{1,12})?(?![A-Za-z0-9])", re.I)

LITERAL, LINK_HOLE, URL_HOLE, NUMBER_HOLE = 0, 1, 2, 3


def _pack(value: bytes) -> bytes:
    return vencode(len(value)) + value


def _read(blob: bytes, position: int) -> tuple[bytes, int]:
    size, position = vdecode(blob, position)
    if position + size > len(blob):
        raise ValueError("truncated body-line stream")
    return blob[position:position + size], position + size


def _kind(value: bytes) -> int:
    if LINK.fullmatch(value):
        return LINK_HOLE
    if URL.fullmatch(value):
        return URL_HOLE
    if NUMBER.fullmatch(value):
        return NUMBER_HOLE
    raise ValueError("unrecognized body-line hole")


def _skeleton(line: bytes) -> tuple[tuple[tuple[int, bytes], ...], tuple[bytes, ...]] | None:
    """Split a raw line into literal segments and exact raw replacement holes."""
    parts: list[tuple[int, bytes]] = []
    holes: list[bytes] = []
    position = literal_bytes = 0
    for match in TOKEN.finditer(line):
        literal = line[position:match.start()]
        parts.append((LITERAL, literal)); literal_bytes += len(literal)
        value = match.group()
        parts.append((_kind(value), b"")); holes.append(value)
        position = match.end()
    parts.append((LITERAL, line[position:])); literal_bytes += len(line) - position
    if not holes or literal_bytes < 24:
        return None
    return tuple(parts), tuple(holes)


def _candidate_lines(data: bytes):
    """Yield complete body line candidates without interpreting XML or text."""
    position = body_id = 0
    while True:
        opening = TEXT_OPEN.search(data, position)
        if not opening:
            return
        body_start = opening.end()
        close = data.find(b"</text>", body_start)
        if close < 0:
            return  # The incomplete body is an opaque literal exception.
        body = data[body_start:close]
        at = body_start
        for chunk in body.splitlines(keepends=True):
            stop = at + len(chunk)
            # A final unterminated line is intentionally not a complete line.
            if chunk.endswith(b"\n"):
                core = chunk.rstrip(b"\r\n")
                if 48 <= len(core) <= 512:
                    split = _skeleton(chunk)
                    if split is not None:
                        yield at, stop, body_id, chunk, split[0], split[1]
            at = stop
        body_id += 1
        position = close + len(b"</text>")


def _select(data: bytes):
    """First pass: deterministically select the globally eligible families."""
    families: dict[tuple[tuple[int, bytes], ...], list[tuple[int, int, int, bytes, tuple[bytes, ...]]]] = defaultdict(list)
    order: list[tuple[tuple[int, bytes], ...]] = []
    for start, stop, body_id, raw, skeleton, holes in _candidate_lines(data):
        if skeleton not in families:
            order.append(skeleton)
        families[skeleton].append((start, stop, body_id, raw, holes))
    selected = []
    index: dict[int, tuple[int, tuple[bytes, ...]]] = {}
    for skeleton in order:
        members = families[skeleton]
        if len(members) < 3 or len({body_id for _start, _stop, body_id, _raw, _holes in members}) < 2:
            continue
        if len({raw for _start, _stop, _body_id, raw, _holes in members}) < 2:
            continue
        family_id = len(selected)
        selected.append((skeleton, members))
        for start, _stop, _body_id, _raw, holes in members:
            if start in index:
                raise AssertionError("overlapping body-line candidates")
            index[start] = family_id, holes
    return selected, index


def _serialize_dictionary(families: list[tuple[tuple[tuple[int, bytes], ...], list]]) -> bytes:
    output = bytearray(vencode(len(families)))
    for skeleton, _members in families:
        output.extend(vencode(len(skeleton)))
        for kind, literal in skeleton:
            output.append(kind)
            if kind == LITERAL:
                output.extend(_pack(literal))
    return bytes(output)


def _deserialize_dictionary(blob: bytes) -> list[tuple[tuple[int, bytes], ...]]:
    count, position = vdecode(blob, 0)
    if count > 1_000_000:
        raise ValueError("too many body-line families")
    result = []
    for _ in range(count):
        pieces, position = vdecode(blob, position)
        if not 1 <= pieces <= 4096:
            raise ValueError("invalid body-line skeleton size")
        skeleton = []
        for _ in range(pieces):
            if position == len(blob):
                raise ValueError("truncated body-line skeleton")
            kind = blob[position]; position += 1
            if kind == LITERAL:
                literal, position = _read(blob, position)
                skeleton.append((kind, literal))
            elif kind in (LINK_HOLE, URL_HOLE, NUMBER_HOLE):
                skeleton.append((kind, b""))
            else:
                raise ValueError("invalid body-line skeleton token")
        result.append(tuple(skeleton))
    if position != len(blob):
        raise ValueError("trailing body-line dictionary bytes")
    return result


def _descriptor(data: bytes, families, index: dict[int, tuple[int, tuple[bytes, ...]]]) -> tuple[bytes, int, int]:
    members = [(start, stop, family_id, holes)
               for family_id, (_skeleton, grouped) in enumerate(families)
               for start, stop, _body, _raw, holes in grouped]
    members.sort()
    output = bytearray()
    cursor = literal_bytes = hole_bytes = 0
    for start, stop, family_id, holes in members:
        if start < cursor:
            raise AssertionError("overlapping selected body lines")
        raw = data[cursor:start]
        if raw:
            output.append(0); output.extend(_pack(raw)); literal_bytes += len(raw)
        output.append(1); output.extend(vencode(family_id)); output.extend(vencode(len(holes)))
        for hole in holes:
            output.extend(_pack(hole)); hole_bytes += len(hole)
        cursor = stop
    raw = data[cursor:]
    if raw:
        output.append(0); output.extend(_pack(raw)); literal_bytes += len(raw)
    return bytes(output), literal_bytes, hole_bytes


def encode(data: bytes) -> tuple[bytes, dict[str, int]]:
    """Encode a self-contained body-line representation and exact accounting."""
    families, index = _select(data)
    dictionary = _serialize_dictionary(families)
    descriptor, literal_bytes, hole_bytes = _descriptor(data, families, index)
    frame = MAGIC + vencode(len(data)) + _pack(RULES) + _pack(dictionary) + _pack(descriptor)
    framing = len(MAGIC) + len(vencode(len(data)))
    selected_members = sum(len(members) for _skeleton, members in families)
    selected_source_bytes = sum(stop - start for _skeleton, members in families for start, stop, _body, _raw, _holes in members)
    accounting = {"physical_bytes": len(frame), "rules_bytes": len(_pack(RULES)), "dictionary_bytes": len(_pack(dictionary)),
                  "descriptor_bytes": len(_pack(descriptor)), "framing_bytes": framing, "selected_family_count": len(families),
                  "selected_member_count": selected_members, "selected_source_bytes": selected_source_bytes,
                  "literal_payload_bytes": literal_bytes, "hole_payload_bytes": hole_bytes}
    if sum(accounting[key] for key in ("rules_bytes", "dictionary_bytes", "descriptor_bytes", "framing_bytes")) != len(frame):
        raise AssertionError("body-line physical accounting mismatch")
    return frame, accounting


def decode(frame: bytes) -> bytes:
    if not frame.startswith(MAGIC):
        raise ValueError("invalid body-line frame magic/version")
    original, position = vdecode(frame, len(MAGIC))
    rules, position = _read(frame, position)
    if rules != RULES:
        raise ValueError("unsupported body-line rule set")
    dictionary_blob, position = _read(frame, position)
    descriptor, position = _read(frame, position)
    if position != len(frame):
        raise ValueError("trailing body-line frame bytes")
    families = _deserialize_dictionary(dictionary_blob)
    output = bytearray(); position = 0
    while position < len(descriptor):
        kind = descriptor[position]; position += 1
        if kind == 0:
            literal, position = _read(descriptor, position); output.extend(literal)
            continue
        if kind != 1:
            raise ValueError("invalid body-line descriptor token")
        family, position = vdecode(descriptor, position)
        holes_count, position = vdecode(descriptor, position)
        if family >= len(families):
            raise ValueError("unknown body-line family")
        skeleton = families[family]
        expected = sum(kind != LITERAL for kind, _literal in skeleton)
        if holes_count != expected:
            raise ValueError("body-line hole count mismatch")
        holes = []
        for _ in range(holes_count):
            hole, position = _read(descriptor, position); holes.append(hole)
        hole_position = 0
        for token, literal in skeleton:
            if token == LITERAL:
                output.extend(literal)
            else:
                hole = holes[hole_position]; hole_position += 1
                if _kind(hole) != token:
                    raise ValueError("body-line hole rule mismatch")
                output.extend(hole)
    if len(output) != original:
        raise ValueError("body-line restored length mismatch")
    return bytes(output)
