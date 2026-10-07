"""CIXI1 lossless spatial-image frame; extracted from the historical codec."""
from __future__ import annotations
import lzma, zlib
import numpy as np
import imagecodecs
from .multinomial import vencode, vdecode
MAGIC=b"CIXI\x01"
_CODEC_OVERHEAD=64<<20
def _metadata(blob, expected, memory):
    if expected<0 or expected+_CODEC_OVERHEAD>memory:raise ValueError("spatial decode memory budget")
    dec=lzma.LZMADecompressor(memlimit=memory)
    out=dec.decompress(blob,max_length=expected+1)
    if not dec.eof or dec.unused_data or len(out)!=expected:raise ValueError("spatial metadata mismatch")
    return out

def regions(data: bytes) -> list[dict]:
    out=[]; pos=0; tags={}
    while pos+8<=len(data) and pos<1<<20:
        g=int.from_bytes(data[pos:pos+2],'little'); e=int.from_bytes(data[pos+2:pos+4],'little'); n=int.from_bytes(data[pos+4:pos+8],'little'); start=pos+8
        if n==0xffffffff or start+n>len(data): break
        if (g,e)==(0x7fe0,0x0010):
            rows=tags.get((0x28,0x10),0); cols=tags.get((0x28,0x11),0); bits=tags.get((0x28,0x100),0)
            if bits==16 and rows and cols and n%(rows*cols*2)==0: out.append({'offset': start, 'length': n, 'width': cols, 'height': n//(cols*2), 'slice_height': rows, 'source': "implicit-VR DICOM"})
            break
        if g==0x28 and e in (0x10,0x11,0x100) and n==2: tags[g,e]=int.from_bytes(data[start:start+2],'little')
        pos=start+n
    return out

def encode_region(data, region, backend="jxl", effort=7):
    off,n,w,h=(region[k] for k in ("offset","length","width","height"))
    if off<0 or min(n,w,h)<=0 or off+n>len(data) or n!=w*h*2: raise ValueError("bad spatial region")
    p=np.frombuffer(data[off:off+n],dtype="<u2").reshape(h,w).astype(np.uint16); bits=max(1,int(p.max(initial=0)).bit_length())
    if backend=="jxl": payload=imagecodecs.jpegxl_encode(p.astype(np.uint8) if bits<=8 else p,lossless=True,effort=effort,bitspersample=bits,numthreads=1); mode=1
    elif backend=="j2k": payload=imagecodecs.jpeg2k_encode(p,reversible=True,bitspersample=bits,numthreads=1); mode=2
    elif backend=="jls": payload=imagecodecs.jpegls_encode(p,level=0); mode=3
    else: raise ValueError("unsupported image backend")
    meta=lzma.compress(data[:off]+data[off+n:],preset=9)
    return MAGIC+bytes([mode])+b''.join(vencode(x) for x in (len(data),off,n,len(meta),len(payload)))+zlib.crc32(data).to_bytes(4,"big")+meta+payload

def decode(frame,max_output_bytes=None,memory_bytes=None):
    if frame[:5]!=MAGIC or len(frame)<6: raise ValueError("invalid spatial frame")
    mode=frame[5]; pos=6; fields=[]
    for _ in range(5): x,pos=vdecode(frame,pos); fields.append(x)
    original,off,n,ms,ps=fields
    if max_output_bytes is None or memory_bytes is None or original>max_output_bytes or original>memory_bytes: raise ValueError("output exceeds limit")
    if n<=0 or n%2 or original+n+_CODEC_OVERHEAD>memory_bytes:raise ValueError("spatial resource estimate exceeds limit")
    if off+n>original or pos+4+ms+ps!=len(frame): raise ValueError("spatial framing mismatch")
    crc=int.from_bytes(frame[pos:pos+4],"big"); pos+=4; meta=_metadata(frame[pos:pos+ms],original-n,memory_bytes); p=frame[pos+ms:]
    fn={1:imagecodecs.jpegxl_decode,2:imagecodecs.jpeg2k_decode,3:imagecodecs.jpegls_decode}.get(mode)
    if fn is None: raise ValueError("invalid spatial representation")
    # CIXI1 predates dimension fields, so it cannot provide a shape for a
    # preallocated JXL output.  The paid region byte count is nevertheless
    # checked before and after decode; native workspace needs process limits.
    a=fn(p); raw=a.astype("<u2").tobytes()
    data=meta[:off]+raw+meta[off:]
    if len(raw)!=n or len(data)!=original or zlib.crc32(data)!=crc: raise ValueError("spatial checksum mismatch")
    return data
