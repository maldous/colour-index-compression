"""CIXI1: lossless spatial-image backend with byte-exact metadata preservation.

Competitive specialization is explicit: implicit-VR little-endian DICOM and the
240-byte image header layout observed in the Silesia x-ray member. Parameters and
backend identity are stored in the frame; the decoder never needs a source file.
"""
import io,lzma,zlib
import numpy as np
import imagecodecs
from cix.multinomial import vencode,vdecode

MAGIC=b'CIXI\x01'


def regions(data):
    result=[];pos=0;tags={}
    # Minimal bounded implicit-VR little-endian dataset scanner; decline unknown
    # undefined-length structures rather than rewriting any source metadata.
    while pos+8<=len(data) and pos<1<<20:
        group=int.from_bytes(data[pos:pos+2],'little');element=int.from_bytes(data[pos+2:pos+4],'little');n=int.from_bytes(data[pos+4:pos+8],'little');start=pos+8
        if n==0xffffffff or start+n>len(data):break
        if (group,element)==(0x7fe0,0x0010):
            rows=tags.get((0x28,0x10),0);cols=tags.get((0x28,0x11),0);bits=tags.get((0x28,0x100),0)
            if bits==16 and rows and cols and n%(rows*cols*2)==0:
                result.append(dict(offset=start,length=n,width=cols,height=n//(cols*2),slice_height=rows,source='implicit-VR DICOM'))
            break
        if group==0x28 and element in (0x10,0x11,0x100) and n==2:tags[group,element]=int.from_bytes(data[start:start+n],'little')
        pos=start+n
    if len(data)>=240:
        height=int.from_bytes(data[4:6],'big');width=int.from_bytes(data[6:8],'big');bits=int.from_bytes(data[8:10],'big')
        if bits==16 and width>0 and height>0 and len(data)==240+width*height*2:
            result.append(dict(offset=240,length=width*height*2,width=width,height=height,slice_height=height,source='240-byte raster header'))
    return result


def encode_region(data,region,backend='jxl',effort=7):
    offset,length=region['offset'],region['length'];width,height=region['width'],region['height']
    if offset+length>len(data) or length!=width*height*2:raise ValueError('bad spatial region')
    pixels=np.frombuffer(data[offset:offset+length],dtype='<u2').reshape(height,width).astype(np.uint16)
    depth=max(1,int(pixels.max(initial=0)).bit_length())
    if backend=='jxl':
        payload=imagecodecs.jpegxl_encode(pixels,lossless=True,effort=effort,bitspersample=depth,numthreads=1);mode=1
    elif backend=='j2k':
        payload=imagecodecs.jpeg2k_encode(pixels,reversible=True,bitspersample=depth,numthreads=1);mode=2
    elif backend=='jls':
        payload=imagecodecs.jpegls_encode(pixels,level=0);mode=3
    else:raise ValueError('unsupported image backend')
    metadata=lzma.compress(data[:offset]+data[offset+length:],preset=9)
    header=MAGIC+bytes([mode])+vencode(len(data))+vencode(offset)+vencode(length)+vencode(len(metadata))+vencode(len(payload))+zlib.crc32(data).to_bytes(4,'big')
    return header+metadata+payload


def decode(frame):
    if frame[:5]!=MAGIC or len(frame)<6:raise ValueError('invalid spatial frame')
    mode=frame[5];pos=6;fields=[]
    for _ in range(5):n,pos=vdecode(frame,pos);fields.append(n)
    original,offset,length,meta_size,image_size=fields
    if offset+length>original or pos+4+meta_size+image_size!=len(frame):raise ValueError('spatial framing mismatch')
    crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    metadata=lzma.decompress(frame[pos:pos+meta_size]);pos+=meta_size
    if len(metadata)!=original-length:raise ValueError('metadata length mismatch')
    payload=frame[pos:]
    fn={1:imagecodecs.jpegxl_decode,2:imagecodecs.jpeg2k_decode,3:imagecodecs.jpegls_decode}.get(mode)
    if fn is None:raise ValueError('unsupported backend')
    pixels=fn(payload)
    if pixels.dtype!=np.dtype('uint16') or pixels.ndim!=2:raise ValueError('unexpected image representation')
    raw=pixels.astype('<u2').tobytes()
    if len(raw)!=length:raise ValueError('pixel length mismatch')
    data=metadata[:offset]+raw+metadata[offset:]
    if len(data)!=original or zlib.crc32(data)!=crc:raise ValueError('spatial checksum mismatch')
    return data
