#!/usr/bin/env python3
"""Check the explicitly supported legacy CIXM6 modes and CIXF1 footer."""
from __future__ import annotations
import os, random, struct, subprocess, sys, tempfile, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BIN=Path(os.environ.get("CIX_NATIVE_BIN",ROOT/"rust/cix-native/target/release"))
def run(*args,input=None,ok=True):
 p=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if ok and p.returncode: raise AssertionError(f"{args}: {p.stderr.decode(errors='replace')}")
 if not ok and not p.returncode: raise AssertionError(f"unexpected success: {args}")
 return p
def get_modes(blob):
 pos=5
 def varint():
  nonlocal pos
  value=shift=0
  while True:
   b=blob[pos];pos+=1;value|=(b&127)<<shift
   if b<128:return value
   shift+=7
 varint()
 modes=[]
 while pos<len(blob):
  mode=blob[pos];pos+=1
  if mode==255:break
  n=varint();size=varint();modes.append(mode);pos+=size
 return modes

def main():
 subprocess.run(["cargo","build","--release","--manifest-path",str(ROOT/"rust/cix-native/Cargo.toml")],check=True)
 sys.path.insert(0,str(ROOT))
 from cix.multinomial import compress, decompress
 from cix.fileformat import _footer, split_file_wrapper
 from cix.runs import encode_run_block
 from cix.adaptive import encode_adaptive
 from cix.multinomial import vencode
 rng=random.Random(112)
 cases=[b"",b"abc",b"A"*2000,random.Random(112).randbytes(3072),bytes(rng.choices(range(8),weights=[50,20,10,8,5,3,2,1],k=6000))]
 with tempfile.TemporaryDirectory(prefix="cix-m6-encode-") as td:
  d=Path(td)
  for i,data in enumerate(cases):
   src=d/f"src-{i}";src.write_bytes(data)
   rust=run(str(BIN/"cix"),"--format","cixm6","--memory","2MiB","-c",str(src)).stdout
   assert rust.startswith(b"CIXM6") and decompress(rust)==data
   assert run(str(BIN/"uncix"),"-c","-",input=rust).stdout==data
   wrapped_rust=run(str(BIN/"cix"),"--format","cixf1","--memory","2MiB","-c",str(src)).stdout
   stream,name=split_file_wrapper(wrapped_rust)
   assert name==src.name and decompress(stream)==data
   assert run(str(BIN/"uncix"),"-c","-",input=wrapped_rust).stdout==data
   wrapped_path=d/f"wrapped-{i}.cix";wrapped_path.write_bytes(wrapped_rust)
   src.unlink()
   run(str(BIN/"uncix"),str(wrapped_path))
   assert src.read_bytes()==data
 run_data=(b"AAAAABBBCC"*1000)+b"tail"
 run_payload,_=encode_run_block(run_data)
 run_archive=b"CIXM6"+vencode(1<<20)+bytes([12])+vencode(len(run_data))+vencode(len(run_payload))+run_payload+bytes([255])+vencode(len(run_data))+struct.pack("<I",zlib.crc32(run_data))
 assert decompress(run_archive)==run_data
 assert run(str(BIN/"uncix"),"-c","-",input=run_archive).stdout==run_data
 prefix=b"context prefix: "*80
 adaptive_data=(b"context prefix: learned bytes "*90)+bytes(range(128))*4
 adaptive_payload=encode_adaptive(adaptive_data,order=2,bucket_bits=8,prefix_history=prefix)
 adaptive_archive=(b"CIXM6"+vencode(1<<20)+bytes([0])+vencode(len(prefix))+vencode(len(prefix))+prefix+
  bytes([10])+vencode(len(adaptive_data))+vencode(len(adaptive_payload))+adaptive_payload+
  bytes([255])+vencode(len(prefix)+len(adaptive_data))+struct.pack("<I",zlib.crc32(prefix+adaptive_data)))
 assert run(str(BIN/"uncix"),"-c","-",input=adaptive_archive).stdout==prefix+adaptive_data
 repeated=b"same block reference payload"*80
 ref=(b"CIXM6"+vencode(1<<20)+bytes([0])+vencode(len(repeated))+vencode(len(repeated))+repeated+bytes([9])+vencode(len(repeated))+vencode(1)+vencode(1)+bytes([255])+vencode(2*len(repeated))+struct.pack("<I",zlib.crc32(repeated+repeated)))
 assert run(str(BIN/"uncix"),"-c","-",input=ref).stdout==repeated+repeated
 for i,data in enumerate(cases):
  archive=compress(data)
  supported=all(mode in (0,1,9) for mode in get_modes(archive))
  if supported:
   assert run(str(BIN/"uncix"),"-c","-",input=archive).stdout==data
   wrapped=archive+_footer("fixture.bin")
   assert run(str(BIN/"uncix"),"-c","-",input=wrapped).stdout==data
   if data:
    bad=archive[:-1]+bytes([archive[-1]^1])
    run(str(BIN/"uncix"),"-c","-",input=bad,ok=False)
    run(str(BIN/"uncix"),"-c","-",input=archive[:-1],ok=False)
   run(str(BIN/"uncix"),"-c","-",input=wrapped[:-1]+b"X",ok=False)
  else:
   run(str(BIN/"uncix"),"-c","-",input=archive,ok=False)
 unsupported=b"CIXM6"+vencode(1<<20)+bytes([2])+vencode(1)+vencode(0)+bytes([255])+vencode(0)+struct.pack("<I",0)
 run(str(BIN/"uncix"),"-c","-",input=unsupported,ok=False)
 print("verified supported and explicitly rejected Python CIXM6 modes, CIXF1, and block references; verified Rust raw/multinomial encode in Python")
if __name__=="__main__":main()
