#!/usr/bin/env python3
from __future__ import annotations
import urllib.request
from pathlib import Path

from cix.multinomial import _ArithmeticDecoder,_ArithmeticEncoder,vdecode,vencode
from cix.ppm import (
    ESCAPE_DISTINCT, _ctx, _eligible, _escape_mass, _rescale,
    encode_ppm, decode_ppm,
)

VERSION=1
TRAIN_MAX=65536
TRAIN_MIN=4096

def _observe(tables,history,symbol,order):
    for o in range(min(order,len(history)),-1,-1):
        key=_ctx(history,o);counts=tables.setdefault(key,{})
        counts[symbol]=counts.get(symbol,0)+1;_rescale(counts)
    if order:
        history.append(symbol)
        if len(history)>order:del history[:-order]

def _prime(prefix,block_len,order):
    tables={};history=bytearray()
    train=min(len(prefix),TRAIN_MAX,max(TRAIN_MIN,block_len*2))
    start=len(prefix)-train
    if start>0 and order:
        history.extend(prefix[max(0,start-order):start])
    for symbol in prefix[start:]:
        _observe(tables,history,symbol,order)
    return tables,history

def encode(data,prefix,order=4):
    tables,history=_prime(prefix,len(data),order);enc=_ArithmeticEncoder()
    for symbol in data:
        excluded=set();coded=False
        for o in range(min(order,len(history)),-1,-1):
            counts=tables.get(_ctx(history,o));symbols=_eligible(counts,excluded)
            if not symbols:continue
            mass=sum(counts[s] for s in symbols)
            escape=_escape_mass(counts,symbols,ESCAPE_DISTINCT);total=mass+escape
            if symbol in counts and symbol not in excluded:
                low=0
                for candidate in symbols:
                    high=low+counts[candidate]
                    if candidate==symbol:
                        enc.encode(low,high,total);coded=True;break
                    low=high
                if coded:break
            else:
                enc.encode(mass,total,total);excluded.update(symbols)
        if not coded:
            remain=[s for s in range(256) if s not in excluded]
            rank=remain.index(symbol);enc.encode(rank,rank+1,len(remain))
        _observe(tables,history,symbol,order)
    payload,bits=enc.finish()
    return bytes((VERSION,order))+vencode(bits)+payload

def decode(blob,n,prefix):
    order=blob[1];bits,pos=vdecode(blob,2)
    dec=_ArithmeticDecoder(blob[pos:],bits);tables,history=_prime(prefix,n,order);out=bytearray()
    for _ in range(n):
        excluded=set();symbol=None
        for o in range(min(order,len(history)),-1,-1):
            counts=tables.get(_ctx(history,o));symbols=_eligible(counts,excluded)
            if not symbols:continue
            mass=sum(counts[s] for s in symbols)
            escape=_escape_mass(counts,symbols,ESCAPE_DISTINCT);total=mass+escape
            target=dec.target(total)
            if target<mass:
                low=0
                for candidate in symbols:
                    high=low+counts[candidate]
                    if target<high:
                        dec.update(low,high,total);symbol=candidate;break
                    low=high
                break
            dec.update(mass,total,total);excluded.update(symbols)
        if symbol is None:
            remain=[s for s in range(256) if s not in excluded]
            target=dec.target(len(remain));symbol=remain[target]
            dec.update(target,target+1,len(remain))
        out.append(symbol);_observe(tables,history,symbol,order)
    return bytes(out)

def main():
    p=Path("benchmark-work/ppm-warm/alice29.txt");p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",p)
    data=p.read_bytes()
    whole=len(encode_ppm(data,max_order=4))
    print("whole-reset",whole,flush=True)

    for chunk in (4096,8192,16384,32768,65536):
        reset=warm=0;prefix=b""
        for start in range(0,len(data),chunk):
            block=data[start:start+chunk]
            r=encode_ppm(block,max_order=4)
            assert decode_ppm(r,source_length=len(block))==block
            reset+=len(r)

            w=encode(block,prefix,4)
            assert decode(w,len(block),prefix)==block
            warm+=len(w)
            prefix=(prefix+block)[-TRAIN_MAX:]
        print("chunk",chunk,"reset",reset,"warm",warm,"delta",warm-reset,"vs-whole",warm-whole,flush=True)

if __name__=="__main__":main()
