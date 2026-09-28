"""Whole-group binary Markov continuation constraints on unchanged PAQ prediction errors.

Each confidence group retains its whole-group binary composition as a fallback.
The alternate uses exact alternating-run compositions; all counts, endpoints,
checksums, lengths and selection bytes are physically carried. Decoding replays
the qualified PAQ predictor without opening the prediction trace or source.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zlib
from cix.multinomial import vencode,vdecode
from benchmarks import paq_cix_residual as base,binary_markov_runs as runmodel

MAGIC=b'CIXH\x06'


def packet(stream,method):
    return runmodel.encode_group(stream,0 if method==2 else 1)[0]


def encode(trace,paq_archive,source,method=2,subbits=1):
    if method not in (0,2,3) or subbits not in range(4):raise ValueError('invalid Markov residual method')
    header_size=9 if paq_archive[7]&32 else 8;header=paq_archive[:header_size]
    if header[:6]!=b'paq8px':raise ValueError('missing PAQ header')
    groups,stats=base.partition(trace,subbits);out=bytearray(MAGIC+bytes([subbits,method,header_size])+header+vencode(len(source))+zlib.crc32(source).to_bytes(4,'big'))
    rows=[]
    for index,stream in enumerate(groups):
        n=len(stream);out.extend(vencode(n))
        if not n:continue
        k=sum(stream);incumbent=vencode(k)+base.rank_binary(stream)
        # A constant group costs only its count varint. Any Markov packet has
        # strictly greater mandatory metadata, so this pruning is exact.
        candidate=packet(stream,method) if method and k not in (0,n) else None
        selected=bool(candidate is not None and len(candidate)<len(incumbent));out.append(int(selected));out.extend(candidate if selected else incumbent)
        rows.append(dict(bucket=index,events=n,errors=k,incumbent_bytes=len(incumbent),markov_bytes=None if candidate is None else len(candidate),selected_markov=selected))
    return bytes(out),dict(stats,method=method,subbits=subbits,physical_bytes=len(out),original_paq_bytes=len(paq_archive),
                          delta_vs_paq_bytes=len(out)-len(paq_archive),groups=rows,selected_markov_groups=sum(r['selected_markov'] for r in rows))


def residuals(frame):
    if frame[:5]!=MAGIC or len(frame)<16:raise ValueError('invalid PAQ/Markov frame')
    subbits,method,header_size=frame[5:8]
    if subbits not in range(4) or method not in (0,2,3) or header_size not in (8,9):raise ValueError('invalid PAQ/Markov parameters')
    header=frame[8:8+header_size];pos=8+header_size;original,pos=vdecode(frame,pos);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    raw=bytearray(b'CIXE1'+bytes([subbits]));events=0
    for _ in range(31<<subbits):
        n,pos=vdecode(frame,pos);events+=n
        if events>1<<28:raise ValueError('residual event limit exceeded')
        stream=bytearray()
        if n:
            if pos>=len(frame):raise ValueError('missing residual selector')
            kind=frame[pos];pos+=1
            if kind==0:
                k,pos=vdecode(frame,pos)
                if k>n:raise ValueError('invalid residual composition')
                size=((math.comb(n,k)-1).bit_length()+7)//8
                stream.extend(base.unrank_binary(frame[pos:pos+size],n,k));pos+=size
            elif kind==1 and method:
                values,pos=runmodel.decode_group(frame,pos,n,0 if method==2 else 1)
                stream.extend(values)
            else:raise ValueError('invalid residual selector')
        raw.extend(n.to_bytes(8,'little'));raw.extend(stream)
    if pos!=len(frame):raise ValueError('unused PAQ/Markov bytes')
    return header,bytes(raw),original,crc


def decode(frame):
    header,raw,original,crc=residuals(frame)
    with tempfile.TemporaryDirectory(prefix='cix-markov-paq-') as folder:
        folder=Path(folder);archive=folder/'input.paq8px215';errors=folder/'errors.bin';output=folder/'restored.bin'
        archive.write_bytes(header+bytes(4));errors.write_bytes(raw)
        env={k:v for k,v in os.environ.items() if k not in ('CIX_TRACE_OUT','CIX_RESIDUAL_IN','CIX_GP_FEEDBACK')};env['CIX_RESIDUAL_IN']=str(errors)
        subprocess.run([str(base.BINARY),'-d','-simd','AVX2',str(archive),str(output)],env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        restored=output.read_bytes()
    if len(restored)!=original or zlib.crc32(restored)!=crc:raise ValueError('PAQ/Markov original checksum mismatch')
    return restored
