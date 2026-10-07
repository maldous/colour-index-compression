"""Exact floating-point grid prediction for the 28-byte SAO record layout.

Decimal-grid coordinates identify a small candidate set of IEEE values. Signed
bit-pattern corrections preserve every original bit, including negative zero,
NaNs and non-grid exceptions. Rank/range controls use identical compositions.
Layout source: https://openzl.org/sddl/examples/
"""
import collections
import math
import struct
import zlib
import numpy as np
from .multinomial import (vencode,vdecode,encode_type_class,decode_type_class,
    multinomial_cardinality,_range_encode_type_sequence,TYPECLASS_RANGE)

MAGIC=b'CIXS\x01'
RAW_MAGIC=b'SAGR1'
FIELDS=((0,8,'0x1.3856bdf09d18ep-24'),(8,8,'0x1.a073a7eb7c212p-25'),
        (20,4,'0x1.f3bdfcb42e8e1p-28'),(24,4,'0x1.4d295322c9b40p-28'))
MAX_RECORDS=8_000_000


def recognizes(data):
    """Accept only the declared seven-int WCSTools 28-byte record subset.

    Recognition is total: malformed/truncated headers return ``False`` and
    the declared record count must exactly cover supplied bytes.  This keeps
    the transformer from silently treating trailing arbitrary bytes as rows.
    """
    if len(data)<28:return False
    try: _,_,count,stnum,mprop,nmag,width=struct.unpack_from('<7i',data)
    except struct.error:return False
    records=abs(count)
    return bool(count and records<=MAX_RECORDS and stnum==0 and mprop==1
                and abs(nmag)==1 and width==28 and 28+28*records==len(data))


def signed(value):
    value=int(value);return vencode(2*value if value>=0 else -2*value-1)


