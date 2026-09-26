"""Format-agnostic periodic residual CIX.

Candidate lags are discovered from repeated byte shingles. For the strongest candidates,
CIX tries XOR and modular subtraction predictors and encodes the residual using the best
native representation. No filename, media dimension, record schema or architecture
constant is consulted.
"""
from __future__ import annotations

import math
from collections import Counter

from .bitplanes import decode_bitplanes, encode_bitplanes
from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .record import discover_record_widths
from .runs import decode_run_block, encode_run_block
from .sparse import decode_sparse_block, encode_sparse_block

PERIODIC_VERSION=1
OP_XOR=0
OP_SUB=1
INNER_MULTINOMIAL=0
INNER_SPARSE=1
INNER_RUNS=2
INNER_BITPLANE=3


def _xor_lag(data:bytes,lag:int)->bytes:
    return data[:lag]+bytes(data[i]^data[i-lag] for i in range(lag,len(data)))

def _sub_lag(data:bytes,lag:int)->bytes:
    return data[:lag]+bytes((data[i]-data[i-lag])&255 for i in range(lag,len(data)))

def _undo_xor(data:bytes,lag:int)->bytes:
    out=bytearray(data)
    for i in range(lag,len(out)): out[i]^=out[i-lag]
    return bytes(out)

def _undo_sub(data:bytes,lag:int)->bytes:
    out=bytearray(data)
    for i in range(lag,len(out)): out[i]=(out[i]+out[i-lag])&255
    return bytes(out)

def _typeclass_estimate(data:bytes)->float:
    n=len(data)
    if not n:return 1.0
    counts=Counter(data);m=len(counts)
    bits=8.0
    if m<256:bits+=math.log2(math.comb(256,m))
    if m>1:bits+=math.log2(math.comb(n-1,m-1))
    bits+=(math.lgamma(n+1)-sum(math.lgamma(c+1) for c in counts.values()))/math.log(2.0)
    return bits/8.0

def profile_periods(data:bytes,limit:int=12)->list[tuple[float,int,int,bytes]]:
    profiled=[]
    for lag in discover_record_widths(data):
        if lag*2>len(data): continue
        for op in (OP_XOR,OP_SUB):
            residual=_xor_lag(data,lag) if op==OP_XOR else _sub_lag(data,lag)
            profiled.append((_typeclass_estimate(residual),lag,op,residual))
    return sorted(profiled,key=lambda x:(x[0],x[1],x[2]))[:limit]

def best_periodic_estimate(data:bytes)->float:
    profiled=profile_periods(data,1)
    return profiled[0][0] if profiled else float("inf")

def encode_periodic_block(data:bytes,beam:int=3)->tuple[bytes,str]:
    candidates=[]
    for _,lag,op,residual in profile_periods(data,max(beam,1))[:beam]:
        inners=[]
        plain=encode_type_class_known_n(residual)
        inners.append((INNER_MULTINOMIAL,plain,"multinomial"))

        counts=Counter(residual)
        if counts and max(counts.values())*4>=len(residual):
            try:
                p,d=encode_sparse_block(residual)
                inners.append((INNER_SPARSE,p,d))
            except Exception: pass

        run_count=1+sum(a!=b for a,b in zip(residual,residual[1:])) if residual else 0
        if residual and run_count*3<=len(residual)*2:
            try:
                p,d=encode_run_block(residual)
                inners.append((INNER_RUNS,p,d))
            except Exception: pass

        try:
            p,d=encode_bitplanes(residual)
            inners.append((INNER_BITPLANE,p,d))
        except Exception: pass

        inner,payload,desc=min(inners,key=lambda item:len(item[1]))
        out=bytes((PERIODIC_VERSION,op,inner))+vencode(lag)+payload
        opname="xor" if op==OP_XOR else "sub"
        candidates.append((out,f"period-{lag}-{opname}->{desc}"))

    if not candidates: raise ValueError("no periodic candidates")
    return min(candidates,key=lambda x:len(x[0]))

def decode_periodic_block(blob:bytes,*,source_length:int)->bytes:
    if len(blob)<3 or blob[0]!=PERIODIC_VERSION:
        raise ValueError("unknown periodic block version")
    op=blob[1];inner=blob[2];lag,pos=vdecode(blob,3);payload=blob[pos:]
    if not 0<lag<source_length: raise ValueError("invalid periodic lag")

    if inner==INNER_MULTINOMIAL:
        residual,used=decode_type_class_known_n(payload,0,source_length)
        if used!=len(payload): raise ValueError("unused periodic multinomial bytes")
    elif inner==INNER_SPARSE:
        residual=decode_sparse_block(payload,source_length=source_length)
    elif inner==INNER_RUNS:
        residual=decode_run_block(payload,source_length=source_length)
    elif inner==INNER_BITPLANE:
        residual=decode_bitplanes(payload,source_length=source_length)
    else:
        raise ValueError("unknown periodic inner mode")

    if op==OP_XOR:return _undo_xor(residual,lag)
    if op==OP_SUB:return _undo_sub(residual,lag)
    raise ValueError("unknown periodic operation")
