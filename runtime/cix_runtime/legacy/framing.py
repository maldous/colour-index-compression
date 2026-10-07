"""Small framing primitives shared by extracted legacy codecs."""
from __future__ import annotations

import zlib


def vencode(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative varint")
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7f) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def vdecode(blob: bytes, pos: int = 0) -> tuple[int, int]:
    value = shift = 0
    for _ in range(10):
        if pos >= len(blob):
            raise ValueError("truncated varint")
        byte = blob[pos]
        pos += 1
        value |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7
    raise ValueError("overlong varint")


def checked_frame(magic: bytes, mode: int, data: bytes) -> bytes:
    return magic + bytes([mode]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4, "big")


def parse_checked_frame(frame: bytes, magic: bytes, modes: range, max_output_bytes: int) -> tuple[int, int, int]:
    if len(frame) < len(magic) + 6 or not frame.startswith(magic):
        raise ValueError("invalid legacy frame")
    mode = frame[len(magic)]
    if mode not in modes:
        raise ValueError("invalid legacy mode")
    size, pos = vdecode(frame, len(magic) + 1)
    if size > max_output_bytes:
        raise ValueError("legacy output exceeds limit")
    if pos + 4 > len(frame):
        raise ValueError("truncated legacy checksum")
    return mode, size, int.from_bytes(frame[pos:pos + 4], "big")


def verify(data: bytes, size: int, checksum: int) -> bytes:
    if len(data) != size or zlib.crc32(data) != checksum:
        raise ValueError("legacy source checksum mismatch")
    return data
