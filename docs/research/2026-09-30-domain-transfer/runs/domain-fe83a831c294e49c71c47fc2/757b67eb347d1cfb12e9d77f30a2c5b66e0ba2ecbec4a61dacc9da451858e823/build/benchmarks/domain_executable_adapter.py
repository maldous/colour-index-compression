"""Reversible ELF64 little-endian relative-relocation address adapter.

This is an explicitly narrow ELF/x86-64 experiment, not an ISA-independent
executable compressor.  It derives every candidate section from the submitted
ELF bytes, normalizes qualifying R_X86_64_RELATIVE addends to section-relative
offsets, and transmits every membership bit and section index in the frame.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from cix.multinomial import vencode, vdecode

MAGIC = b"CIXELF1"
RAW, ADDRESS, ADDRESS_PACKED = 0, 1, 2
ELF64, LITTLE_ENDIAN, X86_64 = 2, 1, 62
SHT_RELA, R_X86_64_RELATIVE = 4, 8


@dataclass(frozen=True)
class Section:
    index: int
    kind: int
    address: int
    offset: int
    size: int
    entsize: int


@dataclass(frozen=True)
class Relative:
    addend_offset: int
    addend: int


def _pack(blob: bytes) -> bytes:
    return vencode(len(blob)) + blob


def _read(blob: bytes, position: int) -> tuple[bytes, int]:
    size, position = vdecode(blob, position)
    if position + size > len(blob):
        raise ValueError("truncated ELF adapter field")
    return blob[position:position + size], position + size


def _elf(data: bytes) -> tuple[list[Section], list[Relative]]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError("ELF magic required")
    if data[4] != ELF64 or data[5] != LITTLE_ENDIAN:
        raise ValueError("only ELF64 little-endian is supported")
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != X86_64:
        raise ValueError("only x86-64 ELF is supported")
    shoff = struct.unpack_from("<Q", data, 40)[0]
    shentsize, shnum = struct.unpack_from("<HH", data, 58)
    if shentsize != 64 or shnum == 0 or shoff + shentsize * shnum > len(data):
        raise ValueError("invalid ELF section table")
    sections = []
    for index in range(shnum):
        at = shoff + index * shentsize
        kind = struct.unpack_from("<I", data, at + 4)[0]
        address, offset, size = struct.unpack_from("<QQQ", data, at + 16)
        entsize = struct.unpack_from("<Q", data, at + 56)[0]
        if kind != 8 and offset + size > len(data):
            raise ValueError("section outside ELF")
        sections.append(Section(index, kind, address, offset, size, entsize))
    relatives = []
    for section in sections:
        if section.kind != SHT_RELA:
            continue
        entsize = section.entsize or 24
        if entsize != 24 or section.size % entsize:
            raise ValueError("invalid ELF64 RELA section")
        for at in range(section.offset, section.offset + section.size, entsize):
            info = struct.unpack_from("<Q", data, at + 8)[0]
            if (info & 0xffffffff) == R_X86_64_RELATIVE:
                relatives.append(Relative(at + 16, struct.unpack_from("<q", data, at + 16)[0]))
    return sections, relatives


def _section_for(sections: list[Section], address: int) -> Section | None:
    candidates = [section for section in sections
                  if section.address and section.size and section.address <= address < section.address + section.size]
    return min(candidates, key=lambda section: (section.size, section.index)) if candidates else None


def _metadata(relatives: list[Relative], sections: list[Section], variant: int) -> tuple[bytes, dict]:
    flags = bytearray((len(relatives) + 7) // 8)
    identifiers = []
    candidates = 0
    for event, relative in enumerate(relatives):
        section = _section_for(sections, relative.addend)
        if variant in (ADDRESS, ADDRESS_PACKED) and section is not None:
            flags[event // 8] |= 1 << (event % 8)
            identifiers.append(section.index)
            candidates += 1
    if variant == ADDRESS:
        packed = b"".join(vencode(identifier) for identifier in identifiers)
        encoding = "individual unsigned varints"
    elif variant == ADDRESS_PACKED:
        cardinality = len(sections) ** len(identifiers)
        width = ((cardinality - 1).bit_length() + 7) // 8
        rank = 0
        for identifier in identifiers:
            rank = rank * len(sections) + identifier
        packed = rank.to_bytes(width, "big")
        encoding = "exact mixed-radix rank, base section-header count"
    else:
        packed = b""; encoding = "none"
    meta = vencode(len(relatives)) + _pack(bytes(flags)) + packed
    return meta, dict(relative_relocations=len(relatives), normalized_addends=candidates,
                      membership_bytes=len(flags), section_index_bytes=len(packed),
                      section_index_encoding=encoding, metadata_bytes=len(meta))


def inspect(data: bytes) -> dict:
    sections, relatives = _elf(data)
    eligible = [(relative, _section_for(sections, relative.addend)) for relative in relatives]
    normalized = [pair for pair in eligible if pair[1] is not None]
    return dict(format="ELF64-little-endian-x86-64", bytes=len(data), section_headers=len(sections),
                rela_sections=sum(section.kind == SHT_RELA for section in sections),
                relative_relocations=len(relatives), normalized_addends=len(normalized),
                unmapped_relative_addends=len(relatives) - len(normalized),
                unique_target_sections=len({section.index for _, section in normalized}),
                relation="R_X86_64_RELATIVE addend lies in a parsed ELF section; normalized value is addend-section.address",
                packing="one membership bit per relative relocation plus one transmitted section index per normalized addend",
                restrictions=["No instruction decoding", "No symbol-name model", "No external linker state",
                              "ELF64 little-endian x86-64 only"])


def encode(data: bytes, variant: str = "address") -> bytes:
    if variant not in ("raw", "address", "address-packed"):
        raise ValueError("variant must be raw, address or address-packed")
    sections, relatives = _elf(data)
    selector = {"raw": RAW, "address": ADDRESS, "address-packed": ADDRESS_PACKED}[variant]
    payload = bytearray(data)
    metadata, _stats = _metadata(relatives, sections, selector)
    if selector in (ADDRESS, ADDRESS_PACKED):
        for relative in relatives:
            section = _section_for(sections, relative.addend)
            if section is not None:
                struct.pack_into("<Q", payload, relative.addend_offset, relative.addend - section.address)
    frame = MAGIC + bytes([selector]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4, "big") + _pack(bytes(payload)) + _pack(metadata)
    return frame


def decode(frame: bytes) -> bytes:
    if not frame.startswith(MAGIC) or len(frame) <= len(MAGIC):
        raise ValueError("invalid ELF adapter frame")
    selector = frame[len(MAGIC)]
    if selector not in (RAW, ADDRESS, ADDRESS_PACKED):
        raise ValueError("invalid ELF adapter variant")
    original, position = vdecode(frame, len(MAGIC) + 1)
    crc = int.from_bytes(frame[position:position + 4], "big"); position += 4
    payload, position = _read(frame, position)
    metadata, position = _read(frame, position)
    if position != len(frame) or len(payload) != original:
        raise ValueError("invalid ELF adapter lengths")
    sections, relatives = _elf(payload)
    count, meta_position = vdecode(metadata, 0)
    flags, meta_position = _read(metadata, meta_position)
    if count != len(relatives) or len(flags) != (count + 7) // 8:
        raise ValueError("ELF adapter relocation metadata mismatch")
    marked = [event for event in range(len(relatives)) if flags[event // 8] & (1 << (event % 8))]
    if selector == ADDRESS:
        identifiers = []
        for _ in marked:
            identifier, meta_position = vdecode(metadata, meta_position)
            identifiers.append(identifier)
    elif selector == ADDRESS_PACKED:
        width = (((len(sections) ** len(marked)) - 1).bit_length() + 7) // 8
        if len(metadata) - meta_position != width:
            raise ValueError("ELF adapter packed section rank length mismatch")
        rank = int.from_bytes(metadata[meta_position:], "big"); meta_position += width
        identifiers = [0] * len(marked)
        for event in range(len(marked) - 1, -1, -1):
            rank, identifiers[event] = divmod(rank, len(sections))
        if rank:
            raise ValueError("ELF adapter packed section rank outside radix")
    else:
        identifiers = []
    restored = bytearray(payload)
    identifier_at = 0
    for event, relative in enumerate(relatives):
        marked = bool(flags[event // 8] & (1 << (event % 8)))
        if selector == RAW and marked:
            raise ValueError("raw variant contains normalized relocation")
        if not marked:
            continue
        index = identifiers[identifier_at]; identifier_at += 1
        if index >= len(sections):
            raise ValueError("ELF adapter section index outside table")
        section = sections[index]
        offset = struct.unpack_from("<Q", payload, relative.addend_offset)[0]
        if not section.address or offset >= section.size:
            raise ValueError("ELF adapter normalized offset outside section")
        struct.pack_into("<Q", restored, relative.addend_offset, section.address + offset)
    if meta_position != len(metadata):
        raise ValueError("trailing ELF adapter metadata")
    data = bytes(restored)
    if len(data) != original or zlib.crc32(data) != crc:
        raise ValueError("ELF adapter checksum mismatch")
    return data
