"""Identical PAQ predictions -> confidence-partitioned conditional compositions.

Control 0 enumerates the exact binary type class. Control 1 arithmetic-codes the
same remaining-count constraint. Both transmit all per-bin lengths and counts.
The PAQ model is replayed causally during restoration, without the source trace.
"""
import math
import os
import subprocess
import tempfile
import zlib
from pathlib import Path
import numpy as np
from cix.multinomial import vencode,vdecode,_ArithmeticEncoder,_ArithmeticDecoder

MAGIC=b'CIXH\x02'
ROOT=Path(__file__).resolve().parents[1]
BINARY=ROOT/'benchmark-work/references/paq8px-cix-bridge/build-local/paq8px'


def partition(trace,subbits):
    if subbits not in range(4) or len(trace)%4:raise ValueError('invalid prediction trace')
    words=np.frombuffer(trace,dtype='<u4').astype(np.uint64)
    p=words&0x7fffffff;y=words>>31
    if np.any(p==0):raise ValueError('zero PAQ probability')
    q=np.minimum(p,(1<<31)-p)
    # Powers of two are exactly represented; log2 only locates an integer bucket.
    exponent=np.floor(np.log2(q)).astype(np.uint64)
    base=np.left_shift(np.uint64(1),exponent)
    bucket=(exponent<<subbits)+(((q-base)<<subbits)//base)
    errors=(y^(p>>30)).astype(np.uint8)
    groups=[errors[bucket==index].tobytes() for index in range(31<<subbits)]
    actual=np.where(y!=0,p,(1<<31)-p)
    predicted_bits=float(np.sum(31-np.log2(actual)))
    return groups,dict(raw_event_bits=len(words),paq_prediction_bits=predicted_bits,
                      bits_removed_by_prediction=len(words)-predicted_bits)


def rank_binary(stream):
    n=len(stream);k=sum(stream);total=math.comb(n,k);width=(total-1).bit_length();rank=0
    for bit in stream:
        if k==0 or k==n:break
        zero=total*(n-k)//n
        if bit:rank+=zero;total-=zero;k-=1
        else:total=zero
        n-=1
    return rank.to_bytes((width+7)//8,'big')


def unrank_binary(blob,n,k):
    total=math.comb(n,k);width=(total-1).bit_length()
    if len(blob)!=(width+7)//8:raise ValueError('rank width mismatch')
    rank=int.from_bytes(blob,'big')
    if rank>=total:raise ValueError('rank outside conditional type class')
    out=bytearray()
    while n:
        if k==0:out.extend(bytes(n));break
        if k==n:out.extend(b'\1'*n);break
        zero=total*(n-k)//n
        if rank<zero:out.append(0);total=zero
        else:out.append(1);rank-=zero;total-=zero;k-=1
        n-=1
    return bytes(out)


def arith_binary(stream):
    n=len(stream);k=sum(stream);coder=_ArithmeticEncoder()
    if k==0 or k==n:return b''
    for bit in stream:
        if k==0 or k==n:break
        if bit:coder.encode(n-k,n,n);k-=1
        else:coder.encode(0,n-k,n)
        n-=1
    payload,bits=coder.finish()
    return vencode(bits)+payload


def unarith_binary(blob,pos,n,k,legacy=False):
    if not legacy and (k==0 or k==n):return bytes([bool(k)])*n,pos
    bits,pos=vdecode(blob,pos);size=(bits+7)//8
    if pos+size>len(blob):raise ValueError('truncated arithmetic residual')
    coder=_ArithmeticDecoder(blob[pos:pos+size],bits);out=bytearray()
    while n:
        if k==0:out.extend(bytes(n));break
        if k==n:out.extend(b'\1'*n);break
        target=coder.target(n)
        if target<n-k:out.append(0);coder.update(0,n-k,n)
        else:out.append(1);coder.update(n-k,n,n);k-=1
        n-=1
    return bytes(out),pos+size


def encode(trace,paq_archive,source,subbits=1,method=0):
    if method not in (0,1):raise ValueError('unsupported residual method')
    if paq_archive[:6]!=b'paq8px':raise ValueError('missing PAQ archive header')
    # OPTION_USELSTM is 32 in the pinned upstream Shared definition.
    header_size=9 if paq_archive[7]&32 else 8
    header=paq_archive[:header_size]
    groups,stats=partition(trace,subbits)
    out=bytearray(MAGIC+bytes([subbits,method,header_size])+header+vencode(len(source))+zlib.crc32(source).to_bytes(4,'big'))
    theoretical=0.0;rank_bytes=0;composition_bytes=0
    for stream in groups:
        n=len(stream);k=sum(stream);count_header=vencode(n)+(vencode(k) if n else b'')
        out.extend(count_header);composition_bytes+=len(count_header)
        cardinality=math.comb(n,k);theoretical+=math.log2(cardinality) if cardinality else 0
        payload=rank_binary(stream) if method==0 else arith_binary(stream)
        out.extend(payload);rank_bytes+=len(payload)
    stats.update(combinatorial_uncertainty_bits=theoretical,composition_metadata_bytes=composition_bytes,
        residual_payload_bytes=rank_bytes,physical_bytes=len(out),baseline_paq_bytes=len(paq_archive),
        delta_vs_paq_bytes=len(out)-len(paq_archive),subbits=subbits,method=method,
        interpretation='The difference from PAQ includes confidence quantization and paid composition constraints. Arithmetic control uses identical constraints.')
    return bytes(out),stats


def residuals(frame):
    if len(frame)<16 or frame[:4]!=b'CIXH' or frame[4] not in (1,2) or frame[5] not in range(4) or frame[6] not in (0,1) or frame[7] not in (8,9):raise ValueError('invalid PAQ/CIX frame')
    legacy=frame[4]==1
    subbits,method,header_size=frame[5:8];header=frame[8:8+header_size];pos=8+header_size
    if header[:6]!=b'paq8px':raise ValueError('invalid embedded PAQ header')
    original,pos=vdecode(frame,pos)
    if pos+4>len(frame):raise ValueError('truncated CRC')
    crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    raw=bytearray(b'CIXE1'+bytes([subbits]));total=0
    for _ in range(31<<subbits):
        n,pos=vdecode(frame,pos)
        if n or legacy:k,pos=vdecode(frame,pos)
        else:k=0
        total+=n
        if k>n or total>1<<28:raise ValueError('invalid diagnostic event count')
        if method==0:
            width=(math.comb(n,k)-1).bit_length();size=(width+7)//8
            stream=unrank_binary(frame[pos:pos+size],n,k);pos+=size
        else:stream,pos=unarith_binary(frame,pos,n,k,legacy=legacy)
        raw.extend(n.to_bytes(8,'little'));raw.extend(stream)
    if pos!=len(frame):raise ValueError('trailing residual bytes')
    return header,bytes(raw),original,crc


def decode(frame):
    header,raw,original,crc=residuals(frame)
    with tempfile.TemporaryDirectory(prefix='cix-conditional-') as folder:
        folder=Path(folder);archive=folder/'input.paq8px215';errors=folder/'errors.bin';output=folder/'restored.bin'
        archive.write_bytes(header+bytes(4));errors.write_bytes(raw)
        env={k:v for k,v in os.environ.items() if k not in ('CIX_TRACE_OUT','CIX_RESIDUAL_IN')}
        env['CIX_RESIDUAL_IN']=str(errors)
        subprocess.run([str(BINARY),'-d','-simd','AVX2',str(archive),str(output)],env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        restored=output.read_bytes()
    if len(restored)!=original or zlib.crc32(restored)!=crc:raise ValueError('PAQ/CIX source checksum mismatch')
    return restored
