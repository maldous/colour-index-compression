#!/usr/bin/env python3
"""Measure redundancy in independent order-1 context type classes via Whittle's formula.

For fixed transition counts F, CIX's independent context-row ordering space has size:
    M(F) = product_i r_i! / product_ij f_ij!

Whittle's exact Markov type class is:
    W_uv(F) = M(F) * H_uv(F)

where H_uv is the appropriate cofactor of I-P. Thus -log2(H) is ordering information
that an exact Markov type-class CIX could remove without changing transition-count
metadata.
"""
from __future__ import annotations
import math, random, urllib.request
from pathlib import Path
import numpy as np

FILES={
"alice29.txt":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
"cp.html":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
"fields.c":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
"grammar.lsp":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
"xargs.1":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}

LN2=math.log(2.0)

def whittle_gain(data:bytes):
    if len(data)<2:return 0.0,0.0,1.0,0
    states=sorted(set(data));index={s:i for i,s in enumerate(states)}
    m=len(states);F=np.zeros((m,m),dtype=np.int64)
    for a,b in zip(data,data[1:]):F[index[a],index[b]]+=1
    rows=F.sum(axis=1)
    log_m=0.0
    for i,row_sum in enumerate(rows):
        r=int(row_sum);log_m+=math.lgamma(r+1)/LN2
        for count in F[i]:
            log_m-=math.lgamma(int(count)+1)/LN2
    if m==1:return log_m,0.0,1.0,m
    A=np.eye(m,dtype=float)
    for i,r in enumerate(rows):
        if r:A[i,:]-=F[i,:]/float(r)
    u=index[data[0]];v=index[data[-1]]
    minor=np.delete(np.delete(A,v,axis=0),u,axis=1)
    sign,logabs=np.linalg.slogdet(minor)
    cofactor_sign=sign*((-1)**(u+v))
    if cofactor_sign<=0:raise RuntimeError("non-positive Whittle cofactor")
    log_h=logabs/LN2
    return log_m,-log_h,math.exp(logabs) if logabs>-700 else 0.0,m

def generated():
    rng=random.Random(20260927);n=32768
    random_data=bytes(rng.randrange(256) for _ in range(n))
    biased=bytes(0 if rng.random()<.92 else rng.randrange(1,16) for _ in range(n))
    markov=bytearray();value=0
    for _ in range(n):
        if rng.random()<.04:value=rng.randrange(64)
        markov.append(value)
    structured=b"".join(
        f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode()
        for i in range(2000)
    )[:n]
    return {"gen-random":random_data,"gen-biased":biased,"gen-markov":bytes(markov),"gen-structured":structured}

def main():
    sources=generated();root=Path("benchmark-work/markov-type");root.mkdir(parents=True,exist_ok=True)
    for name,url in FILES.items():
        p=root/name
        if not p.exists():urllib.request.urlretrieve(url,p)
        sources[name]=p.read_bytes()
    for name,data in sources.items():
        logm,gain,h,states=whittle_gain(data)
        print(
            name,
            "bytes",len(data),
            "states",states,
            "row_order_bits",f"{logm:.2f}",
            "whittle_gain_bits",f"{gain:.2f}",
            "gain_bytes",f"{gain/8:.2f}",
            "gain_bpb",f"{gain/len(data):.6f}",
            "H",f"{h:.6g}",
            flush=True,
        )
if __name__=="__main__":main()
