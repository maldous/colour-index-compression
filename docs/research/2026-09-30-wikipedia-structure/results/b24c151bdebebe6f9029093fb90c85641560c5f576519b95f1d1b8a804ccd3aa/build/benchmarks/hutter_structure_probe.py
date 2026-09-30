#!/usr/bin/env python3
"""Self-contained PAQ v216 structure screen; mode 0 is the raw control."""
from __future__ import annotations
import argparse, hashlib, json, struct, subprocess
from pathlib import Path

MAGIC = b"CIXSTR1\0"
HEADER = struct.Struct(">8sBQQI")

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def paq(binary: Path, args: list[str]) -> None:
    subprocess.run([str(binary), *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def encode(source: Path, archive: Path, binary: Path, expected: str) -> dict:
    if digest(binary) != expected: raise ValueError("pinned PAQ binary hash mismatch")
    raw = source.read_bytes(); temporary = archive.with_suffix(".paq")
    paq(binary, ["-4", "-simd", "AVX2", str(source), str(temporary)])
    payload = temporary.read_bytes(); temporary.unlink()
    if not payload.startswith(b"paq8px"): raise ValueError("invalid PAQ output")
    metadata = json.dumps({"mode":"original","transform_metadata_bytes":0}, sort_keys=True).encode()
    archive.write_bytes(HEADER.pack(MAGIC, 0, len(raw), len(raw), len(metadata)) + metadata + payload)
    return {"original_bytes":len(raw),"transformed_bytes":len(raw),"metadata_bytes":len(metadata),"paq_payload_bytes":len(payload),"physical_frame_bytes":archive.stat().st_size,"frame_sha256":digest(archive)}

def decode(archive: Path, restored: Path, binary: Path, expected: str) -> None:
    if digest(binary) != expected: raise ValueError("pinned PAQ binary hash mismatch")
    raw = archive.read_bytes()
    if len(raw) < HEADER.size: raise ValueError("truncated structure frame")
    magic, mode, original, transformed, mbytes = HEADER.unpack_from(raw); pos = HEADER.size + mbytes
    if magic != MAGIC or mode != 0 or original != transformed: raise ValueError("unsupported structure frame")
    if json.loads(raw[HEADER.size:pos]).get("mode") != "original" or raw[pos:pos+6] != b"paq8px": raise ValueError("bad frame")
    temporary = archive.with_suffix(".decode.paq"); temporary.write_bytes(raw[pos:])
    paq(binary, ["-d", "-simd", "AVX2", str(temporary), str(restored)]); temporary.unlink()
    if restored.stat().st_size != original: raise ValueError("decoded length mismatch")

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("operation",choices=("encode","decode")); p.add_argument("input",type=Path); p.add_argument("output",type=Path); p.add_argument("--paq-binary",type=Path,required=True); p.add_argument("--paq-sha256",required=True); a=p.parse_args()
    if a.operation == "encode": print(json.dumps(encode(a.input,a.output,a.paq_binary,a.paq_sha256),sort_keys=True))
    else: decode(a.input,a.output,a.paq_binary,a.paq_sha256)
    return 0
if __name__ == "__main__": raise SystemExit(main())
