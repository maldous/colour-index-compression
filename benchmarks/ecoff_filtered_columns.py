"""Repartition filtered instructions by byte plane, bit plane or opcode.

The transmitted PAQ archive stays independently recoverable. Region offsets and
lengths are paid metadata. Opcode-conditioned columns use the transmitted first
byte to derive each residual partition; there are no external candidate tables.
This tests representation/context separation, not an intrinsic rank advantage.
"""
import struct
from pathlib import Path
import subprocess
import tempfile
import zlib
import numpy as np
import brotli
from cix.multinomial import vencode,vdecode
from benchmarks import ecoff_filtered as parent, ecoff_constraints as objects

MAGIC=b'CIXB\x15'
TRAILER=b'ECCL1'


def shuffled(data):
    if len(data)%4:raise ValueError('unaligned instruction bytes')
    a=np.frombuffer(data,dtype='<u4').copy();op=a>>26
    mask=(a>>21)==((0x34<<5)+26)
    a[mask]=(a[mask]&~np.uint32(0x1fffff))|((a[mask]+np.arange(len(a),dtype=np.uint32)[mask])&0x1fffff)
    mask=np.isin(op,[0x14,0x15,0x16,0x17]);x=a[mask]
    a[mask]=(x&0xfc000000)|((x&0xffe0)<<10)|((x>>11)&0x7fe0)|(x&31)
    mask=op==0x18;x=a[mask];a[mask]=(x&0xfc000000)|((x&0xffff)<<10)|((x>>16)&0x3ff)
    mask=np.isin(op,[0x10,0x11,0x12,0x13,0x1c]);x=a[mask]
    a[mask]=(x&0xfc000000)|((x<<13)&0x3fc0000)|((x>>8)&0x3ffe0)|(x&31)
    return a.astype('>u4').tobytes()


def locate(structural,archive):
    found=set()
    for off,size in objects.objects(structural):
        data=structural[off:off+size];sections=objects.sections(data)
        if not all(s in sections for s in (b'.text',b'.init',b'.fini')):continue
        start,n=sections[b'.text'];i,ni=sections[b'.init'];f,nf=sections[b'.fini']
        if i!=start+n or f!=i+ni or (n+ni+nf)%4:continue
        n+=ni+nf
        if n<256:continue
        target=shuffled(data[start:start+n]);at=archive.find(target)
        # Ambiguous or undetected code remains unchanged.
        if at<0 or archive.find(target,at+1)>=0:continue
        found.add((at,n))
    result=[]
    for at,n in sorted(found):
        if not result or at>=result[-1][0]+result[-1][1]:result.append((at,n))
    return result


def columns(data,mode,inverse=False):
    if len(data)%4 or mode not in (1,2,3):raise ValueError('invalid column representation')
    n=len(data)//4
    if not n:return data
    a=np.frombuffer(data,dtype=np.uint8)
    if mode==1:
        return a.reshape((4,n) if inverse else (n,4)).T.copy().tobytes()
    if mode==2:
        count=n//8*8;size=count*4
        if not count:return data
        if inverse:
            bits=np.unpackbits(a[:size].reshape(32,count//8),axis=1).T
            body=np.packbits(bits,axis=1).tobytes()
        else:
            bits=np.unpackbits(a[:size].reshape(count,4),axis=1).T
            body=np.packbits(bits,axis=1).tobytes()
        return body+data[size:]
    if inverse:
        out=np.empty((n,4),dtype=np.uint8);out[:,0]=a[:n];keys=out[:,0]>>2;pos=n
        for key in range(64):
            mask=keys==key;count=int(mask.sum())
            if count:out[mask,1:]=a[pos:pos+3*count].reshape(3,count).T;pos+=3*count
        if pos!=len(data):raise ValueError('opcode partition length mismatch')
        return out.tobytes()
    a=a.reshape(n,4);keys=a[:,0]>>2
    return a[:,0].tobytes()+b''.join(a[keys==key,1:].T.copy().tobytes() for key in range(64))


def transform(archive,regions,mode):
    if mode==0:return archive
    out=bytearray(archive);metadata=bytearray(vencode(len(regions)));previous=0
    for at,n in regions:
        if at<previous or n<=0 or n%4 or at+n>len(out):raise ValueError('invalid filtered region')
        metadata.extend(vencode(at-previous)+vencode(n));previous=at+n
        out[at:at+n]=columns(archive[at:at+n],mode)
    return bytes(out)+metadata+len(metadata).to_bytes(4,'big')+TRAILER


def inverse(raw,mode):
    if mode==0:return raw
    if len(raw)<10 or raw[-5:]!=TRAILER:raise ValueError('invalid filtered column trailer')
    size=int.from_bytes(raw[-9:-5],'big');start=len(raw)-9-size
    if start<0:raise ValueError('invalid filtered column metadata size')
    metadata=raw[start:-9];count,pos=vdecode(metadata,0);out=bytearray(raw[:start]);previous=0
    for _ in range(count):
        delta,pos=vdecode(metadata,pos);n,pos=vdecode(metadata,pos);at=previous+delta
        if n<=0 or n%4 or at+n>len(out):raise ValueError('invalid filtered column range')
        out[at:at+n]=columns(bytes(out[at:at+n]),mode,True);previous=at+n
    if pos!=len(metadata):raise ValueError('unused filtered column metadata')
    return bytes(out)


def encode(data,mode=3):
    if mode not in range(4):raise ValueError('invalid filtered column mode')
    structural,_=parent.structure.transform(data,1)
    with tempfile.TemporaryDirectory(prefix='cix-filtered-columns-') as folder:
        folder=Path(folder);source=folder/'source.bin';archive=folder/'stream.paq8px216';source.write_bytes(structural)
        subprocess.run([parent.native.paq_binary('v216'),'-0','-simd','AVX2',str(source),str(archive)],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        stored=archive.read_bytes()
    regions=locate(structural,stored) if mode else [];raw=transform(stored,regions,mode)
    if inverse(raw,mode)!=stored:raise ValueError('filtered columns failed archive restoration')
    frame=MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+brotli.compress(raw,quality=11,lgwin=24)
    return frame,dict(mode=mode,original_bytes=len(data),regions=len(regions),region_bytes=sum(n for _,n in regions),
        metadata_bytes=len(raw)-len(stored),structural_sha256=parent.native.sha(structural),
        native_archive_sha256=parent.native.sha(stored),backend_input_sha256=parent.native.sha(raw))


def decode(frame):
    if len(frame)<11 or frame[:5]!=MAGIC or frame[5] not in range(4):raise ValueError('invalid filtered columns frame')
    mode=frame[5];n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big')
    stored=inverse(brotli.decompress(frame[pos+4:]),mode)
    with tempfile.TemporaryDirectory(prefix='cix-filtered-columns-') as folder:
        folder=Path(folder);archive=folder/'stream.paq8px216';out=folder/'restored.bin';archive.write_bytes(stored)
        subprocess.run([str(parent.FORK),'-d','-simd','AVX2',str(archive),str(out)],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        data=parent.structure.inverse(out.read_bytes())
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('filtered columns checksum mismatch')
    return data
