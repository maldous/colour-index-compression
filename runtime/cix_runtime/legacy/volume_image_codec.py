"""CIXV1 reversible volume/JXL codec extracted from the historical winner."""
from __future__ import annotations
import lzma,zlib
import numpy as np
import imagecodecs
from .multinomial import vencode,vdecode
MAGIC=b"CIXV\x01"
_CODEC_OVERHEAD=64<<20
def _metadata(blob,expected,memory):
 if expected<0 or expected+_CODEC_OVERHEAD>memory:raise ValueError("volume decode memory budget")
 d=lzma.LZMADecompressor(memlimit=memory);out=d.decompress(blob,max_length=expected+1)
 if not d.eof or d.unused_data or len(out)!=expected:raise ValueError("volume metadata mismatch")
 return out
def zigzag(a): a=((a.astype(np.int64)+32768)&65535)-32768; return ((a<<1)^(a>>15)).astype(np.uint16)
def unzigzag(a): a=a.astype(np.int64); return (a>>1)^-(a&1)
def transform(v,mode):
 z,h,w=v.shape
 if mode==0:return v.reshape(z*h,w)
 if mode==1:return v.transpose(1,0,2).reshape(h*z,w).copy()
 if mode==2:return v.transpose(1,2,0).reshape(h,w*z).copy()
 if mode==3:return v.copy()
 if mode==4: d=v.astype(np.int64);d[1:]-=v[:-1].astype(np.int64);return zigzag(d).reshape(z*h,w)
 if mode==5:
  d=v.astype(np.int64)
  for axis in (0,1,2):d=np.diff(d,axis=axis,prepend=np.zeros_like(np.take(d,[0],axis=axis)))
  return zigzag(d).reshape(z*h,w)
 raise ValueError("unknown volume mode")
def inverse(a,shape,mode):
 z,h,w=shape
 if a.dtype not in (np.dtype("uint8"),np.dtype("uint16")) or a.size!=z*h*w:raise ValueError("invalid decoded volume")
 if mode==0:return a.reshape(shape)
 if mode==1:return a.reshape(h,z,w).transpose(1,0,2).copy()
 if mode==2:return a.reshape(h,w,z).transpose(2,0,1).copy()
 if mode==3:return a.reshape(shape)
 if mode in (4,5):
  d=unzigzag(a.reshape(shape))
  for axis in ((0,) if mode==4 else (2,1,0)):d=np.cumsum(d,axis=axis)
  return (d&65535).astype(np.uint16)
 raise ValueError("unknown volume mode")
def encode(data,region,mode=0,effort=9):
 off,n,h,w=(region[k] for k in ("offset","length","slice_height","width")); z=n//(h*w*2)
 if off<0 or min(n,h,w,z)<=0 or n!=z*h*w*2 or off+n>len(data):raise ValueError("invalid volume region")
 v=np.frombuffer(data[off:off+n],dtype="<u2").reshape(z,h,w); a=transform(v,mode); bits=max(1,int(a.max(initial=0)).bit_length()); a=a.astype(np.uint8 if bits<=8 else np.uint16)
 p=imagecodecs.jpegxl_encode(a,lossless=True,effort=effort,bitspersample=bits,numthreads=1,planar=(mode==3),photometric="GRAY"); m=lzma.compress(data[:off]+data[off+n:],preset=9)
 return MAGIC+bytes([mode])+b''.join(vencode(x) for x in (len(data),off,n,z,h,w,len(m),len(p)))+zlib.crc32(data).to_bytes(4,"big")+m+p
def _decode_fields(frame):
    pos=6; fields=[]
    for _ in range(8):
        value,pos=vdecode(frame,pos);fields.append(value)
    return fields, pos


def decode(frame,max_output_bytes=None,memory_bytes=None):
 if frame[:5]!=MAGIC or len(frame)<6:raise ValueError("invalid volume frame")
 mode=frame[5];f,pos=_decode_fields(frame)
 original,off,n,z,h,w,ms,ps=f
 if max_output_bytes is None or memory_bytes is None or original>max_output_bytes or original>memory_bytes:raise ValueError("output exceeds limit")
 if n<=0 or original+n+_CODEC_OVERHEAD>memory_bytes:raise ValueError("volume resource estimate exceeds limit")
 if not z*h*w or n!=z*h*w*2 or off+n>original or pos+4+ms+ps!=len(frame):raise ValueError("volume framing mismatch")
 crc=int.from_bytes(frame[pos:pos+4],"big");pos+=4;m=_metadata(frame[pos:pos+ms],original-n,memory_bytes)
 payload=frame[pos+ms:]
 # A bounded buffer lets the binding infer uint8/uint16 without allocating
 # an image from untrusted dimensions or assuming a libjxl ABI layout.
 a=imagecodecs.jpegxl_decode(payload,numthreads=1,out=bytearray(n))
 raw=inverse(a,(z,h,w),mode).astype("<u2").tobytes();out=m[:off]+raw+m[off:]
 if len(out)!=original or zlib.crc32(out)!=crc:raise ValueError("volume checksum mismatch")
 return out
