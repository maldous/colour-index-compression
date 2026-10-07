"""Deterministic checks for the CIXH1 mixed-region candidate.

These fixtures establish byte preservation and frame admission.  They do not
assert that a semantic recognizer must win: the complete mixed frame competes
with whole-input candidates on its actual paid size.
"""
from __future__ import annotations

import zlib
import struct

import pytest

from cix_runtime import heterogeneous
from cix_runtime.regions import MAX_GENERIC_REGION, boundaries, regions


def _candidate(data: bytes):
    candidates, diagnostics = heterogeneous.catalog(data)
    assert [candidate.id for candidate in candidates] == ["heterogeneous-cixh1-v1"]
    assert diagnostics
    return candidates[0]


def test_roundtrip_preserves_text_numeric_text_and_lexical_bytes() -> None:
    # The runtime treats lexical numeric spellings as bytes.  This preserves
    # NaN spellings, negative zero, delimiters, and following arbitrary bytes.
    data = (b"before: nan -0.0 +0.00\n" + b"1.25,-2e3,0\n" * 80 +
            b"after:\x00unknown\xfffield\n")
    archive = _candidate(data).encode(data)
    assert heterogeneous.recognizes_magic(archive[:5])
    assert heterogeneous.decode(archive, len(data), heterogeneous.MAX_CIXH_MEMORY) == data


def test_boundaries_cover_late_and_interleaved_regions_without_gaps() -> None:
    data = (b"text-first:" + b"a" * (MAX_GENERIC_REGION + 13) +
            b"\n" + b"-0.0,1.0,2e9\n" * 20 + b"opaque\x00field" +
            b"\n" + b"3,4,5\n" * 40)
    pieces = boundaries(data)
    assert pieces[0][0] == 0
    assert pieces[-1][1] == len(data)
    assert all(left[1] == right[0] for left, right in zip(pieces, pieces[1:]))
    assert all(end - start <= MAX_GENERIC_REGION for start, end in pieces)
    assert _candidate(data).encode(data).startswith(heterogeneous.MAGIC)


def test_unknown_bytes_use_complete_generic_fallback() -> None:
    data = bytes(range(256)) * 5 + b"unrecognised-substream\x00\xff"
    archive = _candidate(data).encode(data)
    assert heterogeneous.decode(archive, len(data), heterogeneous.MAX_CIXH_MEMORY) == data


def test_malformed_archive_is_rejected() -> None:
    data = b"x" * 1024
    archive = _candidate(data).encode(data)
    with pytest.raises(ValueError):
        heterogeneous.decode(archive[:-1], len(data), heterogeneous.MAX_CIXH_MEMORY)
    damaged = bytearray(archive)
    damaged[-1] ^= 1
    with pytest.raises(ValueError):
        heterogeneous.decode(bytes(damaged), len(data), heterogeneous.MAX_CIXH_MEMORY)


def test_mixed_candidate_is_considered_even_when_whole_input_wins() -> None:
    # A one-region repetition has the same zlib payload as whole-input zlib,
    # so CIXH1's paid header makes the whole-input candidate legitimately
    # smaller.  Consideration therefore does not imply a specialist win.
    data = b"whole-file repetition\n" * 2048
    archive = _candidate(data).encode(data)
    assert len(zlib.compress(data, 6)) < len(archive)


def _sdf_member() -> bytes:
    return (b"molecule\nproducer\ncomment\n  1  0  0  0  0  0            999 V2000\n"
            b"    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
            b"M  END\n$$$$\n")


def _dicom_member() -> bytes:
    tag = lambda group, element, value: struct.pack("<HHI", group, element, len(value)) + value
    return (tag(0x28, 0x10, (2).to_bytes(2, "little")) +
            tag(0x28, 0x11, (2).to_bytes(2, "little")) +
            tag(0x28, 0x100, (16).to_bytes(2, "little")) +
            tag(0x7FE0, 0x0010, bytes(range(8))))


def test_late_sdf_and_dicom_spans_remain_unsplit() -> None:
    data = b"unknown-prefix\x00\n" + _sdf_member() + b"interleaved-opaque" + _dicom_member() + b"suffix"
    pieces = regions(data)
    kinds = [item.kind for item in pieces]
    assert "sdf-v2000" in kinds
    assert "dicom-implicit-vr" in kinds
    assert all(item.end - item.start > 0 for item in pieces)
    assert heterogeneous.decode(_candidate(data).encode(data), len(data), heterogeneous.MAX_CIXH_MEMORY) == data


def test_late_wcstools_header_is_its_own_known_span() -> None:
    header = struct.pack("<7i", 0, 0, 1, 0, 1, 1, 28)
    data = b"xxxx" + header + b"\x00" * 28 + b"opaque-tail"
    assert any(item.kind == "wcstools-sao-28" for item in regions(data))


def test_late_elf_segment_extent_is_its_own_known_span() -> None:
    elf = bytearray(124)
    elf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<QQ", elf, 32, 64, 0)
    struct.pack_into("<HHHHH", elf, 52, 64, 56, 1, 64, 0)
    struct.pack_into("<IIQQQQQQ", elf, 64, 1, 0, 120, 0, 0, 4, 4, 0)
    data = b"late:" + bytes(elf) + b":opaque"
    assert any(item.kind == "elf" for item in regions(data))
