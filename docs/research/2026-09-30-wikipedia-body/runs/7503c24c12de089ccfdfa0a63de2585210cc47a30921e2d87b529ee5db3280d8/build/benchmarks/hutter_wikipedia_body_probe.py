#!/usr/bin/env python3
"""Pinned PAQ wrapper for the self-contained Wikipedia body-line transform."""
from __future__ import annotations
import argparse, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks import hutter_wikipedia_body_lines as body
from benchmarks.hutter_structure_probe import digest, paq

MAGIC = b"CIXWBOD1"
HEADER = struct.Struct(">8sBQQI")
METADATA = json.dumps({"format":"Wikipedia body lines","version":1}, sort_keys=True).encode()

def encode(source, archive, binary, expected):
    if digest(binary) != expected: raise ValueError("pinned PAQ binary mismatch")
    data = source.read_bytes(); transformed, stats = body.encode(data)
    temporary_source = archive.with_suffix(".source.bin"); temporary_archive = archive.with_suffix(".paq")
    temporary_source.write_bytes(transformed)
    paq(binary, ["-4", "-simd", "AVX2", str(temporary_source), str(temporary_archive)])
    payload = temporary_archive.read_bytes()
    if not payload.startswith(b"paq8px"): raise ValueError("invalid PAQ output")
    archive.write_bytes(HEADER.pack(MAGIC, 0, len(data), len(transformed), len(METADATA)) + METADATA + payload)
    temporary_source.unlink(); temporary_archive.unlink()
    return dict(original_bytes=len(data), transformed_bytes=len(transformed), transform_accounting=stats,
                total_bytes=archive.stat().st_size, paq_payload_bytes=len(payload), metadata_bytes=len(METADATA),
                framing_bytes=HEADER.size, archive_sha256=digest(archive))

def decode(archive, restored, binary, expected):
    if digest(binary) != expected: raise ValueError("pinned PAQ binary mismatch")
    data = archive.read_bytes()
    if len(data) < HEADER.size: raise ValueError("truncated body archive")
    magic, mode, original, transformed, mbytes = HEADER.unpack_from(data)
    if magic != MAGIC or mode != 0 or data[HEADER.size:HEADER.size+mbytes] != METADATA: raise ValueError("invalid body wrapper")
    payload = data[HEADER.size+mbytes:]
    temporary = archive.with_suffix(".decode.paq"); temporary.write_bytes(payload)
    paq(binary, ["-d", "-simd", "AVX2", str(temporary), str(restored)]); temporary.unlink()
    raw = restored.read_bytes()
    if len(raw) != transformed: raise ValueError("transform length mismatch")
    output = body.decode(raw)
    if len(output) != original: raise ValueError("restoration length mismatch")
    restored.write_bytes(output)

def main():
    p=argparse.ArgumentParser(); p.add_argument("operation",choices=("encode","decode")); p.add_argument("input",type=Path); p.add_argument("output",type=Path); p.add_argument("--paq-binary",type=Path,required=True); p.add_argument("--paq-sha256",required=True); a=p.parse_args()
    if a.operation == "encode": print(json.dumps(encode(a.input,a.output,a.paq_binary,a.paq_sha256),sort_keys=True))
    else: decode(a.input,a.output,a.paq_binary,a.paq_sha256)
    return 0
if __name__ == "__main__": raise SystemExit(main())
