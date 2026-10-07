"""Separate GP-load successes from a reversible filtered code skeleton.

All displacement bytes are carried, including exceptions. The first two bytes
of each instruction identify field positions and destination-register contexts.
Modes 4/5 receive identical conditional counts: exact multinomial rank versus
remaining-count arithmetic. Histogram and framing costs are always physical.
"""
import math
from pathlib import Path
import subprocess
import tempfile
import zlib
import numpy as np
import brotli
from cix import multinomial as typeclass
from cix.multinomial import vencode,vdecode
from benchmarks import ecoff_filtered_columns as regions

parent=regions.parent
MAGIC=b'CIXB\x16';TRAILER=b'ECGP2';CHUNK=256


def composition_encode(data,method):
    out=bytearray();space=0.
    for start in range(0,len(data),CHUNK):
        block=data[start:start+CHUNK];counts=typeclass._counts(block);active=[s for s,c in enumerate(counts) if c]
        out.extend(vencode(len(active)))
        for symbol in active:out.append(symbol);out.extend(vencode(counts[symbol]))
        cardinality=typeclass.multinomial_cardinality(counts);space+=math.log2(cardinality)
        if method==0:
            size=((cardinality-1).bit_length()+7)//8;out.extend(typeclass.permutation_rank(block,counts).to_bytes(size,'big'))
        else:
            payload,bits=typeclass._range_encode_type_sequence(block,counts);out.extend(vencode(bits)+payload)
    return bytes(out),space


def composition_decode(blob,pos,n,method):
    result=bytearray()
    while len(result)<n:
        length=min(CHUNK,n-len(result));m,pos=vdecode(blob,pos)
        if not 1<=m<=min(256,length):raise ValueError('invalid conditional alphabet')
        counts=[0]*256;previous=-1
        for _ in range(m):
            if pos>=len(blob):raise ValueError('truncated conditional alphabet')
            symbol=blob[pos];pos+=1;count,pos=vdecode(blob,pos)
            if symbol<=previous or not count or count>length:raise ValueError('invalid conditional counts')
            previous=symbol;counts[symbol]=count
        if sum(counts)!=length:raise ValueError('conditional count total mismatch')
        if method==0:
            cardinality=typeclass.multinomial_cardinality(counts);size=((cardinality-1).bit_length()+7)//8
            if pos+size>len(blob):raise ValueError('truncated conditional rank')
            block=typeclass.permutation_unrank(int.from_bytes(blob[pos:pos+size],'big'),counts);pos+=size
        else:
            bits,pos=vdecode(blob,pos);size=(bits+7)//8
            if bits>length*8+64 or pos+size>len(blob):raise ValueError('invalid conditional arithmetic size')
            block=typeclass._range_decode_type_sequence(blob[pos:pos+size],bits,counts);pos+=size
        result.extend(block)
    return bytes(result),pos


def fields(code):
    a=np.frombuffer(code,dtype=np.uint8).reshape(-1,4)
    mask=(a[:,0]>>2==0x29)&(a[:,1]&31==29)
    positions=np.flatnonzero(mask);registers=((a[mask,0]&3)<<3)|(a[mask,1]>>5)
    values=(a[mask,2].astype(np.uint16)<<8)|a[mask,3]
    return positions,registers,values


def residual(values,registers,mode,inverse=False):
    previous=[0]*32;out=[]
    for value,register in zip(values,registers):
        key=int(register) if mode==3 else 0;value=int(value)
        if inverse:decoded=(value+previous[key])&65535;out.append(decoded);previous[key]=decoded
        else:out.append((value-previous[key])&65535);previous[key]=value
    return np.array(out,dtype=np.uint16)


