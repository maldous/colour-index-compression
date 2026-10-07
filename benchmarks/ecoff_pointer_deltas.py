"""Causal pointer predictions keyed by relocation-derived candidate alphabets.

Every predictor uses already decoded pointers or transmitted symbol values.
Residuals are modular signed 64-bit differences; arbitrary pointers stay exact.
"""
import struct
from cix.multinomial import vencode,vdecode
from benchmarks import ecoff_got as parent, ecoff_relocated_pointers as locator

MAGIC=b'ECRD1'


def process(data,mode,inverse=False,residuals=b''):
    if mode not in range(6):raise ValueError('invalid pointer-delta model')
    out=bytearray(data);fields=locator.candidates(data);last=0;bykey={};keys={id(v):tuple(v) for _,v,_ in fields};side=bytearray();pos=0;exact=0;small=0
    for where,options,_ in fields:
        key=keys[id(options)]
        prediction=bykey.get(key,options[0]) if mode in (2,5) else options[0] if mode==3 else last
        if inverse:
            if mode>=4:
                if any(out[where:where+8]):raise ValueError('pointer-delta skeleton is not zero')
                residual,pos=vdecode(residuals,pos)
                if residual >= 1<<64:raise ValueError('pointer residual outside word')
            else:residual=struct.unpack_from('<Q',data,where)[0]
            value=parent.parent.delta(residual,prediction,64,True) if mode else residual
            struct.pack_into('<Q',out,where,value)
        else:
            value=struct.unpack_from('<Q',data,where)[0];residual=parent.parent.delta(value,prediction,64) if mode else value
            if mode>=4:
                out[where:where+8]=bytes(8);side.extend(vencode(residual))
            elif mode:struct.pack_into('<Q',out,where,residual)
        exact+=value==prediction;small+=residual<16384
        last=value;bykey[key]=value
    if inverse and pos!=len(residuals):raise ValueError('unused pointer delta bytes')
    return bytes(out),bytes(side),dict(mapped_pointers=len(fields),exact_predictions=exact,small_residuals=small,residual_bytes=len(side))


def transform(data,mode=2):
    raw,side,stats=process(data,mode);skeleton,_=parent.transform(raw,3)
    meta=bytes([mode])+parent.pack(side)
    frame=skeleton+meta+len(meta).to_bytes(8,'little')+MAGIC
    return frame,dict(stats,mode=mode,original_bytes=len(data),transformed_bytes=len(frame))


def inverse(raw):
    if len(raw)<15 or raw[-5:]!=MAGIC:raise ValueError('invalid pointer-delta trailer')
    size=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-size
    if start<0 or size<2:raise ValueError('invalid pointer-delta metadata')
    meta=raw[start:-13];mode=meta[0];side,pos=parent.read(meta,1)
    if pos!=len(meta) or (mode<4 and side):raise ValueError('invalid residual substream')
    data=parent.inverse(raw[:start]);return process(data,mode,True,side)[0]
