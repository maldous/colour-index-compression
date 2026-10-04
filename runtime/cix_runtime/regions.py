"""Bounded, input-derived structure spans for CIXH1."""
from __future__ import annotations

import struct
from dataclasses import dataclass

MAX_GENERIC_REGION = 64 * 1024
MAX_STRUCTURED_REGIONS = 256
MAX_DICOM_HEADER = 1 << 20
MAX_SDF_RECORD = 16 << 20
MAX_ELF_TABLE = 16 << 20


@dataclass(frozen=True)
class Region:
    start: int
    end: int
    kind: str = "generic"


def _sdf_candidate(data: bytes, marker: int) -> Region | None:
    """Validate the bounded member containing one V2000 marker."""
    line_end = data.find(b"\n", marker)
    if line_end < 0 or line_end - marker > 256: return None
    starts, probe = [], marker
    for _ in range(4):
        previous = data.rfind(b"\n", 0, probe)
        if previous < 0: return None
        starts.append(previous + 1); probe = previous
    start = starts[-1]
    separator = data.find(b"$$$$\n", line_end + 1, min(len(data), start + MAX_SDF_RECORD))
    if separator < 0: return None
    lines = data[start:separator].splitlines(keepends=True)
    try:
        counts = lines[3]; atoms, bonds = int(counts[:3]), int(counts[3:6])
        valid = counts.rstrip().endswith(b"V2000") and 0 < atoms <= 999 and 0 <= bonds <= 999
        valid = valid and len(lines) >= 5 + atoms + bonds and lines[4 + atoms + bonds].startswith(b"M  ")
    except (IndexError, ValueError): return None
    return Region(start, separator + 5, "sdf-v2000") if valid else None


def _group_adjacent(records: list[Region]) -> list[Region]:
    grouped: list[Region] = []
    for item in records:
        if grouped and grouped[-1].end == item.start: grouped[-1] = Region(grouped[-1].start, item.end, item.kind)
        else: grouped.append(item)
    return grouped


def _sdf_spans(data: bytes) -> list[Region]:
    """Find contiguous canonical V2000 members, including late members."""
    records: list[Region] = []
    anchor = 0
    while len(records) < MAX_STRUCTURED_REGIONS:
        marker = data.find(b"V2000", anchor)
        if marker < 0:
            break
        item = _sdf_candidate(data, marker)
        if item is None: anchor = marker + 5
        else: records.append(item); anchor = item.end
    return _group_adjacent(records)


def _wcstools_spans(data: bytes) -> list[Region]:
    spans: list[Region] = []
    for offset in range(0, max(0, len(data) - 27), 4):
        try:
            _, _, count, stnum, mprop, nmag, width = struct.unpack_from("<7i", data, offset)
        except struct.error:
            break
        records = abs(count)
        end = offset + 28 + 28 * records
        if (0 < records <= 8_000_000 and stnum == 0 and mprop == 1 and
                abs(nmag) == 1 and width == 28 and end <= len(data)):
            spans.append(Region(offset, end, "wcstools-sao-28"))
            if len(spans) >= MAX_STRUCTURED_REGIONS:
                break
    return spans


def _dicom_dimensions(group: int, element: int, size: int, value: bytes,
                      rows: int, cols: int, bits: int) -> tuple[int, int, int]:
    if group != 0x28 or size != 2: return rows, cols, bits
    decoded = int.from_bytes(value, "little")
    if element == 0x10: return decoded, cols, bits
    if element == 0x11: return rows, decoded, bits
    if element == 0x100: return rows, cols, decoded
    return rows, cols, bits


def _dicom_pixel_region(start: int, end: int, size: int, rows: int, cols: int,
                        bits: int) -> Region | None:
    if bits != 16 or not rows or not cols or size % (rows * cols * 2): return None
    return Region(start, end, "dicom-implicit-vr")


def _dicom_candidate(data: bytes, start: int) -> Region | None:
    """Validate one rows-tag anchored implicit-VR sequence."""
    pos, limit, rows, cols, bits = start, min(len(data), start + MAX_DICOM_HEADER), 0, 0, 0
    try:
        while pos + 8 <= limit:
            group, element, size = struct.unpack_from("<HHI", data, pos)
            value_start, value_end = pos + 8, pos + 8 + size
            if size == 0xFFFFFFFF or value_end > len(data) or value_end > limit: return None
            rows, cols, bits = _dicom_dimensions(group, element, size, data[value_start:value_end], rows, cols, bits)
            if (group, element) == (0x7FE0, 0x0010):
                return _dicom_pixel_region(start, value_end, size, rows, cols, bits)
            pos = value_end
    except (OverflowError, struct.error): return None
    return None


