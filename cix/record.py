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
BASE_WIDTHS=(2,3,4,8,12,16,24,32,48,64,96,128,192,216,256,384,432,512,768,1024,1536,2048)

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

def _divisors(value:int)->set[int]:
    out=set()
    root=int(math.isqrt(value))
    for d in range(2,root+1):
        if value%d==0:
            out.add(d)
            out.add(value//d)
    return out

def discover_record_widths(data:bytes,max_width:int=2048)->list[int]:
    """Discover likely periods from repeated 4-byte shingles.

    The search is format agnostic: repeated local byte patterns vote for the distance
    at which they recur. Strong distances and their divisors are then considered as
    deterministic record widths alongside a small universal prior set.
    """
    limit=min(max_width,max(0,len(data)//16))
    if limit<2:
        return []

    candidates={w for w in BASE_WIDTHS if w<=limit}
    previous={}
    votes=Counter()
    sample=data[:min(len(data),65536)]
    for pos in range(0,max(0,len(sample)-4),4):
        token=sample[pos:pos+4]
        last=previous.get(token)
        if last is not None:
            distance=pos-last
            if 2<=distance<=limit:
                votes[distance]+=1
        previous[token]=pos

    for distance,_ in votes.most_common(16):
        candidates.add(distance)
        candidates.update(d for d in _divisors(distance) if d<=limit)

    return sorted(candidates)

def profile_record_widths(data:bytes)->list[tuple[float,int]]:
    widths=discover_record_widths(data)
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
