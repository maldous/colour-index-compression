"""Raster/record-lag CIX model.

Detects strong repeated byte strides (including the 216-byte stride of 1728-pixel fax
scanlines), XORs each record with the previous record, then chooses the best native CIX
representation for the residual: multinomial, dominant-byte sparse exceptions, runs, or
bit-plane combinatorial coding.
"""
from __future__ import annotations

from .bitplanes import decode_bitplanes, encode_bitplanes
from .multinomial import decode_type_class_known_n, encode_type_class_known_n, vdecode, vencode
from .runs import decode_run_block, encode_run_block
from .sparse import decode_sparse_block, encode_sparse_block

RASTER_VERSION=1
INNER_MULTINOMIAL=1
INNER_SPARSE=2
INNER_RUNS=3
INNER_BITPLANE=4
COMMON_LAGS=(32,64,96,128,192,216,256,384,432,512,768,1024)

def _xor_lag(data:bytes,lag:int)->bytes:
    if lag>=len(data): return data
    return data[:lag]+bytes(data[i]^data[i-lag] for i in range(lag,len(data)))

def _undo_xor_lag(data:bytes,lag:int)->bytes:
    out=bytearray(data)
    for i in range(lag,len(out)): out[i]^=out[i-lag]
    return bytes(out)

def _equality(data:bytes,lag:int)->float:
    if lag>=len(data): return 0.0
    sample_end=min(len(data),65536)
    start=lag
    if start>=sample_end:return 0.0
    equal=sum(data[i]==data[i-lag] for i in range(start,sample_end))
    return equal/(sample_end-start)

def encode_raster_block(data:bytes)->tuple[bytes,str]:
    profiled=sorted(
        ((_equality(data,lag),lag) for lag in COMMON_LAGS if lag*2<=len(data)),
        reverse=True,
    )
    if not profiled or profiled[0][0] < 0.20:
        raise ValueError("no strong record/row lag")

    candidates=[]
    for score,lag in profiled[:3]:
        transformed=_xor_lag(data,lag)

        plain=encode_type_class_known_n(transformed)
        candidates.append((
            bytes((RASTER_VERSION,INNER_MULTINOMIAL))+vencode(lag)+plain,
            f"lag{lag}-xor->multinomial",
        ))

        counts=[0]*256
        for b in transformed:counts[b]+=1
        if max(counts)*4>=len(transformed):
            try:
                payload,desc=encode_sparse_block(transformed)
                candidates.append((
                    bytes((RASTER_VERSION,INNER_SPARSE))+vencode(lag)+payload,
                    f"lag{lag}-xor->{desc}",
                ))
            except Exception:pass

        run_count=1+sum(a!=b for a,b in zip(transformed,transformed[1:]))
        if run_count*3<=len(transformed)*2:
            try:
                payload,desc=encode_run_block(transformed)
                candidates.append((
                    bytes((RASTER_VERSION,INNER_RUNS))+vencode(lag)+payload,
                    f"lag{lag}-xor->{desc}",
                ))
            except Exception:pass

        try:
            payload,desc=encode_bitplanes(transformed)
            candidates.append((
                bytes((RASTER_VERSION,INNER_BITPLANE))+vencode(lag)+payload,
                f"lag{lag}-xor->{desc}",
            ))
        except Exception:pass

    return min(candidates,key=lambda item:len(item[0]))

def decode_raster_block(blob:bytes,*,source_length:int)->bytes:
    if len(blob)<2 or blob[0]!=RASTER_VERSION:
        raise ValueError("unknown raster block version")
    mode=blob[1];lag,pos=vdecode(blob,2);payload=blob[pos:]
    if not 0<lag<source_length:raise ValueError("invalid raster lag")

    if mode==INNER_MULTINOMIAL:
        transformed,used=decode_type_class_known_n(payload,0,source_length)
        if used!=len(payload):raise ValueError("unused raster multinomial bytes")
    elif mode==INNER_SPARSE:
        transformed=decode_sparse_block(payload,source_length=source_length)
    elif mode==INNER_RUNS:
        transformed=decode_run_block(payload,source_length=source_length)
    elif mode==INNER_BITPLANE:
        transformed=decode_bitplanes(payload,source_length=source_length)
    else:
        raise ValueError("unknown raster inner mode")
    return _undo_xor_lag(transformed,lag)
