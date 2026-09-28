"""Causal grid-coordinate feedback predicts exact floating-point corrections.

All coordinates are decoded before their corrections. A table keyed by the
decoded coordinate predicts the last correction at that coordinate. No table is
transmitted or obtained from the source at decode time. Rank/range controls
receive exactly the same residuals and compositions.
"""
import collections
import math
import zlib
import numpy as np
from cix.multinomial import vencode,vdecode,decode_type_class
from benchmarks import record_float_grid as grid

MAGIC=b'CIXY\x01'
RAW=b'SGFB1'


def prefix(blob):
    if blob[:5]!=grid.RAW_MAGIC or blob[5]!=1:raise ValueError('expected raw-palette grid stream')
    n,pos=vdecode(blob,6)
    pos+=1+28+blob[pos]+4*n
    if pos>len(blob):raise ValueError('truncated grid prefix')
    return n,pos


def quantized(blob,n):
    q=[];pos=0;previous=0
    for _ in range(n):
        delta,pos=grid.read_signed(blob,pos);previous+=delta;q.append(previous)
    if pos!=len(blob):raise ValueError('coordinate stream length mismatch')
    return q


def read_field(blob,pos,n,width,mode):
    start=pos;pos+=8;size,pos=vdecode(blob,pos);qbytes=blob[pos:pos+size];pos+=size
    q=quantized(qbytes,n);field_prefix=blob[start:pos]
    coding=blob[pos];pos+=1;palette=[]
    if coding==1:
        count,pos=vdecode(blob,pos)
        if count>256 or (not count and n):raise ValueError('invalid correction palette')
        for _ in range(count):value,pos=grid.read_signed(blob,pos);palette.append(value)
    elif coding!=0:raise ValueError('invalid correction coding')
    size,pos=vdecode(blob,pos);payload=blob[pos:pos+size];pos+=size
    if len(payload)!=size:raise ValueError('truncated corrections')
    if coding==0:
        if size!=n*width:raise ValueError('raw correction size')
        residues=list(map(int,np.frombuffer(payload,dtype='<i'+str(width))))
    else:
        if mode==1:ids=payload
        else:
            ids=bytearray();at=0
            for offset in range(0,n,1024):
                length,at=vdecode(payload,at);part=payload[at:at+length];at+=length
                chunk,used=decode_type_class(part)
                if used!=length or len(chunk)!=min(1024,n-offset):raise ValueError('correction class mismatch')
                ids.extend(chunk)
            if at!=len(payload):raise ValueError('trailing correction classes')
        if len(ids)!=n or any(x>=len(palette) for x in ids):raise ValueError('invalid correction IDs')
        residues=[palette[x] for x in ids]
    return q,residues,field_prefix,pos


def write_field(residues,width,mode):
    counts=collections.Counter(residues);palette=sorted(counts,key=lambda x:(-counts[x],x));out=bytearray()
    if len(palette)>256:
        out.append(0);payload=np.array(residues,dtype='<i'+str(width)).tobytes()
    else:
        out.append(1);out.extend(vencode(len(palette)))
        for value in palette:out.extend(grid.signed(value))
        lookup={value:i for i,value in enumerate(palette)};ids=bytes(lookup[x] for x in residues)
        if mode==1:payload=ids
        else:
            payload=bytearray()
            for at in range(0,len(ids),1024):
                frame=grid.type_frame(ids[at:at+1024],mode==3);payload.extend(vencode(len(frame)));payload.extend(frame)
    out.extend(vencode(len(payload)));out.extend(payload)
    n=len(residues)
    bits=(math.lgamma(n+1)-sum(math.lgamma(c+1) for c in counts.values()))/math.log(2)
    return bytes(out),dict(correction_alphabet=len(palette),correction_combinatorial_bits=bits,correction_payload_bytes=len(payload))


def feedback(q,residues,width,reverse=False):
    history={};out=[];mod=1<<(8*width);half=mod//2
    for coordinate,value in zip(q,residues):
        prediction=history.get(coordinate,0)
        actual=(value+prediction+half)%mod-half if reverse else value
        error=(value-prediction+half)%mod-half
        out.append(actual if reverse else error);history[coordinate]=actual
    return out


def transform(data,mode=1,model=1):
    if mode not in (1,2,3) or model not in (0,1):raise ValueError('invalid feedback policy')
    base,base_stats=grid.transform(data,1);n,pos=prefix(base)
    out=bytearray(RAW+bytes([mode,model])+base[:pos]);rows=[]
    for start,width,_ in grid.FIELDS:
        q,values,field_prefix,pos=read_field(base,pos,n,width,1)
        predicted=feedback(q,values,width) if model else values
        payload,stats=write_field(predicted,width,mode);out.extend(field_prefix);out.extend(payload)
        rows.append(dict(offset=start,zero_corrections_before=values.count(0),zero_corrections_after=predicted.count(0),**stats))
    if pos!=len(base):raise ValueError('trailing base grid stream')
    return bytes(out),dict(mode=mode,model=model,records=n,original_bytes=len(data),transformed_bytes=len(out),fields=rows,base_fields=base_stats['fields'])


def inverse(blob):
    if blob[:5]!=RAW or len(blob)<7 or blob[5] not in (1,2,3) or blob[6] not in (0,1):raise ValueError('invalid feedback transform')
    mode,model=blob[5:7];base=blob[7:];n,pos=prefix(base);out=bytearray(base[:pos])
    for _,width,_ in grid.FIELDS:
        q,values,field_prefix,pos=read_field(base,pos,n,width,mode)
        restored=feedback(q,values,width,True) if model else values
        out.extend(field_prefix);out.extend(write_field(restored,width,1)[0])
    if pos!=len(base):raise ValueError('trailing feedback transform')
    return grid.inverse(bytes(out))


def encode(data,mode=1,model=1,backend=1,paq_options='-4'):
    import lzma,brotli,zstandard
    transformed,stats=transform(data,mode,model)
    if backend==0:payload=lzma.compress(transformed,preset=9|lzma.PRESET_EXTREME)
    elif backend==1:payload=brotli.compress(transformed,quality=11)
    elif backend==2:payload=zstandard.ZstdCompressor(level=22).compress(transformed)
    elif backend==3:
        from benchmarks.competitive_codec import encode_paq
        payload=encode_paq(transformed,'v215',paq_options)
    else:raise ValueError('invalid feedback backend')
    frame=MAGIC+bytes([backend])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    return frame,dict(**stats,backend=backend,physical_bytes=len(frame))


def decode(frame):
    import lzma,brotli,zstandard
    if frame[:5]!=MAGIC or len(frame)<6:raise ValueError('invalid feedback frame')
    backend=frame[5];n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    if backend==0:raw=lzma.decompress(frame[pos:])
    elif backend==1:raw=brotli.decompress(frame[pos:])
    elif backend==2:raw=zstandard.ZstdDecompressor().decompress(frame[pos:])
    elif backend==3:
        from benchmarks.competitive_codec import decode as decode_paq
        raw=decode_paq(frame[pos:])
    else:raise ValueError('invalid feedback backend')
    data=inverse(raw)
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('feedback checksum mismatch')
    return data
