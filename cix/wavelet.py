"""Hierarchical/wavelet Colour-Index coding.

A byte alphabet is recursively split by bit prefix. At every internal node:
1. encode how many symbols go to the 1-child;
2. encode the exact binary arrangement without replacement.

This is a direct recursive generalisation of C(n,k). The product of all binary
type-class cardinalities equals the multinomial sequence cardinality, while empty
branches cost nothing below the point where they disappear.
"""
from __future__ import annotations
import math
from .multinomial import _ArithmeticEncoder,_ArithmeticDecoder,vencode,vdecode

VERSION=1

def _encode_node(values:bytes,depth:int,encoder:_ArithmeticEncoder)->None:
    n=len(values)
    if n==0 or depth==8:return
    shift=7-depth
    bits=[(v>>shift)&1 for v in values]
    ones=sum(bits)

    # Child population: one of n+1 possibilities.
    encoder.encode(ones,ones+1,n+1)

    zero=n-ones;one=ones;remaining=n
    for bit in bits:
        if bit:
            encoder.encode(zero,remaining,remaining)
            one-=1
        else:
            encoder.encode(0,zero,remaining)
            zero-=1
        remaining-=1

    if ones==0:
        _encode_node(values,depth+1,encoder)
    elif ones==n:
        _encode_node(values,depth+1,encoder)
    else:
        zeros=bytes(v for v,b in zip(values,bits) if not b)
        ones_values=bytes(v for v,b in zip(values,bits) if b)
        _encode_node(zeros,depth+1,encoder)
        _encode_node(ones_values,depth+1,encoder)


def estimate_wavelet_bits(data: bytes) -> float:
    """Cheap histogram-only estimate of hierarchical CIX length."""
    counts=[0]*256
    for value in data:
        counts[value]+=1

    def node(lo:int,hi:int,depth:int)->float:
        n=sum(counts[lo:hi])
        if n==0 or depth==8:
            return 0.0
        mid=(lo+hi)//2
        ones=sum(counts[mid:hi])
        bits=math.log2(n+1)
        if 0<ones<n:
            bits+=math.log2(math.comb(n,ones))
        bits+=node(lo,mid,depth+1)
        bits+=node(mid,hi,depth+1)
        return bits

    return node(0,256,0)+24.0

def encode_wavelet(data:bytes)->bytes:
    enc=_ArithmeticEncoder()
    _encode_node(data,0,enc)
    payload,bits=enc.finish()
    return bytes((VERSION,))+vencode(bits)+payload

def _decode_node(n:int,depth:int,decoder:_ArithmeticDecoder,prefix:int=0)->bytes:
    if n==0:return b""
    if depth==8:return bytes((prefix,))*n

    total=n+1
    ones=decoder.target(total)
    if not 0<=ones<=n:raise ValueError("wavelet child count")
    decoder.update(ones,ones+1,total)

    zero=n-ones;one=ones;remaining=n;bits=[]
    for _ in range(n):
        if zero==0:
            bit=1
            decoder.update(0,one,remaining)
            one-=1
        elif one==0:
            bit=0
            decoder.update(0,zero,remaining)
            zero-=1
        else:
            target=decoder.target(remaining)
            if target<zero:
                bit=0;decoder.update(0,zero,remaining);zero-=1
            else:
                bit=1;decoder.update(zero,remaining,remaining);one-=1
        remaining-=1;bits.append(bit)

    zcount=n-ones
    zero_values=_decode_node(zcount,depth+1,decoder,prefix<<1) if zcount else b""
    one_values=_decode_node(ones,depth+1,decoder,(prefix<<1)|1) if ones else b""
    zi=oi=0;out=bytearray()
    for bit in bits:
        if bit:
            out.append(one_values[oi]);oi+=1
        else:
            out.append(zero_values[zi]);zi+=1
    return bytes(out)

def decode_wavelet(blob:bytes,source_length:int)->bytes:
    if not blob or blob[0]!=VERSION:raise ValueError("bad wavelet version")
    bits,pos=vdecode(blob,1)
    if pos+(bits+7)//8!=len(blob):raise ValueError("wavelet payload length")
    dec=_ArithmeticDecoder(blob[pos:],bits)
    return _decode_node(source_length,0,dec)
