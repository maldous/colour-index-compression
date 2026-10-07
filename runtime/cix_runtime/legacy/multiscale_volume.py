"""CIXI2 exact multiscale volume frame (the smaller MR envelope)."""
from __future__ import annotations
import lzma,zlib
import numpy as np
import imagecodecs
from .multinomial import vencode,vdecode
MAGIC=b"CIXI\x02"
_CODEC_OVERHEAD=64<<20
def _metadata(blob,expected,memory):
 if expected<0 or expected+_CODEC_OVERHEAD>memory:raise ValueError("multiscale decode memory budget")
 d=lzma.LZMADecompressor(memlimit=memory);out=d.decompress(blob,max_length=expected+1)
 if not d.eof or d.unused_data or len(out)!=expected:raise ValueError("multiscale metadata mismatch")
 return out
def split_axis(a,axis,p):
 x=np.moveaxis(a,axis,0).astype(np.int64);lo=x[::2].copy();count=len(x)//2;pred=lo[:count]
 if p:pred=(pred+lo[np.minimum(np.arange(count)+1,len(lo)-1)])//2
 d=((x[1::2]-pred+32768)&65535)-32768;hi=((d<<1)^(d>>15)).astype(np.uint16)
 return np.moveaxis(lo.astype(np.uint16),0,axis).copy(),np.moveaxis(hi,0,axis).copy()
def join_axis(lo,hi,axis,p):
 a=np.moveaxis(lo,axis,0).astype(np.int64);h=np.moveaxis(hi,axis,0).astype(np.int64);pred=a[:len(h)]
 if p:pred=(pred+a[np.minimum(np.arange(len(h))+1,len(a)-1)])//2
 d=(h>>1)^-(h&1);out=np.empty((len(a)+len(h),*a.shape[1:]),dtype=np.uint16);out[::2]=a;out[1::2]=(pred+d)&65535
 return np.moveaxis(out,0,axis).copy()
def encode(data,region,axes=0,levels=0,predictor=0,effort=10):
 if not 0<=axes<8 or not 0<=levels<=8 or predictor not in (0,1):raise ValueError("unsupported multiscale parameters")
 off,n,h,w=(region[k] for k in ("offset","length","slice_height","width"));z,r=divmod(n,2*h*w)
 if r or min(z,h,w)<=0 or off<0 or off+n>len(data):raise ValueError("invalid volume region")
 a=np.frombuffer(data[off:off+n],dtype="<u2").reshape(z,h,w);plan=[axis for _ in range(levels) for axis in range(3) if axes&(1<<axis)];bands=[]
 def leaf(x):
  bits=max(1,int(x.max()).bit_length());x=x.astype(np.uint8 if bits<=8 else np.uint16);planar=x.shape[0]>1
  if not planar:x=x[0]
  p=imagecodecs.jpegxl_encode(x,lossless=True,effort=effort,bitspersample=bits,numthreads=1,planar=planar,photometric="GRAY");bands.append(p);return vencode(len(p))+p
 def visit(x,step):
  while step<len(plan) and x.shape[plan[step]]<2:step+=1
  if step==len(plan):return leaf(x)
  lo,hi=split_axis(x,plan[step],predictor);return visit(lo,step+1)+leaf(hi)
 m=lzma.compress(data[:off]+data[off+n:],preset=9);frame=MAGIC+bytes([axes,levels,predictor])+b''.join(vencode(x) for x in (len(data),off,z,h,w,len(m)))+zlib.crc32(data).to_bytes(4,"big")+m+visit(a,0)
 return frame,{"axes":axes,"levels":levels,"predictor":predictor,"effort":effort,"band_bytes":[len(x) for x in bands],"physical_bytes":len(frame)}


def _decode_band(frame, pos, shape):
 size,pos=vdecode(frame,pos)
 if pos+size>len(frame):raise ValueError("truncated multiscale band")
 # The binding supports ``out``; its native workspace remains subject to the
 # caller's RLIMIT_AS/cgroup, which Python cannot impose here.
 payload=frame[pos:pos+size]
 x=imagecodecs.jpegxl_decode(payload,numthreads=1,out=bytearray(2*int(np.prod(shape))))
 if x.dtype not in (np.dtype("uint8"),np.dtype("uint16")) or x.size!=np.prod(shape):raise ValueError("invalid multiscale band")
 return x.reshape(shape).astype(np.uint16),pos+size


def _decode_tree(frame, pos, plan, shape, predictor, step=0):
 while step<len(plan) and shape[plan[step]]<2:step+=1
 if step==len(plan):return _decode_band(frame,pos,shape)
 axis=plan[step];lo=list(shape);hi=list(shape);lo[axis]=(shape[axis]+1)//2;hi[axis]=shape[axis]//2
 lower,pos=_decode_tree(frame,pos,plan,tuple(lo),predictor,step+1)
 upper,pos=_decode_band(frame,pos,tuple(hi))
 return join_axis(lower,upper,axis,predictor),pos


def decode(frame,max_output_bytes=None,memory_bytes=None):
 if frame[:5]!=MAGIC or len(frame)<8:raise ValueError("invalid multiscale frame")
 axes,levels,predictor=frame[5:8]
 if axes>7 or levels>8 or predictor>1:raise ValueError("unsupported multiscale parameters")
 pos=8;f=[]
 for _ in range(6):x,pos=vdecode(frame,pos);f.append(x)
 original,off,z,h,w,ms=f;n=2*z*h*w
 if max_output_bytes is None or memory_bytes is None or original>max_output_bytes or original>memory_bytes:raise ValueError("output exceeds limit")
 if original+n+_CODEC_OVERHEAD>memory_bytes:raise ValueError("multiscale resource estimate exceeds limit")
 if not n or off+n>original or pos+4+ms>len(frame):raise ValueError("invalid multiscale dimensions")
 crc=int.from_bytes(frame[pos:pos+4],"big");pos+=4;m=_metadata(frame[pos:pos+ms],original-n,memory_bytes);pos+=ms
 plan=[axis for _ in range(levels) for axis in range(3) if axes&(1<<axis)]
 a,pos=_decode_tree(frame,pos,plan,(z,h,w),predictor)
 if pos!=len(frame):raise ValueError("trailing multiscale bytes")
 out=m[:off]+a.astype("<u2").tobytes()+m[off:]
 if len(out)!=original or zlib.crc32(out)!=crc:raise ValueError("multiscale checksum mismatch")
 return out