def _dicom_spans(data: bytes) -> list[Region]:
    """Find implicit-VR pixels from a supported tag sequence."""
    spans: list[Region] = []
    needle, search = b"\x28\x00\x10\x00", 0
    while len(spans) < MAX_STRUCTURED_REGIONS:
        start = data.find(needle, search)
        if start < 0: break
        search = start + 1
        item = _dicom_candidate(data, start)
        if item is not None: spans.append(item)
    return spans


def _elf_header(data: bytes, offset: int) -> tuple[int, str, int, int, int, int, int, int, int] | None:
    """Return validated class, layout, and table fields for one ELF header."""
    if offset + 64 > len(data) or data[offset:offset + 4] != b"\x7fELF": return None
    kind, endian = data[offset + 4], data[offset + 5]
    if kind not in (1, 2) or endian not in (1, 2) or data[offset + 6] != 1: return None
    order = "<" if endian == 1 else ">"
    try:
        if kind == 1:
            phoff, shoff = struct.unpack_from(order + "II", data, offset + 28)
            ehsize, phentsize, phnum, shentsize, shnum = struct.unpack_from(order + "HHHHH", data, offset + 40)
        else:
            phoff, shoff = struct.unpack_from(order + "QQ", data, offset + 32)
            ehsize, phentsize, phnum, shentsize, shnum = struct.unpack_from(order + "HHHHH", data, offset + 52)
    except struct.error: return None
    if ehsize < (52 if kind == 1 else 64) or phentsize == 0 or shentsize == 0: return None
    return kind, order, phoff, shoff, phentsize, phnum, shentsize, shnum, ehsize


def _elf_load_extent(data: bytes, offset: int, kind: int, order: str,
                     phoff: int, phentsize: int, phnum: int, extent: int) -> int | None:
    """Extend table coverage through validated PT_LOAD file extents."""
    try:
        for index in range(phnum):
            entry = offset + phoff + index * phentsize
            fields = struct.unpack_from(order + ("IIIII" if kind == 1 else "IIQQQQ"), data, entry)
            if fields[0] == 1: extent = max(extent, fields[1] + fields[4] if kind == 1 else fields[2] + fields[5])
    except struct.error: return None
    return extent


def _elf_span(data: bytes, offset: int) -> Region | None:
    header = _elf_header(data, offset)
    if header is None: return None
    kind, order, phoff, shoff, phentsize, phnum, shentsize, shnum, ehsize = header
    tables_end = max(ehsize, phoff + phentsize * phnum, shoff + shentsize * shnum)
    if tables_end > MAX_ELF_TABLE or offset + tables_end > len(data): return None
    extent = _elf_load_extent(data, offset, kind, order, phoff, phentsize, phnum, tables_end)
    if extent is None: return None
    if extent <= 0 or offset + extent > len(data):
        return None
    return Region(offset, offset + extent, "elf")


def _elf_spans(data: bytes) -> list[Region]:
    spans: list[Region] = []
    offset = 0
    while len(spans) < MAX_STRUCTURED_REGIONS:
        offset = data.find(b"\x7fELF", offset)
        if offset < 0:
            break
        item = _elf_span(data, offset)
        if item is None:
            offset += 4
        else:
            spans.append(item)
            offset = item.end
    return spans


def structured_regions(data: bytes) -> list[Region]:
    """Return non-overlapping known spans, preferring the earliest full span."""
    proposed = _sdf_spans(data) + _wcstools_spans(data) + _dicom_spans(data) + _elf_spans(data)
    proposed.sort(key=lambda item: (item.start, -(item.end - item.start), item.kind))
    accepted: list[Region] = []
    for item in proposed:
        if not accepted or item.start >= accepted[-1].end:
            accepted.append(item)
        if len(accepted) >= MAX_STRUCTURED_REGIONS:
            break
    return accepted


def regions(data: bytes) -> list[Region]:
    """Partition every byte; only unknown gaps receive fixed-size cuts."""
    result: list[Region] = []
    position = 0
    for known in structured_regions(data):
        while known.start - position > MAX_GENERIC_REGION:
            result.append(Region(position, position + MAX_GENERIC_REGION))
            position += MAX_GENERIC_REGION
        if known.start > position:
            result.append(Region(position, known.start))
        result.append(known)
        position = known.end
    while len(data) - position > MAX_GENERIC_REGION:
        result.append(Region(position, position + MAX_GENERIC_REGION))
        position += MAX_GENERIC_REGION
    if position < len(data):
        result.append(Region(position, len(data)))
    assert not result or (result[0].start == 0 and result[-1].end == len(data))
    assert all(left.end == right.start for left, right in zip(result, result[1:]))
    return result


def boundaries(data: bytes) -> list[tuple[int, int]]:
    return [(item.start, item.end) for item in regions(data)]
