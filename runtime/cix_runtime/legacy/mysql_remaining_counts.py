"""Exact remaining-count order codec retained from the MyISAM constraint path."""
from __future__ import annotations

import collections
import math

from .multinomial import Fenwick, _ArithmeticDecoder, _ArithmeticEncoder, multinomial_cardinality, vdecode, vencode

def _permutation_blocks(ids, counts):
    tree=Fenwick(counts);out=bytearray(b'\x04');remaining=len(ids);rank=0;product=1;used=0
    for symbol in ids:
        digit=tree.prefix(symbol);rank=rank*remaining+digit;product*=remaining;tree.add(symbol,-1);remaining-=1;used+=1
        if used==1024 or not remaining:
            out.extend(rank.to_bytes(((product-1).bit_length()+7)//8,'big'));rank=0;product=1;used=0
    return bytes(out)

def _type_class_rank(ids, counts):
    cardinality=multinomial_cardinality(counts);total=cardinality;remaining=len(ids);mutable=counts[:];tree=Fenwick(mutable);rank=0
    for symbol in ids:
        rank+=total*tree.prefix(symbol)//remaining;total=total*mutable[symbol]//remaining;mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    return b'\x03'+rank.to_bytes(((cardinality-1).bit_length()+7)//8,'big')

def _decode_plain(blob, n):
    pos=1;out=[]
    for _ in range(n):x,pos=vdecode(blob,pos);out.append(x)
    if pos!=len(blob):raise ValueError('trailing IDs')
    return out

def _decode_arithmetic(blob, counts, dynamic):
    bits,pos=vdecode(blob,1)
    if len(blob)-pos!=(bits+7)//8:raise ValueError('order arithmetic length')
    decoder=_ArithmeticDecoder(blob[pos:],bits);mutable=counts[:];tree=Fenwick(mutable);remaining=sum(counts);out=[]
    for _ in range(remaining):
        target=decoder.target(remaining);symbol=tree.select(target);low=tree.prefix(symbol);decoder.update(low,low+mutable[symbol],remaining);out.append(symbol)
        if dynamic:mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    return out

def _decode_rank(blob, counts):
    n=sum(counts)
    if n>4096:raise ValueError('oversized exact rank')
    total=multinomial_cardinality(counts);rank=int.from_bytes(blob[1:],'big')
    if len(blob)-1!=((total-1).bit_length()+7)//8 or rank>=total:raise ValueError('invalid type-class rank')
    mutable=counts[:];tree=Fenwick(mutable);remaining=n;out=[]
    while remaining:
        symbol=tree.select(rank*remaining//total);rank-=total*tree.prefix(symbol)//remaining;total=total*mutable[symbol]//remaining;out.append(symbol);mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    return out

def _decode_permutation_blocks(blob, counts):
    if any(c!=1 for c in counts):raise ValueError('not a permutation')
    tree=Fenwick(counts);remaining=sum(counts);pos=1;out=[]
    while remaining:
        length=min(1024,remaining);bases=list(range(remaining,remaining-length,-1));product=math.prod(bases);width=((product-1).bit_length()+7)//8
        rank=int.from_bytes(blob[pos:pos+width],'big');pos+=width
        if pos>len(blob) or rank>=product:raise ValueError('invalid conditional permutation rank')
        digits=[0]*length
        for i in range(length-1,-1,-1):rank,digits[i]=divmod(rank,bases[i])
        for digit in digits:
            symbol=tree.select(digit);out.append(symbol);tree.add(symbol,-1);remaining-=1
    if pos!=len(blob):raise ValueError('trailing permutation ranks')
    return out

def order_encode(ids,counts,mode):
    n=len(ids)
    if mode==1:return b'\x00'+b''.join(vencode(x) for x in ids)
    if mode==4 and all(c==1 for c in counts):
        return _permutation_blocks(ids, counts)
    if mode==4 and n<=4096:
        return _type_class_rank(ids, counts)
    encoder=_ArithmeticEncoder();mutable=counts[:];tree=Fenwick(mutable);remaining=n;dynamic=mode!=2
    for symbol in ids:
        low=tree.prefix(symbol);encoder.encode(low,low+mutable[symbol],remaining)
        if dynamic:mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    payload,bits=encoder.finish()
    return bytes([2 if dynamic else 1])+vencode(bits)+payload


def order_decode(blob,counts):
    if not blob:raise ValueError('missing ordering mode')
    kind=blob[0];n=sum(counts);out=[]
    if kind==0:
        out=_decode_plain(blob,n)
    elif kind in (1,2):
        out=_decode_arithmetic(blob,counts,kind==2)
    elif kind==3:
        out=_decode_rank(blob,counts)
    elif kind==4:
        out=_decode_permutation_blocks(blob,counts)
    else:raise ValueError('invalid ordering mode')
    expected = dict(enumerate(counts))
    if len(out)!=n or collections.Counter(out)!=collections.Counter(expected):raise ValueError('ordering composition mismatch')
    return out
