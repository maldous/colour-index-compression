#!/usr/bin/env python3
"""Physical alternatives for CIX count-vector metadata.

No codec behavior is changed.  We compare the exact current active-set + stars-and-bars
histogram byte cost with reversible generic count-vector representations built from the
existing CIX integer substream coder.
"""
from __future__ import annotations

import math
import random
import urllib.request
from pathlib import Path

from cix.multinomial import vencode
from cix.substreams import encode_uints

URLS = {
    "alice29": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "grammar": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
    "xargs": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}

def counts(data: bytes) -> list[int]:
    out=[0]*256
    for b in data: out[b]+=1
    return out

def fixed_width_bytes(cardinality: int) -> int:
    if cardinality <= 1: return 0
    return ((cardinality-1).bit_length()+7)//8

def current_size(cs:list[int],n:int)->int:
    active=[i for i,c in enumerate(cs) if c]
    m=len(active)
    size=len(vencode(m))
    if n==0:return size
    if m<256:size+=fixed_width_bytes(math.comb(256,m))
    if m>1:size+=fixed_width_bytes(math.comb(n-1,m-1))
    return size

def zigzag(x:int)->int:
    return x*2 if x>=0 else (-x)*2-1

def candidates(cs:list[int],n:int)->dict[str,int]:
    active=[c for c in cs if c]
    m=len(active)
    base=len(vencode(m))
    if m<256:base+=fixed_width_bytes(math.comb(256,m))

    result={"current":current_size(cs,n)}
    if m:
        # active counts are positive; last count is implied by n.
        vals=[c-1 for c in active[:-1]]
        result["active-uint"]=1+base+len(encode_uints(vals))

        prev=0
        deltas=[]
        for c in active[:-1]:
            deltas.append(zigzag(c-prev));prev=c
        result["active-delta"]=1+base+len(encode_uints(deltas))

    # Full fixed alphabet removes active-set metadata. Last count is implied.
    vals=cs[:-1]
    result["dense-uint"]=1+len(encode_uints(vals))
    prev=0; deltas=[]
    for c in vals:
        deltas.append(zigzag(c-prev));prev=c
    result["dense-delta"]=1+len(encode_uints(deltas))
    return result

def generated():
    rng=random.Random(20260928);n=32768
    rand=bytes(rng.randrange(256) for _ in range(n))
    biased=bytes(0 if rng.random()<.92 else rng.randrange(1,16) for _ in range(n))
    balanced=bytes(i&255 for i in range(n))
    periodic=(bytes(range(37))*((n//37)+1))[:n]
    return {"gen-random":rand,"gen-biased":biased,"gen-balanced":balanced,"gen-periodic":periodic}

def sources():
    out=generated();work=Path("benchmark-work/count-vector");work.mkdir(parents=True,exist_ok=True)
    for name,url in URLS.items():
        p=work/name
        if not p.exists():urllib.request.urlretrieve(url,p)
        out["canterbury-"+name]=p.read_bytes()
    return out

def main():
    totals={}
    block_size=8192
    for name,data in sources().items():
        src={}
        choices={}
        for start in range(0,len(data),block_size):
            block=data[start:start+block_size]
            if not block:continue
            c=candidates(counts(block),len(block))
            for k,v in c.items():src[k]=src.get(k,0)+v
            winner=min(c,key=lambda k:(c[k],k))
            choices[winner]=choices.get(winner,0)+1
        incumbent=src["current"]
        # A future portfolio always retains incumbent. Candidate carries its own mode byte.
        best=sum([]) if False else None
        print(name,"totals",src,"block_winners",choices,flush=True)
        for k,v in src.items():totals[k]=totals.get(k,0)+v
    print("SUMMARY",totals,
          "best_alternative",min((v,k) for k,v in totals.items() if k!="current"),
          "current",totals["current"],flush=True)

if __name__=="__main__":
    main()
