#!/usr/bin/env python3
from __future__ import annotations
import random, urllib.request
from pathlib import Path
from cix.multinomial import _ArithmeticEncoder,_ArithmeticDecoder,vencode,vdecode

METHODS={0:"one",1:"distinct",2:"half-distinct",3:"singletons"}

def ctx(h,o): return bytes(h[-o:]) if o else b""
def eligible(counts,excluded):
    if not counts:return []
    return [s for s in sorted(counts) if s not in excluded]
def escape_mass(counts,symbols,method):
    if method==0:return 1
    if method==1:return max(1,len(symbols))
    if method==2:return max(1,(len(symbols)+1)//2)
    if method==3:return max(1,sum(1 for s in symbols if counts[s]==1))
    raise ValueError

def encode(data,order,method):
    tables={};h=bytearray();enc=_ArithmeticEncoder()
    for symbol in data:
        excluded=set();coded=False
        for o in range(min(order,len(h)),-1,-1):
            c=tables.get(ctx(h,o));syms=eligible(c,excluded)
            if not syms:continue
            mass=sum(c[s] for s in syms);esc=escape_mass(c,syms,method);total=mass+esc
            if symbol in c and symbol not in excluded:
                low=0
                for candidate in syms:
                    high=low+c[candidate]
                    if candidate==symbol:
                        enc.encode(low,high,total);coded=True;break
                    low=high
                if coded:break
            else:
                enc.encode(mass,total,total);excluded.update(syms)
        if not coded:
            remaining=[s for s in range(256) if s not in excluded]
            rank=remaining.index(symbol);enc.encode(rank,rank+1,len(remaining))
        for o in range(min(order,len(h)),-1,-1):
            k=ctx(h,o);c=tables.setdefault(k,{})
            c[symbol]=c.get(symbol,0)+1
            if sum(c.values())>16384:
                for s in list(c):c[s]=max(1,(c[s]+1)//2)
        if order:
            h.append(symbol)
            if len(h)>order:del h[:-order]
    p,bits=enc.finish()
    return bytes((method,order))+vencode(bits)+p

def decode(blob,n):
    method,order=blob[0],blob[1];bits,p=vdecode(blob,2)
    dec=_ArithmeticDecoder(blob[p:],bits);tables={};h=bytearray();out=bytearray()
    for _ in range(n):
        excluded=set();symbol=None
        for o in range(min(order,len(h)),-1,-1):
            c=tables.get(ctx(h,o));syms=eligible(c,excluded)
            if not syms:continue
            mass=sum(c[s] for s in syms);esc=escape_mass(c,syms,method);total=mass+esc
            target=dec.target(total)
            if target<mass:
                low=0
                for candidate in syms:
                    high=low+c[candidate]
                    if target<high:
                        dec.update(low,high,total);symbol=candidate;break
                    low=high
                break
            dec.update(mass,total,total);excluded.update(syms)
        if symbol is None:
            remaining=[s for s in range(256) if s not in excluded]
            target=dec.target(len(remaining));symbol=remaining[target]
            dec.update(target,target+1,len(remaining))
        out.append(symbol)
        for o in range(min(order,len(h)),-1,-1):
            k=ctx(h,o);c=tables.setdefault(k,{})
            c[symbol]=c.get(symbol,0)+1
            if sum(c.values())>16384:
                for s in list(c):c[s]=max(1,(c[s]+1)//2)
        if order:
            h.append(symbol)
            if len(h)>order:del h[:-order]
    return bytes(out)

def sources():
    rng=random.Random(20260927);n=16384
    structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(1000))[:n]
    markov=bytearray();v=0
    for _ in range(n):
        if rng.random()<.03:v=rng.randrange(256)
        markov.append(v)
    random_data=bytes(rng.randrange(256) for _ in range(8192))
    path=Path("benchmark-work/ppm-escape/alice29.txt");path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists(): urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",path)
    return {"structured":(structured,3),"markov":(bytes(markov),1),"random":(random_data,1),"alice64k":(path.read_bytes()[:65536],4)}

def main():
    for name,(data,order) in sources().items():
        row={}
        for method,label in METHODS.items():
            p=encode(data,order,method);assert decode(p,len(data))==data
            row[label]=len(p)
        print(name,len(data),"order",order,row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
