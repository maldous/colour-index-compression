#!/usr/bin/env python3
"""Self-contained PAQ v216 structure screen; mode 0 is the raw control."""
from __future__ import annotations
import argparse, hashlib, json, struct, subprocess, sys
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

def transform(data: bytes, mode: str) -> tuple[bytes, dict]:
    if mode == "original": return data, {"mode":"original", "applied":True}
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if mode == "B":
        from benchmarks import hutter_structure_order
        return hutter_structure_order.encode(data, 1)
    from benchmarks import hutter_structure
    return hutter_structure.encode(data, mode)

def inverse(data: bytes, mode: int, metadata: dict) -> bytes:
    if mode == 0: return data
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if mode == 3:
        from benchmarks import hutter_structure_order
        metadata_mode = metadata.get("mode") if isinstance(metadata, dict) else None
        if metadata_mode not in (0, 1):
            raise ValueError("invalid B transform metadata mode")
        return hutter_structure_order.decode(data, metadata_mode, metadata)
    from benchmarks import hutter_structure
    return hutter_structure.decode(data, mode, metadata)

def encode(source: Path, archive: Path, binary: Path, expected: str, requested_mode: str) -> dict:
    if digest(binary) != expected: raise ValueError("pinned PAQ binary hash mismatch")
    raw = source.read_bytes(); transformed, accounting = transform(raw, requested_mode)
    mode = {"original": 0, "C": 1, "D": 2, "B": 3}[requested_mode]
    temporary_source = archive.with_suffix(".source.bin"); temporary_source.write_bytes(transformed)
    temporary = archive.with_suffix(".paq")
    paq(binary, ["-4", "-simd", "AVX2", str(temporary_source), str(temporary)]); temporary_source.unlink()
    payload = temporary.read_bytes(); temporary.unlink()
    if not payload.startswith(b"paq8px"): raise ValueError("invalid PAQ output")
    metadata = json.dumps(accounting, sort_keys=True).encode()
    archive.write_bytes(HEADER.pack(MAGIC, mode, len(raw), len(transformed), len(metadata)) + metadata + payload)
    return {"requested_mode":requested_mode,"applied_mode":mode,"original_bytes":len(raw),"transformed_bytes":len(transformed),"metadata_bytes":len(metadata),"paq_payload_bytes":len(payload),"physical_frame_bytes":archive.stat().st_size,"frame_sha256":digest(archive)}

def decode(archive: Path, restored: Path, binary: Path, expected: str) -> None:
    if digest(binary) != expected: raise ValueError("pinned PAQ binary hash mismatch")
    raw = archive.read_bytes()
    if len(raw) < HEADER.size: raise ValueError("truncated structure frame")
    magic, mode, original, transformed, mbytes = HEADER.unpack_from(raw); pos = HEADER.size + mbytes
    if magic != MAGIC or mode not in (0,1,2,3) or raw[pos:pos+6] != b"paq8px": raise ValueError("bad frame")
    metadata = json.loads(raw[HEADER.size:pos])
    temporary = archive.with_suffix(".decode.paq"); temporary.write_bytes(raw[pos:])
    paq(binary, ["-d", "-simd", "AVX2", str(temporary), str(restored)]); temporary.unlink()
    decoded = inverse(restored.read_bytes(), mode, metadata); restored.write_bytes(decoded)
    if restored.stat().st_size != original: raise ValueError("decoded length mismatch")

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("operation",choices=("encode","decode")); p.add_argument("input",type=Path); p.add_argument("output",type=Path); p.add_argument("--paq-binary",type=Path,required=True); p.add_argument("--paq-sha256",required=True); p.add_argument("--mode",default="original",choices=("original","B","C","D")); a=p.parse_args()
    if a.operation == "encode": print(json.dumps(encode(a.input,a.output,a.paq_binary,a.paq_sha256,a.mode),sort_keys=True))
    else: decode(a.input,a.output,a.paq_binary,a.paq_sha256)
    return 0
if __name__ == "__main__": raise SystemExit(main())