def transform(stored,locations,mode):
    if mode==0:return stored,dict(loads=0,raw_displacement_bits=0,conditional_order_bits=None,metadata_and_residual_bytes=0)
    out=bytearray(stored);metadata=bytearray(vencode(len(locations)));end=0;total=0;space=0.
    for at,n in locations:
        if at<end or n<=0 or n%4 or at+n>len(stored):raise ValueError('invalid GP region')
        metadata.extend(vencode(at-end)+vencode(n));end=at+n
        positions,registers,values=fields(stored[at:at+n]);total+=len(values)
        for where in positions:out[at+4*int(where)+2:at+4*int(where)+4]=b'\0\0'
        if mode in (2,3):values=residual(values,registers,mode)
        if mode<=3:metadata.extend((values>>8).astype(np.uint8).tobytes()+(values&255).astype(np.uint8).tobytes())
        else:
            for register in range(32):
                group=values[registers==register]
                for shift in (8,0):
                    payload,bits=composition_encode(((group>>shift)&255).astype(np.uint8).tobytes(),mode-4)
                    metadata.extend(payload);space+=bits
    raw=bytes(out)+metadata+len(metadata).to_bytes(4,'big')+TRAILER
    return raw,dict(loads=total,raw_displacement_bits=16*total,conditional_order_bits=space if mode>=4 else None,metadata_and_residual_bytes=len(raw)-len(stored))


def inverse(raw,mode):
    if mode==0:return raw
    if len(raw)<10 or raw[-5:]!=TRAILER:raise ValueError('invalid GP residual trailer')
    size=int.from_bytes(raw[-9:-5],'big');start=len(raw)-9-size
    if start<0:raise ValueError('invalid GP residual metadata size')
    metadata=raw[start:-9];count,pos=vdecode(metadata,0);out=bytearray(raw[:start]);end=0
    for _ in range(count):
        delta,pos=vdecode(metadata,pos);n,pos=vdecode(metadata,pos);at=end+delta
        if n<=0 or n%4 or at+n>len(out):raise ValueError('invalid GP residual range')
        end=at+n;positions,registers,zeros=fields(bytes(out[at:end]));number=len(positions)
        if np.any(zeros):raise ValueError('nonzero GP residual skeleton')
        if mode<=3:
            if pos+2*number>len(metadata):raise ValueError('truncated GP residual values')
            values=np.frombuffer(metadata[pos:pos+number],dtype=np.uint8).astype(np.uint16)<<8;pos+=number
            values|=np.frombuffer(metadata[pos:pos+number],dtype=np.uint8);pos+=number
            if mode in (2,3):values=residual(values,registers,mode,True)
        else:
            values=np.zeros(number,dtype=np.uint16)
            for register in range(32):
                mask=registers==register;length=int(mask.sum())
                for shift in (8,0):
                    decoded,pos=composition_decode(metadata,pos,length,mode-4)
                    values[mask]|=np.frombuffer(decoded,dtype=np.uint8).astype(np.uint16)<<shift
        for where,value in zip(positions,values):out[at+4*int(where)+2:at+4*int(where)+4]=int(value).to_bytes(2,'big')
    if pos!=len(metadata):raise ValueError('unused GP residual metadata')
    return bytes(out)


def encode(data,mode=1):
    if mode not in range(6):raise ValueError('invalid GP residual mode')
    structural,_=parent.structure.transform(data,1)
    with tempfile.TemporaryDirectory(prefix='cix-gp-residual-') as folder:
        folder=Path(folder);source=folder/'source.bin';archive=folder/'stream.paq8px216';source.write_bytes(structural)
        subprocess.run([parent.native.paq_binary('v216'),'-0','-simd','AVX2',str(source),str(archive)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        stored=archive.read_bytes()
    locations=regions.locate(structural,stored) if mode else [];raw,stats=transform(stored,locations,mode)
    if inverse(raw,mode)!=stored:raise ValueError('GP residual archive failed restoration')
    frame=MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+brotli.compress(raw,quality=11,lgwin=24)
    return frame,dict(stats,mode=mode,original_bytes=len(data),regions=len(locations),structural_sha256=parent.native.sha(structural),native_archive_sha256=parent.native.sha(stored),backend_input_sha256=parent.native.sha(raw))


def decode(frame):
    if len(frame)<11 or frame[:5]!=MAGIC or frame[5] not in range(6):raise ValueError('invalid GP residual frame')
    mode=frame[5];n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big');stored=inverse(brotli.decompress(frame[pos+4:]),mode)
    with tempfile.TemporaryDirectory(prefix='cix-gp-residual-') as folder:
        folder=Path(folder);archive=folder/'stream.paq8px216';out=folder/'restored.bin';archive.write_bytes(stored)
        subprocess.run([str(parent.FORK),'-d','-simd','AVX2',str(archive),str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        data=parent.structure.inverse(out.read_bytes())
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('GP residual checksum mismatch')
    return data
