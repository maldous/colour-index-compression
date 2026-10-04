#!/usr/bin/env python3
"""Generate a compact source-only ECOFF parity vector for native relations.

This deliberately invokes no compression backend.  It exercises a relocation
in .rdata that points at a transmitted .text symbol, a GP-relative load whose
dynamic-GOT slot maps to that repeated symbol name, and one .pdata address.
The output is a JSON record of exact Python raw-transform bytes for Rust tests.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

from cix_runtime.legacy import (
    ecoff_pdata,
    ecoff_pdata_symbols,
    ecoff_section_pointers,
    ecoff_symbol_loads,
)


def section(name, virtual, size, offset):
    return struct.pack("<8sQQQQQQHHI", name, 0, virtual, size, offset, 0, 0, 0, 0, 0)


def fixture():
    # All offsets are explicit so this remains a small auditable byte layout.
    entries = [
        (b".text\0\0\0", 0x1000, 4, 0x400),
        (b".got\0\0\0\0", 0x2008, 16, 0x408),
        (b".dynamic", 0x3000, 64, 0x418),
        (b".pdata\0\0", 0x4000, 24, 0x458),
        (b".rdata\0\0", 0x5000, 8, 0x470),
        (b".rel.dyn", 0x6000, 16, 0x478),
        (b".dynsym\0", 0x7000, 48, 0x488),
        (b".dynstr\0", 0x7100, 7, 0x4B8),
        (b".hash\0\0\0", 0x7200, 8, 0x4C0),
    ]
    data = bytearray(0x4C8)
    data[:2] = b"\x83\x01"
    struct.pack_into("<H", data, 2, len(entries))
    struct.pack_into("<H", data, 20, 80)
    struct.pack_into("<H", data, 22, 0x2005)
    struct.pack_into("<Q", data, 96, 0x2000)  # GP: the GOT slot is +8.
    for index, values in enumerate(entries):
        data[104 + index * 64 : 104 + (index + 1) * 64] = section(*values)
    # Alpha ldq $29,8($29): low immediate 8 is normalized through the name map.
    struct.pack_into("<I", data, 0x400, (0x29 << 26) | (29 << 16) | 8)
    # Only the second duplicate symbol is dynamically mapped.  Both remain in
    # dynsym, so global frequency ranking sees two occurrences while _maps has
    # one unambiguous displacement for the retained name.
    for row, (tag, value) in enumerate(((0x7000000A, 0), (0x70000013, 1), (0x70000011, 2))):
        struct.pack_into("<IIQ", data, 0x418 + row * 16, tag, 0, value)
    # Three procedure addresses force a real mode-1 delta residual at entry 3.
    for row, word in enumerate((0, 4, 8)):
        struct.pack_into("<I", data, 0x458 + row * 8, word)
    struct.pack_into("<Q", data, 0x470, 0x1000)  # relocated pointer to .text function.
    struct.pack_into("<QII", data, 0x478, 0x5000, 2, 0)  # symbol 0, relocation type 2.
    for row in range(2):
        struct.pack_into("<I", data, 0x488 + row * 24, 1)  # dynstr offset for .text
        struct.pack_into("<Q", data, 0x488 + row * 24 + 8, 0x1000)
    data[0x4B8:0x4BF] = b"\0.text\0"
    struct.pack_into("<II", data, 0x4C0, 1, 2)
    return bytes(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = fixture()
    section_raw, section_stats = ecoff_section_pointers.transform(source, 4)
    load_raw, load_stats = ecoff_symbol_loads.transform(source, 2)
    pdata_raw, pdata_stats = ecoff_pdata.transform(source, 1)
    combined_raw, combined_stats = ecoff_pdata_symbols.transform(source, 1)
    print(json.dumps({"section": section_stats, "symbol_load": load_stats, "pdata": pdata_stats, "pdata_symbols": combined_stats}, sort_keys=True), file=sys.stderr)
    assert section_stats["eligible_pointers"] >= 1 and section_stats["in_candidates"] >= 1
    assert load_stats["eligible_loads"] >= 1 and load_stats["normalized_loads"] >= 1
    assert pdata_stats["tables"] >= 1
    assert struct.unpack_from("<I", pdata_raw, 0x468)[0] == 4
    assert combined_stats["predicted_addresses"] >= 1
    for raw, inverse in ((section_raw, ecoff_section_pointers.inverse), (load_raw, ecoff_symbol_loads.inverse), (pdata_raw, ecoff_pdata.inverse), (combined_raw, ecoff_pdata_symbols.inverse)):
        assert inverse(raw) == source
    ambiguous = bytearray(source)
    # Mapping both duplicate names gives _maps an ambiguous two-slot name. The
    # reference still records the eligible load descriptor, with a clear flag.
    struct.pack_into("<IIQ", ambiguous, 0x418 + 16, 0x70000013, 0, 0)
    ambiguous_raw, ambiguous_stats = ecoff_symbol_loads.transform(bytes(ambiguous), 2)
    assert ambiguous_stats["eligible_loads"] >= 1 and ambiguous_stats["normalized_loads"] == 0
    assert ecoff_symbol_loads.inverse(ambiguous_raw) == bytes(ambiguous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema": "cix.ecoff-relation-fixture.v1",
        "source_hex": source.hex(),
        "section_pointer_mode4_hex": section_raw.hex(),
        "symbol_load_mode2_hex": load_raw.hex(),
        "pdata_mode1_hex": pdata_raw.hex(),
        "pdata_symbols_mode1_hex": combined_raw.hex(),
        "symbol_load_ambiguous_mode2_hex": ambiguous_raw.hex(),
        "event_counts": {
            "section": section_stats,
            "symbol_load": load_stats,
            "pdata": pdata_stats,
            "pdata_symbols": combined_stats,
        },
    }, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
