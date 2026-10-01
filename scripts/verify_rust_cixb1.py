#!/usr/bin/env python3
"""Cross-check bounded CIXB1 direct-backend envelopes; fixtures are not data comparisons."""
from __future__ import annotations
import hashlib, os, random, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BIN=Path(os.environ.get("CIX_NATIVE_BIN",ROOT/"rust/cix-native/target/release"))
sys.path.insert(0,str(ROOT))

def run(*args,input=None,ok=True):
    p=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if ok and p.returncode: raise AssertionError(f"{args}: {p.stderr.decode(errors='replace')}")
    if not ok and not p.returncode: raise AssertionError(f"unexpected success: {args}")
    return p

def wrap(backend:int,profile:int,data:bytes,payload:bytes)->bytes:
    return struct.pack("<5sBBII32s",b"CIXB1",backend,profile,len(data),len(payload),hashlib.sha256(data).digest())+payload

def main():
    subprocess.run(["cargo","build","--release","--manifest-path",str(ROOT/"rust/cix-native/Cargo.toml")],check=True)
    from cix.backend_portfolio import encode_external_bytes,decode_external_bytes
    data=(b"CIXB1\0external codec fixture\n"*1800)+random.Random(78013).randbytes(4096)
    cases={"gzip":("fast","current","size"),"bzip2":("current","size"),"xz":("current","size"),"zstd":("fast","current","size"),"brotli":("fast",)}
    profile_id={"fast":1,"current":2,"size":3}; backend_id={"gzip":1,"bzip2":2,"xz":3,"zstd":4,"brotli":5}
    rows=[]
    with tempfile.TemporaryDirectory(prefix="cix-cixb1-verify-") as td:
        d=Path(td);source=d/"fixture.bin";source.write_bytes(data)
        for backend,profiles in cases.items():
            for profile in profiles:
                rust=run(str(BIN/"cix"),"--external",backend,"--profile",profile,"-c",str(source)).stdout
                assert rust[:5]==b"CIXB1" and len(rust)>=47
                assert run(str(BIN/"uncix"),"-c","-",input=rust).stdout==data
                if backend in ("gzip","bzip2","xz"):
                    assert decode_external_bytes(rust,{})==data
                elif backend=="zstd":
                    payload=rust[47:]
                    restored=run("zstd","-q","-d","-c",input=payload).stdout
                    assert restored==data
                else:
                    import brotli
                    assert brotli.decompress(rust[47:])==data
                # Construct Python-compatible backend bytes and check Rust decode.
                if backend in ("gzip","bzip2","xz"):
                    py=encode_external_bytes(data,backend,profile,{})
                elif backend=="zstd":
                    src=d/"zsrc";src.write_bytes(data);zout=d/"zsrc.zst"
                    args=["zstd","--single-thread","-q","-f"]
                    args += ["--fast=131072"] if profile=="fast" else ["-3"] if profile=="current" else ["--ultra","-22"]
                    run(*args,str(src),"-o",str(zout));payload=zout.read_bytes();py=wrap(4,profile_id[profile],data,payload)
                else:
                    import brotli
                    payload=brotli.compress(data,quality=0);py=wrap(5,profile_id[profile],data,payload)
                assert run(str(BIN/"uncix"),"-c","-",input=py).stdout==data
                for malformed in (py[:-1],py+b"x",py[:15]+bytes([py[15]^1])+py[16:]):
                    run(str(BIN/"uncix"),"-c","-",input=malformed,ok=False)
                rows.append({"backend":backend,"profile":profile,"rust_encode":True,"python_encode_or_standard_codec_decode":True,"rust_decode":True,"malformed_rejected":True})
    print(f"verified {len(rows)} CIXB1 backend/profile combinations in both decode directions")

if __name__=="__main__":main()
