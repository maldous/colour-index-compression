#!/usr/bin/env python3
from __future__ import annotations
import random, urllib.request
from pathlib import Path
from cix.ctw import encode_ctw,decode_ctw
from cix.ppm import encode_ppm

def sources():
    rng=random.Random(20260927);n=8192
    random_data=bytes(rng.randrange(256) for _ in range(n))
    biased=bytes(0 if rng.random()<.9 else rng.randrange(1,16) for _ in range(n))
    periodic=bytes(((i%37)*7)&255 for i in range(n))
    repeat=(b"generic-context-tree-sequence|"*500)[:n]
    structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(500))[:n]
    path=Path("benchmark-work/ctw/alice29.txt");path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",path)
    return {"random":random_data,"biased":biased,"periodic":periodic,"repeat":repeat,"structured":structured,"alice16k":path.read_bytes()[:16384]}

def main():
    for name,data in sources().items():
        results={}
        for depth in (8,12,16,20):
            p=encode_ctw(data,depth=depth)
            assert decode_ctw(p,source_length=len(data))==data
            results[f"ctw{depth}"]=len(p)
        results["ppm4"]=len(encode_ppm(data,max_order=4))
        print(name,len(data),results,"winner",min((v,k) for k,v in results.items()),flush=True)
if __name__=="__main__":main()
