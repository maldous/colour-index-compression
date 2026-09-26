#!/usr/bin/env python3
from __future__ import annotations
import random,struct,urllib.request
from pathlib import Path
from cix.bwt import bwt_transform,bwt_inverse,mtf_encode,mtf_decode,encode_bwt_block
from cix.substreams import encode_bytes,decode_bytes,BitWriter,BitReader
from cix.multinomial import vencode,vdecode

def rle2_tokens(mtf:bytes):
    tokens=bytearray();side=[];i=0
    while i<len(mtf):
        if mtf[i]==0:
            j=i+1
            while j<len(mtf) and mtf[j]==0:j+=1
            z=j-i-1
            while True:
                tokens.append(0 if (z&1)==0 else 1)
                if z<2:break
                z=(z-2)//2
            i=j
        else:
            r=mtf[i]
            if r<=253:tokens.append(r+1)
            else:
                tokens.append(255);side.append(r-254)
            i+=1
    return bytes(tokens),side

def unrle2(tokens:bytes,side:list[int])->bytes:
    out=bytearray();i=0;si=0
    while i<len(tokens):
        t=tokens[i]
        if t<=1:
            value=-1;weight=1
            while i<len(tokens) and tokens[i]<=1:
                if tokens[i]==0:value+=weight
                else:value+=2*weight
                weight<<=1;i+=1
            out.extend(b"\0"*(value+1))
            continue
        if t<255:
            out.append(t-1)
        else:
            out.append(254+side[si]);si+=1
        i+=1
    if si!=len(side):raise ValueError
    return bytes(out)

def encode(data:bytes):
    primary,bwt=bwt_transform(data);mtf=mtf_encode(bwt)
    tokens,side=rle2_tokens(mtf)
    tb=encode_bytes(tokens)
    w=BitWriter()
    for bit in side:w.bit(bit)
    sb=w.finish()
    out=bytearray(vencode(primary)+vencode(len(tokens))+vencode(len(side))+vencode(len(tb)))
    out+=tb+sb
    return bytes(out)

def decode(blob:bytes,n:int):
    p=0;primary,p=vdecode(blob,p);nt,p=vdecode(blob,p);ns,p=vdecode(blob,p);tl,p=vdecode(blob,p)
    tokens=decode_bytes(blob[p:p+tl],nt);p+=tl
    r=BitReader(blob[p:]);side=[r.bit() for _ in range(ns)]
    mtf=unrle2(tokens,side)
    if len(mtf)!=n:raise ValueError
    return bwt_inverse(primary,mtf_decode(mtf))

def sources():
    rng=random.Random(20260927);n=16384
    structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(1000))[:n]
    repeat=(b"generic-bwt-repeat-sequence|"*1000)[:n]
    random_data=bytes(rng.randrange(256) for _ in range(n))
    p=Path("benchmark-work/bwt-rle2/alice29.txt");p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",p)
    return {"structured":structured,"repeat":repeat,"random":random_data,"alice32k":p.read_bytes()[:32768]}

def main():
    for name,data in sources().items():
        new=encode(data);assert decode(new,len(data))==data
        old,_=encode_bwt_block(data)
        print(name,len(data),{"current":len(old),"rle2":len(new)},"delta",len(new)-len(old),flush=True)
if __name__=="__main__":main()
