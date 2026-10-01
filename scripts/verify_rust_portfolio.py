#!/usr/bin/env python3
"""Correctness-only cross-decoding for bounded native portfolio selection."""
from __future__ import annotations
import hashlib, os, random, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BIN=Path(os.environ.get("CIX_NATIVE_BIN",ROOT/"rust/cix-native/target/release"))
sys.path.insert(0,str(ROOT))
def run(*args,input=None,ok=True):
    p=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if ok and p.returncode: raise AssertionError(f"{args}: {p.stderr.decode(errors='replace')}")
    if not ok and not p.returncode: raise AssertionError(f"unexpected success: {args}")
    return p
def main():
    subprocess.run(["cargo","build","--release","--manifest-path",str(ROOT/"rust/cix-native/Cargo.toml")],check=True)
    from cix.pipeline import decode_file
    data=(b"bounded native portfolio fixture\0"*200)+random.Random(1917).randbytes(4096)
    with tempfile.TemporaryDirectory(prefix="cix-portfolio-verify-") as td:
        d=Path(td); src=d/"input.bin";src.write_bytes(data)
        for profile,mem in (("fast","128MiB"),("current","128MiB"),("size","384MiB")):
            archive=run(str(BIN/"cix"),"--portfolio",profile,"--memory",mem,"-c",str(src)).stdout
            assert archive[:5] in (b"CIXG1",b"CIXB1")
            restored=run(str(BIN/"uncix"),"-c","-",input=archive).stdout
            assert restored==data
            ap=d/f"{profile}.cix";rp=d/f"{profile}.restored";ap.write_bytes(archive)
            if archive[:5]==b"CIXG1":
                decode_file(ap,rp)
            else:
                import bz2, gzip, lzma, struct
                backend=archive[5]; payload=archive[47:]
                if backend==1: restored_py=gzip.decompress(payload)
                elif backend==2: restored_py=bz2.decompress(payload)
                elif backend==3: restored_py=lzma.decompress(payload)
                elif backend==4: restored_py=run("zstd","-q","-d","-c",input=payload).stdout
                elif backend==5:
                    import brotli
                    restored_py=brotli.decompress(payload)
                else: raise AssertionError("unknown CIXB1 backend ID")
                rp.write_bytes(restored_py)
                assert len(restored_py)==struct.unpack_from("<I",archive,7)[0]
                assert hashlib.sha256(restored_py).digest()==archive[15:47]
            assert hashlib.sha256(rp.read_bytes()).digest()==hashlib.sha256(data).digest()
        run(str(BIN/"cix"),"--portfolio","size","--memory","128MiB","-c",str(src),ok=False)
        run(str(BIN/"cix"),"--portfolio","fast","--stream","-c",str(src),ok=False)
    print("verified fast/current/size portfolio round trips with Rust and Python decoders; malformed option combinations rejected")
if __name__=="__main__": main()
