#!/usr/bin/env python3
from __future__ import annotations
import random, urllib.request
from pathlib import Path
from cix.ppm import encode_ppm, decode_ppm

def sources():
    rng=random.Random(20260927)
    n=16384
    structured=b"".join(
        f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}|{i%2}\n".encode()
        for i in range(1000)
    )[:n]
    periodic=bytes(((i%53)*7)&255 for i in range(n))
    repeat=(b"generic-repeat-model-sequence|"*1000)[:n]
    markov=bytearray();v=0
    for _ in range(n):
        if rng.random()<.03:v=rng.randrange(256)
        markov.append(v)
    path=Path("benchmark-work/ppm/alice29.txt");path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",path)
    alice=path.read_bytes()[:65536]
    return {"structured":structured,"periodic":periodic,"repeat":repeat,"markov":bytes(markov),"alice64k":alice}

def main():
    for name,data in sources().items():
        row={}
        for order in range(1,9):
            p=encode_ppm(data,max_order=order)
            assert decode_ppm(p,source_length=len(data))==data
            row[order]=len(p)
        print(name,len(data),row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