def read_signed(blob,pos):
    value,pos=vdecode(blob,pos);return (value//2 if not value&1 else -(value//2)-1),pos


def type_frame(stream,range_control):
    frame=encode_type_class(stream)
    if not range_control or not stream:return frame
    counts=[0]*256
    for value in stream:counts[value]+=1
    size=((multinomial_cardinality(counts)-1).bit_length()+7)//8
    prefix=frame[:-size-1];payload,bits=_range_encode_type_sequence(stream,counts)
    return prefix+bytes([TYPECLASS_RANGE])+vencode(bits)+payload


def _encode_residues(residue, mode):
    counts=collections.Counter(map(int,residue));palette=sorted(counts,key=lambda v, counts=counts:(-counts[v],v));out=bytearray()
    if len(palette)>256:
        out.append(0);payload=residue.tobytes();entropy=None
    else:
        out.append(1);out.extend(vencode(len(palette)))
        for value in palette:out.extend(signed(value))
        ids={value:i for i,value in enumerate(palette)};stream=bytes(ids[int(value)] for value in residue)
        entropy=(math.lgamma(len(residue)+1)-sum(math.lgamma(c+1) for c in counts.values()))/math.log(2)
        if mode==1:payload=stream
        else:
            payload=bytearray()
            for at in range(0,len(stream),1024):
                frame=type_frame(stream[at:at+1024],mode==3);payload.extend(vencode(len(frame)));payload.extend(frame)
    out.extend(vencode(len(payload)));out.extend(payload)
    return bytes(out), palette, entropy, len(payload)


def _encode_field(records, n, start, width, scale_hex, mode):
    scale=float.fromhex(scale_hex)
    values=records[:,start:start+width].copy().reshape(-1).view('<f'+str(width))
    valid=np.isfinite(values)&(np.abs(values.astype('float64'))<=((1<<31)-1)*scale)
    q=np.zeros(n,dtype='<i8');q[valid]=np.rint(values[valid].astype('float64')/scale).astype('int64')
    predicted=(q.astype('float64')*scale).astype('<f'+str(width))
    residue=(values.view('<u'+str(width))-predicted.view('<u'+str(width))).view('<i'+str(width))
    qbytes=b''.join(signed(v) for v in np.diff(q,prepend=0))
    encoded, palette, entropy, payload_bytes = _encode_residues(residue, mode)
    field=struct.pack('<d',scale)+vencode(len(qbytes))+qbytes+encoded
    stats={'offset':start,'width':width,'scale_hex':scale.hex(),'quantized_min':int(q.min()) if n else 0,
        'quantized_max':int(q.max()) if n else 0,'non_grid_exceptions':int((~valid).sum()),
        'residue_values':len(palette),'residue_combinatorial_bits':entropy,'quantized_bytes':len(qbytes),'residue_payload_bytes':payload_bytes}
    return field, stats


def transform(data,mode=1):
    if len(data)<28 or mode not in (0,1,2,3):raise ValueError('invalid fixed-record input')
    n=(len(data)-28)//28;tail=data[28+n*28:];records=np.frombuffer(data[28:28+n*28],dtype='u1').reshape(n,28)
    out=bytearray(RAW_MAGIC+bytes([mode])+vencode(n)+bytes([len(tail)])+data[:28]+tail);stats=[]
    if mode==0:
        out.extend(records.T.copy().tobytes());return bytes(out), {'mode': mode, 'records': n, 'transformed_bytes': len(out), 'original_bytes': len(data)}
    out.extend(records[:,16:20].T.copy().tobytes())
    for start,width,scale_hex in FIELDS:
        field, field_stats = _encode_field(records, n, start, width, scale_hex, mode)
        out.extend(field)
        stats.append(field_stats)
    return bytes(out), {'mode': mode, 'records': n, 'transformed_bytes': len(out), 'original_bytes': len(data), 'fields': stats}


def _read_coordinates(blob, pos, n):
    size,pos=vdecode(blob,pos);end=pos+size
    if end>len(blob):raise ValueError('truncated integer stream')
    q=[];previous=0
    for _ in range(n):
        delta,pos=read_signed(blob,pos);previous+=delta
        if not -(1<<31)<previous<(1<<31):raise ValueError('quantized coordinate outside range')
        q.append(previous)
    if pos!=end:raise ValueError('integer stream length mismatch')
    return q, pos


def _read_palette(blob, pos, n, width):
    if pos>=len(blob):raise ValueError('missing residual mode')
    coding=blob[pos];pos+=1;palette=[]
    if coding==1:
        count,pos=vdecode(blob,pos)
        if count>256 or (not count and n):raise ValueError('invalid correction alphabet')
        for _ in range(count):
            value,pos=read_signed(blob,pos)
            if not -(1<<(width*8-1))<=value<(1<<(width*8-1)):raise ValueError('correction outside range')
            palette.append(value)
    elif coding!=0:raise ValueError('invalid correction representation')
    return coding, palette, pos


def _read_residue_payload(blob, pos):
    size,pos=vdecode(blob,pos);payload=blob[pos:pos+size];pos+=size
    if len(payload)!=size:raise ValueError('truncated correction payload')
    return payload, pos


def _read_residue(blob, pos, n, width, mode):
    coding, palette, pos = _read_palette(blob, pos, n, width)
    payload, pos = _read_residue_payload(blob, pos)
    if not coding:
        if len(payload)!=n*width:raise ValueError('raw correction size mismatch')
        return np.frombuffer(payload,dtype='<i'+str(width)), pos
    stream=payload if mode==1 else _decode_type_stream(payload,n)
    if len(stream)!=n or any(value>=len(palette) for value in stream):raise ValueError('invalid correction symbols')
    return np.array([palette[value] for value in stream],dtype='<i'+str(width)), pos


def _decode_type_stream(payload, n):
    stream=bytearray();at=0
    for offset in range(0,n,1024):
        length,at=vdecode(payload,at);part=payload[at:at+length];at+=length;chunk,used=decode_type_class(part)
        if used!=length or len(chunk)!=min(1024,n-offset):raise ValueError('correction class mismatch')
        stream.extend(chunk)
    if at!=len(payload):raise ValueError('trailing correction classes')
    return stream


def _restore_field(blob, pos, records, n, start, width, mode):
    if pos+8>len(blob):raise ValueError('truncated grid scale')
    scale=struct.unpack_from('<d',blob,pos)[0];pos+=8
    if not math.isfinite(scale) or scale<=0:raise ValueError('invalid grid scale')
    q,pos=_read_coordinates(blob,pos,n)
    residue,pos=_read_residue(blob,pos,n,width,mode)
    predicted=(np.asarray(q,dtype='float64')*scale).astype('<f'+str(width)).view('<u'+str(width))
    bits=predicted+residue.view('<u'+str(width))
    records[:,start:start+width]=bits.view('u1').reshape(n,width)
    return pos


def inverse(blob):
    if blob[:5]!=RAW_MAGIC or len(blob)<6 or blob[5] not in (0,1,2,3):raise ValueError('invalid grid transform')
    mode=blob[5];n,pos=vdecode(blob,6)
    if pos>=len(blob):raise ValueError('missing tail length')
    nt=blob[pos];pos+=1
    if nt>=28 or pos+28+nt>len(blob):raise ValueError('invalid header or tail')
    header=blob[pos:pos+28];pos+=28;tail=blob[pos:pos+nt];pos+=nt
    if mode==0:
        if pos+28*n!=len(blob):raise ValueError('transpose length mismatch')
        return header+np.frombuffer(blob[pos:],dtype='u1').reshape(28,n).T.copy().tobytes()+tail
    records=np.zeros((n,28),dtype='u1')
    if pos+4*n>len(blob):raise ValueError('truncated opaque fields')
    records[:,16:20]=np.frombuffer(blob[pos:pos+4*n],dtype='u1').reshape(4,n).T;pos+=4*n
    for start,width,_ in FIELDS:
        pos = _restore_field(blob, pos, records, n, start, width, mode)
    if pos!=len(blob):raise ValueError('trailing grid transform')
    return header+records.tobytes()+tail


def encode(data,mode=1,backend=0):
    import lzma,brotli,zstandard
    transformed,stats=transform(data,mode)
    if backend==0:payload=lzma.compress(transformed,preset=9|lzma.PRESET_EXTREME)
    elif backend==1:payload=brotli.compress(transformed,quality=11)
    elif backend==2:payload=zstandard.ZstdCompressor(level=22).compress(transformed)
    else:raise ValueError('unknown grid backend')
    frame=MAGIC+bytes([backend])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    return frame, {**stats, 'backend': backend, 'physical_bytes': len(frame)}


def decode(frame):
    import lzma,brotli,zstandard
    if frame[:5]!=MAGIC or len(frame)<6:raise ValueError('invalid grid frame')
    backend=frame[5];n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4;payload=frame[pos:]
    if backend==0:transformed=lzma.decompress(payload)
    elif backend==1:transformed=brotli.decompress(payload)
    elif backend==2:transformed=zstandard.ZstdDecompressor().decompress(payload)
    else:raise ValueError('unknown grid backend')
    data=inverse(transformed)
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('grid frame checksum mismatch')
    return data
