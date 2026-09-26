"""Record/field-conditioned multinomial CIX.

For candidate record width w, bytes at offsets i mod w form deterministic lanes.
Each lane is encoded as its own 256-symbol type class. No per-byte selector is stored;
given n and w, the decoder knows exactly which lane supplies every output position.

This is the positional analogue of context-conditioned multinomial CIX and is useful for
spreadsheets, binary records, telemetry, executables, and raster rows.
"""
from __future__ import annotations

import math
from collections import Counter

from .multinomial import (
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)

RECORD_VERSION=1
WIDTHS=(2,3,4,8,12,16,24,32,48,64,96,128,216,256,384,512,768,1024)

def _estimate_lane(lane:bytes)->float:
    n=len(lane)
    if not n:return 0.0
    counts=Counter(lane);m=len(counts)
    bits=8.0
    if m<256:bits+=math.log2(math.comb(256,m))
    if m>1:bits+=math.log2(math.comb(n-1,m-1))
    bits+=(math.lgamma(n+1)-sum(math.lgamma(c+1) for c in counts.values()))/math.log(2.0)
    return bits/8.0

def _estimate(data:bytes,width:int)->float:
    return sum(_estimate_lane(data[lane::width]) for lane in range(width))

def profile_record_widths(data:bytes)->list[tuple[float,int]]:
    widths=[w for w in WIDTHS if w<=len(data)//16]
    return sorted((_estimate(data,w),w) for w in widths)

def best_record_estimate(data:bytes)->float:
    profiled=profile_record_widths(data)
    return profiled[0][0] if profiled else float("inf")

def encode_record_block(data:bytes,beam:int=2)->tuple[bytes,str]:
    profiled=profile_record_widths(data)[:beam]
    if not profiled:raise ValueError("block too short for record model")
    candidates=[]
    for _,width in profiled:
        out=bytearray((RECORD_VERSION,));out+=vencode(width)
        for lane in range(width):
            stream=data[lane::width]
            out+=encode_type_class_known_n(stream)
        candidates.append((bytes(out),f"record-multinomial-w{width}"))
    return min(candidates,key=lambda x:len(x[0]))

def decode_record_block(blob:bytes,*,source_length:int)->bytes:
    if not blob or blob[0]!=RECORD_VERSION:
        raise ValueError("unknown record block version")
    width,pos=vdecode(blob,1)
    if not 1<=width<=source_length:raise ValueError("invalid record width")
    lanes=[]
    for lane in range(width):
        count=(source_length-lane+width-1)//width if lane<source_length else 0
        stream,pos=decode_type_class_known_n(blob,pos,count)
        lanes.append(stream)
    if pos!=len(blob):raise ValueError("trailing record bytes")
    cursors=[0]*width;out=bytearray(source_length)
    for index in range(source_length):
        lane=index%width
        out[index]=lanes[lane][cursors[lane]]
        cursors[lane]+=1
    return bytes(out)
