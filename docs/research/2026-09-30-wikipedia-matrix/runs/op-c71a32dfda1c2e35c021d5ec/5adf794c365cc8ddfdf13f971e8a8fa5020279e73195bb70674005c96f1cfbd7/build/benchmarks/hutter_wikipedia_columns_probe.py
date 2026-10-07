#!/usr/bin/env python3
"""Pinned PAQ wrapper for self-contained Wikipedia column ablations."""
from __future__ import annotations
import argparse, json, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks import hutter_wikipedia_columns as columns
from benchmarks.hutter_structure_probe import digest, paq

MAGIC=b'CIXWCOL1'
HEADER=struct.Struct('>8sBQQI')
# Constant across all three ablations; detailed diagnostics stay in the receipt.
METADATA=json.dumps({'format':'Wikipedia columns','version':1},sort_keys=True).encode()


def encode(source, archive, binary, expected, mode):
    if digest(binary)!=expected: raise ValueError('pinned PAQ binary mismatch')
    data=source.read_bytes(); transformed,costs=columns.encode(data,mode)
    temporary_source=archive.with_suffix('.source.bin'); temporary_archive=archive.with_suffix('.paq')
    temporary_source.write_bytes(transformed)
    paq(binary,['-4','-simd','AVX2',str(temporary_source),str(temporary_archive)])
    payload=temporary_archive.read_bytes()
    if not payload.startswith(b'paq8px'): raise ValueError('invalid PAQ output')
    archive.write_bytes(HEADER.pack(MAGIC,columns.MODES.index(mode),len(data),len(transformed),len(METADATA))+METADATA+payload)
    temporary_source.unlink(); temporary_archive.unlink()
    return dict(mode=mode, original_bytes=len(data), transformed_bytes=len(transformed), transform_accounting=costs,
                total_bytes=archive.stat().st_size, paq_payload_bytes=len(payload),metadata_bytes=len(METADATA),framing_bytes=HEADER.size,
                archive_sha256=digest(archive))


def decode(archive, restored, binary, expected):
    if digest(binary)!=expected: raise ValueError('pinned PAQ binary mismatch')
    data=archive.read_bytes()
    if len(data)<HEADER.size: raise ValueError('truncated column archive')
    magic,mode,original,transformed,mbytes=HEADER.unpack_from(data)
    if magic!=MAGIC or mode>=len(columns.MODES) or data[HEADER.size:HEADER.size+mbytes]!=METADATA: raise ValueError('invalid column wrapper')
    payload=data[HEADER.size+mbytes:]
    if not payload.startswith(b'paq8px'): raise ValueError('invalid PAQ payload')
    temporary=archive.with_suffix('.decode.paq'); temporary.write_bytes(payload)
    paq(binary,['-d','-simd','AVX2',str(temporary),str(restored)]); temporary.unlink()
    raw=restored.read_bytes()
    if len(raw)!=transformed or raw[len(columns.MAGIC)]!=mode: raise ValueError('transform identity mismatch')
    output=columns.decode(raw)
    if len(output)!=original: raise ValueError('restoration length mismatch')
    restored.write_bytes(output)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('encode','decode'));p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--mode',choices=columns.MODES,default='raw');p.add_argument('--paq-binary',required=True,type=Path);p.add_argument('--paq-sha256',required=True);a=p.parse_args()
    if a.operation=='encode':print(json.dumps(encode(a.input,a.output,a.paq_binary,a.paq_sha256,a.mode),sort_keys=True))
    else:decode(a.input,a.output,a.paq_binary,a.paq_sha256)
    return 0
if __name__=='__main__':raise SystemExit(main())
