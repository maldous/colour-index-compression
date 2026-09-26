#!/usr/bin/env python3
from __future__ import annotations
import random, urllib.request
from pathlib import Path
from cix.bwt import bwt_transform, mtf_encode, _runa_runb_tokens
from cix.substreams import encode_bytes
from cix.ppm import encode_ppm, decode_ppm

def sources():
    rng=random.Random(20260927);n=16384
    structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(1000))[:n]
    repeat=(b"generic-bwt-token-sequence|"*1000)[:n]
    random_data=bytes(rng.randrange(256) for _ in range(n))
    p=Path("benchmark-work/bwt-token/alice29.txt");p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",p)
    return {"structured":structured,"repeat":repeat,"random":random_data,"alice32k":p.read_bytes()[:32768]}

def main():
    for name,data in sources().items():
        _,bwt=bwt_transform(data);tokens,_=_runa_runb_tokens(mtf_encode(bwt))
        row={"local":len(encode_bytes(tokens))}
        for order in (1,2,3,4):
            p=encode_ppm(tokens,max_order=order)
            assert decode_ppm(p,source_length=len(tokens))==tokens
            row[f"ppm{order}"]=len(p)
        print(name,"tokens",len(tokens),row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
