"""Causal register-recency ranks inside exactly recoverable PAQ filter blocks.

Register identity is represented by its position in a decoder-maintained list.
Modes compare shared recency, protected fixed registers, role-specific recency,
and bounded recency resets. Every position is legal; this is predictive
canonicalization, not a claim that permutation alone reduces state count.
"""
import struct
from pathlib import Path
import subprocess
import tempfile
import zlib
import brotli
from cix.multinomial import vencode,vdecode
from benchmarks import ecoff_filtered_columns as regions, ecoff_instruction_loss as layout

parent=regions.parent
MAGIC=b'CIXB\x18';TRAILER=b'ECRG1'


def register_fields(word):
    opcode=word>>26;kind,fields=layout.schema(opcode,word);position=6
    for name,width in fields:
        # PAQ splits BSR's 21-bit target into Rb/displacement model states.
        # Its apparent Rb is part of an address, so do not rank it as a register.
        if name in ('Ra','Rb','Rc') and not (opcode==0x34 and name=='Rb'):
            floating=kind=='Fp' or (kind=='Mem' and name=='Ra' and 0x20<=opcode<=0x27)
            yield 32-position-width,kind,name,int(floating)
        position+=width


def recency(data,mode,inverse=False):
    if len(data)%4 or mode not in (1,2,3,4):raise ValueError('invalid register-recency input')
    tables={};out=bytearray()
    for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
        if mode==4 and i%256==0:tables.clear()
        for shift,kind,field,floating in register_fields(word):
            value=(word>>shift)&31
            fixed={31} if floating else {26,29,30,31}
            if mode!=1 and value in fixed:continue
            symbols=list(range(32)) if mode==1 else [r for r in range(32) if r not in fixed]
            key=(floating,kind,field) if mode==3 else (floating,)
            table=tables.setdefault(key,symbols.copy())
            if inverse:
                rank=symbols.index(value);value=table.pop(rank);encoded=value
            else:
                rank=table.index(value);encoded=symbols[rank];table.pop(rank)
            table.insert(0,value);word=(word&~(31<<shift))|(encoded<<shift)
        out.extend(word.to_bytes(4,'big'))
    return bytes(out)


def transform(stored,locations,mode):
    if mode==0:return stored
    out=bytearray(stored);metadata=bytearray(vencode(len(locations)));end=0
    for at,n in locations:
        if at<end or n<=0 or n%4 or at+n>len(out):raise ValueError('invalid register region')
        metadata.extend(vencode(at-end)+vencode(n));end=at+n;out[at:end]=recency(stored[at:end],mode)
    return bytes(out)+metadata+len(metadata).to_bytes(4,'big')+TRAILER


def inverse(raw,mode):
    if mode==0:return raw
    if len(raw)<10 or raw[-5:]!=TRAILER:raise ValueError('invalid register trailer')
    size=int.from_bytes(raw[-9:-5],'big');start=len(raw)-9-size
    if start<0:raise ValueError('invalid register metadata size')
    metadata=raw[start:-9];count,pos=vdecode(metadata,0);out=bytearray(raw[:start]);end=0
    for _ in range(count):
        delta,pos=vdecode(metadata,pos);n,pos=vdecode(metadata,pos);at=end+delta
        if n<=0 or n%4 or at+n>len(out):raise ValueError('invalid register range')
        end=at+n;out[at:end]=recency(bytes(out[at:end]),mode,True)
    if pos!=len(metadata):raise ValueError('unused register metadata')
    return bytes(out)


def encode(data,mode=2):
    if mode not in range(5):raise ValueError('invalid register rank mode')
    structural,_=parent.structure.transform(data,1)
    with tempfile.TemporaryDirectory(prefix='cix-register-rank-') as folder:
        folder=Path(folder);source=folder/'source.bin';archive=folder/'stream.paq8px216';source.write_bytes(structural)
        subprocess.run([parent.native.paq_binary('v216'),'-0','-simd','AVX2',str(source),str(archive)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        stored=archive.read_bytes()
    locations=regions.locate(structural,stored) if mode else [];raw=transform(stored,locations,mode)
    if inverse(raw,mode)!=stored:raise ValueError('register ranks failed stored archive restoration')
    frame=MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+brotli.compress(raw,quality=11,lgwin=24)
    return frame,dict(mode=mode,original_bytes=len(data),regions=len(locations),region_bytes=sum(n for _,n in locations),metadata_bytes=len(raw)-len(stored),structural_sha256=parent.native.sha(structural),native_archive_sha256=parent.native.sha(stored),backend_input_sha256=parent.native.sha(raw))


def decode(frame):
    if len(frame)<11 or frame[:5]!=MAGIC or frame[5] not in range(5):raise ValueError('invalid register rank frame')
    mode=frame[5];n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big');stored=inverse(brotli.decompress(frame[pos+4:]),mode)
    with tempfile.TemporaryDirectory(prefix='cix-register-rank-') as folder:
        folder=Path(folder);archive=folder/'stream.paq8px216';out=folder/'restored.bin';archive.write_bytes(stored)
        subprocess.run([str(parent.FORK),'-d','-simd','AVX2',str(archive),str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        data=parent.structure.inverse(out.read_bytes())
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('register rank checksum mismatch')
    return data
