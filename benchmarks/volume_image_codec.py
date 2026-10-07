"""CIXV1: reversible volume layouts and inter-slice residuals with lossless JXL."""
import lzma,zlib
import numpy as np
import imagecodecs
from cix.multinomial import vencode,vdecode

MAGIC=b'CIXV\x01'


def zigzag(a):
    a=((a.astype(np.int64)+32768)&65535)-32768
    return ((a<<1)^(a>>15)).astype(np.uint16)


def unzigzag(a):
    a=a.astype(np.int64);return (a>>1)^-(a&1)


def transform(volume,mode):
    z,h,w=volume.shape
    if mode==0:return volume.reshape(z*h,w)
    if mode==1:return volume.transpose(1,0,2).reshape(h*z,w).copy()
    if mode==2:return volume.transpose(1,2,0).reshape(h,w*z).copy()
    if mode==3:return volume.copy() # planar channels
    if mode==4:
        d=volume.astype(np.int64);d[1:]-=volume[:-1].astype(np.int64)
        return zigzag(d).reshape(z*h,w)
    if mode==5:
        # Independent first-order differences along all three volume axes.
        d=volume.astype(np.int64)
        for axis in (0,1,2):d=np.diff(d,axis=axis,prepend=np.zeros_like(np.take(d,[0],axis=axis)))
        return zigzag(d).reshape(z*h,w)
    raise ValueError('unknown volume mode')


def inverse(array,shape,mode):
    z,h,w=shape
    if array.dtype not in (np.dtype('uint8'),np.dtype('uint16')) or array.size!=z*h*w:raise ValueError('invalid decoded volume')
    if mode==0:return array.reshape(shape)
    if mode==1:return array.reshape(h,z,w).transpose(1,0,2).copy()
    if mode==2:return array.reshape(h,w,z).transpose(2,0,1).copy()
    if mode==3:return array.reshape(shape)
    if mode in (4,5):
        d=unzigzag(array.reshape(shape))
        for axis in ((0,) if mode==4 else (2,1,0)):d=np.cumsum(d,axis=axis)
        return (d&65535).astype(np.uint16)
    raise ValueError('unknown volume mode')


def encode(data,region,mode=0,effort=9):
    offset,length=region['offset'],region['length'];h,w=region['slice_height'],region['width']
    if offset<0 or min(length,h,w)<=0:raise ValueError('invalid volume region')
    z=length//(h*w*2)
    if length!=z*h*w*2 or offset+length>len(data):raise ValueError('invalid volume region')
    volume=np.frombuffer(data[offset:offset+length],dtype='<u2').reshape(z,h,w)
    array=transform(volume,mode);bits=max(1,int(array.max(initial=0)).bit_length())
    if bits<=8:array=array.astype(np.uint8)
    payload=imagecodecs.jpegxl_encode(array,lossless=True,effort=effort,bitspersample=bits,numthreads=1,planar=(mode==3),photometric='GRAY')
    metadata=lzma.compress(data[:offset]+data[offset+length:],preset=9)
    fields=(len(data),offset,length,z,h,w,len(metadata),len(payload))
    return MAGIC+bytes([mode])+b''.join(vencode(x) for x in fields)+zlib.crc32(data).to_bytes(4,'big')+metadata+payload


def decode(frame):
    if frame[:5]!=MAGIC or len(frame)<6:raise ValueError('invalid volume frame')
    mode=frame[5];pos=6;fields=[]
    for _ in range(8):n,pos=vdecode(frame,pos);fields.append(n)
    original,offset,length,z,h,w,meta_size,image_size=fields
    if not z*h*w or length!=z*h*w*2 or offset+length>original or pos+4+meta_size+image_size!=len(frame):raise ValueError('volume framing mismatch')
    crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    meta=lzma.decompress(frame[pos:pos+meta_size]);pos+=meta_size
    if len(meta)!=original-length:raise ValueError('volume metadata mismatch')
    array=imagecodecs.jpegxl_decode(frame[pos:],numthreads=1)
    volume=inverse(array,(z,h,w),mode);raw=volume.astype('<u2').tobytes()
    result=meta[:offset]+raw+meta[offset:]
    if len(result)!=original or zlib.crc32(result)!=crc:raise ValueError('volume checksum mismatch')
    return result
