"""Self-contained paragraph/newline body-unit representation experiment.

The two modes are deliberately alternative segmentations.  The frame never
requires the original XML, a parser, or external dictionary during decoding.
"""
from __future__ import annotations

from collections import defaultdict

from benchmarks import hutter_wikipedia_body_lines as body
from benchmarks import hutter_wikipedia_unit_profile as profile
from cix.multinomial import vdecode, vencode


MAGIC = b"HWBU1"
MAX_SOURCE = 64 * 1024 * 1024
MAX_FRAME = 128 * 1024 * 1024
MODES = {"paragraph-16384": 1, "line-4096": 2}
MODE_NAMES = {value: key for key, value in MODES.items()}
RULES = {
    "paragraph-16384": (b"complete-text-body;blankline-paragraph;48<=unit<=16384;literal>=24;"
                          b"members>=3;bodies>=2;distinct-raw>=2;LINK|URL|NUMBER"),
    "line-4096": (b"complete-text-body;newline-terminated-line;48<=unit<=4096;literal>=24;"
                    b"members>=3;bodies>=2;distinct-raw>=2;LINK|URL|NUMBER"),
}


def _pack(value: bytes) -> bytes:
    return vencode(len(value)) + value


def _read(blob: bytes, position: int) -> tuple[bytes, int]:
    size, position = vdecode(blob, position)
    if size > MAX_FRAME or position + size > len(blob):
        raise ValueError("truncated or excessive body-unit stream")
    return blob[position:position + size], position + size


def _paragraphs(data: bytes):
    """Exact shared eligibility generator; blank separators remain literal."""
    yield from profile.paragraphs16384(data)


def _lines(data: bytes):
    """Exact shared eligibility generator for newline-terminated units."""
    yield from profile.newline4096(data)


def _candidates(data: bytes, mode: str):
    generator = _paragraphs if mode == "paragraph-16384" else _lines
    for start, stop, body_id, raw in generator(data):
        split = body._skeleton(raw)
        if split is not None:
            yield start, stop, body_id, raw, split[0], split[1]


def _select(data: bytes, mode: str):
    grouped: dict[tuple, list] = defaultdict(list)
    order: list[tuple] = []
    for start, stop, body_id, raw, skeleton, holes in _candidates(data, mode):
        if skeleton not in grouped:
            order.append(skeleton)
        grouped[skeleton].append((start, stop, body_id, raw, holes))
    families, selected = [], {}
    for skeleton in order:
        members = grouped[skeleton]
        if len(members) < 3 or len({item[2] for item in members}) < 2 or len({item[3] for item in members}) < 2:
            continue
        family_id = len(families)
        families.append((skeleton, members))
        for start, _stop, _body_id, _raw, holes in members:
            if start in selected:
                raise AssertionError("overlapping body-unit candidates")
            selected[start] = (family_id, holes)
    return families, selected


def _descriptor(data: bytes, families: list[tuple], selected: dict[int, tuple[int, tuple[bytes, ...]]]):
    members = [(start, stop, family, holes)
               for family, (_skeleton, group) in enumerate(families)
               for start, stop, _body_id, _raw, holes in group]
    members.sort()
    output = bytearray(); cursor = literal_bytes = hole_bytes = 0
    for start, stop, family, holes in members:
        if start < cursor:
            raise AssertionError("overlapping selected body-unit descriptors")
        literal = data[cursor:start]
        if literal:
            output.append(0); output.extend(_pack(literal)); literal_bytes += len(literal)
        output.append(1); output.extend(vencode(family)); output.extend(vencode(len(holes)))
        for hole in holes:
            output.extend(_pack(hole)); hole_bytes += len(hole)
        cursor = stop
    literal = data[cursor:]
    if literal:
        output.append(0); output.extend(_pack(literal)); literal_bytes += len(literal)
    return bytes(output), literal_bytes, hole_bytes


