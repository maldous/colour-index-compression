#!/usr/bin/env python3
"""Probe whether the structural prefilter hides generic high-alphabet context wins."""
from __future__ import annotations
import random
import cix.multinomial as m
from cix.cli import config_for_level

def make_walk(n,seed,step):
    r=random.Random(seed);x=128;out=bytearray()
    choices=tuple(range(-step,step+1))
    for _ in range(n):
        x=(x+r.choice(choices))&255;out.append(x)
    return bytes(out)

def make_affine(n,seed):
    r=random.Random(seed);x=1;out=bytearray()
    for _ in range(n):
        x=(5*x+r.randrange(8))&255;out.append(x)
    return bytes(out)

def enc(data,force):
    old=m._looks_bwt_worthy
    try:
        if force:m._looks_bwt_worthy=lambda _:True
        cfg=config_for_level(6)
        e=m.StreamEncoder(cfg);blob=e.feed(data)+e.finish()
        assert m.decompress(blob)==data
        return len(blob),e.block_descriptions
    finally:m._looks_bwt_worthy=old

def main():
    cases={
      "walk8":make_walk(16384,1,8),
      "walk16":make_walk(16384,2,16),
      "affine":make_affine(16384,3),
      "iid":bytes(random.Random(4).randrange(256) for _ in range(16384)),
    }
    total0=total1=0
    for name,data in cases.items():
        worth=m._looks_bwt_worthy(data)
        a,am=enc(data,False);b,bm=enc(data,True)
        total0+=a;total1+=b
        print(name,"worthy",worth,"baseline",a,am,"forced",b,bm,"delta",b-a,flush=True)
    print("TOTAL",total0,total1,"delta",total1-total0,flush=True)
if __name__=="__main__":main()
