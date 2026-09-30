#!/usr/bin/env python3
"""Pinned matched-PAQ wrapper for self-contained paragraph/long-line units."""
from __future__ import annotations
import argparse
import json
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks import hutter_wikipedia_body_units as units
from benchmarks.hutter_structure_probe import digest, paq

MAGIC = b"CIXWUNT1"
HEADER = struct.Struct(">8sBQQI")
MODES = ("original", "paragraph-16384", "line-4096")
METADATA = b'{"format":"body-units","version":1}'


def encode(source, archive, binary, expected, mode):
    if digest(binary) != expected: raise ValueError("pinned PAQ binary mismatch")
    raw = source.read_bytes()
    transformed, accounting = (raw, {"mode": "original", "physical_bytes": len(raw)}) if mode == "original" else units.encode(raw, mode)
    tmp_source = archive.with_suffix(".source.bin"); tmp_archive = archive.with_suffix(".paq")
    tmp_source.write_bytes(transformed)
    paq(binary, ["-4", "-simd", "AVX2", str(tmp_source), str(tmp_archive)])
    payload = tmp_archive.read_bytes()
    if not payload.startswith(b"paq8px"): raise ValueError("invalid PAQ output")
    archive.write_bytes(HEADER.pack(MAGIC, MODES.index(mode), len(raw), len(transformed), len(METADATA)) + METADATA + payload)
    tmp_source.unlink(); tmp_archive.unlink()
    return {"mode": mode, "original_bytes": len(raw), "transformed_bytes": len(transformed),
            "transform_accounting": accounting, "total_bytes": archive.stat().st_size,
            "paq_payload_bytes": len(payload), "metadata_bytes": len(METADATA), "framing_bytes": HEADER.size,
            "archive_sha256": digest(archive)}


def decode(archive, restored, binary, expected):
    if digest(binary) != expected: raise ValueError("pinned PAQ binary mismatch")
    blob = archive.read_bytes()
    if len(blob) < HEADER.size: raise ValueError("truncated unit archive")
    magic, mode, n, transformed, m = HEADER.unpack_from(blob)
    if magic != MAGIC or mode >= len(MODES) or m != len(METADATA) or blob[HEADER.size:HEADER.size+m] != METADATA:
        raise ValueError("invalid unit wrapper")
    tmp = archive.with_suffix(".decode.paq"); tmp.write_bytes(blob[HEADER.size+m:])
    paq(binary, ["-d", "-simd", "AVX2", str(tmp), str(restored)])
    tmp.unlink(); frame = restored.read_bytes()
    if len(frame) != transformed: raise ValueError("transformed size mismatch")
    out = frame if mode == 0 else units.decode(frame)
    if len(out) != n: raise ValueError("restored size mismatch")
    restored.write_bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("encode", "decode")); p.add_argument("input", type=Path); p.add_argument("output", type=Path)
    p.add_argument("--paq-binary", type=Path, required=True); p.add_argument("--paq-sha256", required=True)
    p.add_argument("--mode", choices=MODES, default="paragraph-16384")
    a = p.parse_args()
    if a.operation == "encode": print(json.dumps(encode(a.input, a.output, a.paq_binary, a.paq_sha256, a.mode), sort_keys=True))
    else: decode(a.input, a.output, a.paq_binary, a.paq_sha256)


if __name__ == "__main__": main()