def encode(data: bytes, mode: str) -> tuple[bytes, dict[str, int | str]]:
    """Return an exact frame and complete pre-backend physical accounting."""
    if mode not in MODES:
        raise ValueError("unsupported body-unit mode")
    if len(data) > MAX_SOURCE:
        raise ValueError("body-unit source exceeds 64 MiB bound")
    families, selected = _select(data, mode)
    dictionary = body._serialize_dictionary(families)
    descriptor, literal_bytes, hole_bytes = _descriptor(data, families, selected)
    rules = RULES[mode]
    frame = MAGIC + bytes((MODES[mode],)) + vencode(len(data)) + _pack(rules) + _pack(dictionary) + _pack(descriptor)
    framing = len(MAGIC) + 1 + len(vencode(len(data)))
    source_bytes = sum(stop - start for _skeleton, group in families for start, stop, _body, _raw, _holes in group)
    accounting: dict[str, int | str] = {
        "mode": mode, "physical_bytes": len(frame), "rules_bytes": len(_pack(rules)),
        "dictionary_bytes": len(_pack(dictionary)), "descriptor_bytes": len(_pack(descriptor)),
        "framing_bytes": framing, "selected_family_count": len(families),
        "selected_member_count": sum(len(group) for _skeleton, group in families),
        "selected_source_bytes": source_bytes, "literal_payload_bytes": literal_bytes,
        "hole_payload_bytes": hole_bytes,
    }
    if sum(int(accounting[key]) for key in ("rules_bytes", "dictionary_bytes", "descriptor_bytes", "framing_bytes")) != len(frame):
        raise AssertionError("body-unit physical accounting mismatch")
    return frame, accounting


def decode(frame: bytes) -> bytes:
    """Decode solely from ``frame`` and reject invalid rules, bounds, or holes."""
    if len(frame) > MAX_FRAME or not frame.startswith(MAGIC) or len(frame) <= len(MAGIC):
        raise ValueError("invalid body-unit frame magic/version")
    mode_code = frame[len(MAGIC)]
    if mode_code not in MODE_NAMES:
        raise ValueError("unsupported body-unit mode")
    mode = MODE_NAMES[mode_code]
    original, position = vdecode(frame, len(MAGIC) + 1)
    if original > MAX_SOURCE:
        raise ValueError("body-unit restored size exceeds bound")
    rules, position = _read(frame, position)
    if rules != RULES[mode]:
        raise ValueError("unsupported body-unit rule set")
    dictionary_blob, position = _read(frame, position)
    descriptor, position = _read(frame, position)
    if position != len(frame):
        raise ValueError("trailing body-unit frame bytes")
    families = body._deserialize_dictionary(dictionary_blob)
    output = bytearray(); position = 0
    while position < len(descriptor):
        token = descriptor[position]; position += 1
        if token == 0:
            literal, position = _read(descriptor, position)
            output.extend(literal)
        elif token == 1:
            family, position = vdecode(descriptor, position)
            count, position = vdecode(descriptor, position)
            if family >= len(families):
                raise ValueError("unknown body-unit family")
            skeleton = families[family]
            expected = sum(kind != body.LITERAL for kind, _literal in skeleton)
            if count != expected:
                raise ValueError("body-unit hole count mismatch")
            holes = []
            for _ in range(count):
                hole, position = _read(descriptor, position)
                holes.append(hole)
            hole_at = 0
            for kind, literal in skeleton:
                if kind == body.LITERAL:
                    output.extend(literal)
                else:
                    hole = holes[hole_at]; hole_at += 1
                    if body._kind(hole) != kind:
                        raise ValueError("body-unit hole rule mismatch")
                    output.extend(hole)
        else:
            raise ValueError("invalid body-unit descriptor token")
        if len(output) > original:
            raise ValueError("body-unit restored length exceeds declared size")
    if len(output) != original:
        raise ValueError("body-unit restored length mismatch")
    return bytes(output)
