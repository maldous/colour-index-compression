"""CIXO1: reversible image orientation selection around the spatial backend.

The six-byte outer header contains an orientation, then a complete CIXI1 frame.
Only pixel bytes are rearranged. The inner frame records region boundaries and
image dimensions; the outer decoder needs neither input filename nor source data.
"""
import numpy as np
import imagecodecs
from cix.multinomial import vdecode
from benchmarks import spatial_image_codec as spatial

MAGIC=b'CIXO\x01'


def orient(array,mode,inverse=False):
    if mode not in range(8):raise ValueError('invalid orientation')
    if inverse:
        if mode&4:array=array[:,::-1]
        if mode&2:array=array[::-1,:]
        if mode&1:array=array.T
    else:
        if mode&1:array=array.T
        if mode&2:array=array[::-1,:]
        if mode&4:array=array[:,::-1]
    return array.copy()


def encode(data,region,mode,effort=10):
    offset,length=region['offset'],region['length'];h,w=region['height'],region['width']
    if offset<0 or min(length,h,w)<=0 or length!=h*w*2 or offset+length>len(data):raise ValueError('invalid region')
    array=np.frombuffer(data[offset:offset+length],dtype='<u2').reshape(h,w)
    pixels=orient(array,mode)
    transformed=data[:offset]+pixels.astype('<u2').tobytes()+data[offset+length:]
    new_region={**region,'height':pixels.shape[0],'width':pixels.shape[1]}
    return MAGIC+bytes([mode])+spatial.encode_region(transformed,new_region,'jxl',effort)


def decode(frame):
    if len(frame)<12 or frame[:5]!=MAGIC or frame[5] not in range(8):raise ValueError('invalid orientation frame')
    inner=frame[6:]
    if inner[:6]!=spatial.MAGIC+b'\x01':raise ValueError('orientation requires JXL backend')
    # The ordinary inner decoder verifies sizes, metadata and checksum first.
    transformed=spatial.decode(inner)
    fields=[];pos=6
    for _ in range(5):n,pos=vdecode(inner,pos);fields.append(n)
    original,offset,length,meta_size,image_size=fields
    pixels=imagecodecs.jpegxl_decode(inner[pos+4+meta_size:],numthreads=1)
    raw=orient(pixels,frame[5],inverse=True).astype('<u2').tobytes()
    if len(raw)!=length:raise ValueError('orientation pixel length mismatch')
    return transformed[:offset]+raw+transformed[offset+length:]
