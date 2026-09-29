"""Expose transmitted 16-bit rasters to PAQ's actual 8-bit image experts.

This is a reversible representation experiment. Width, height, split position,
original metadata and every sample bit are carried inside the coded stream.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import zlib
import numpy as np
from cix.multinomial import vencode,vdecode
from benchmarks import competitive_codec as paq, spatial_image_codec as spatial

RAW=b'PGMP1'
MAGIC=b'CIXB\x23'
SOURCES=[__file__,paq.__file__,spatial.__file__,str(Path(__file__).resolve().parents[1]/'cix/multinomial.py')]


def transform(data,region,shift):
    if shift==0:return RAW+b'\x00'+data
    if shift not in (4,6,8):raise ValueError('invalid pixel split')
    offset=region['offset'];w=region['width'];h=region['height'];length=w*h*2
    if min(w,h)<=0 or offset<0 or offset+length>len(data):raise ValueError('invalid raster extent')
    pixels=np.frombuffer(data[offset:offset+length],dtype='<u2')
    if pixels.max(initial=0)>>shift>255:raise ValueError('high plane exceeds eight bits')
    meta=data[:offset]+data[offset+length:]
    header=b'P5\n'+f'{w} {h}\n255\n'.encode()
    return (RAW+bytes([shift])+vencode(offset)+vencode(w)+vencode(h)+vencode(len(meta))+meta
            +header+(pixels>>shift).astype(np.uint8).tobytes()
            +header+(pixels&((1<<shift)-1)).astype(np.uint8).tobytes())


def inverse(raw):
    if len(raw)<6 or raw[:5]!=RAW:raise ValueError('invalid pixel planes')
    shift=raw[5]
    if shift==0:return raw[6:]
    if shift not in (4,6,8):raise ValueError('invalid pixel split')
    pos=6;fields=[]
    for _ in range(4):n,pos=vdecode(raw,pos);fields.append(n)
    offset,w,h,m=fields;n=w*h;header=b'P5\n'+f'{w} {h}\n255\n'.encode()
    if min(w,h)<=0 or offset>m or pos+m+2*(len(header)+n)!=len(raw):raise ValueError('invalid plane extent')
    meta=raw[pos:pos+m];pos+=m
    if raw[pos:pos+len(header)]!=header:raise ValueError('invalid high plane header')
    pos+=len(header);high=np.frombuffer(raw[pos:pos+n],dtype=np.uint8).astype(np.uint16);pos+=n
    if raw[pos:pos+len(header)]!=header:raise ValueError('invalid low plane header')
    pos+=len(header);low=np.frombuffer(raw[pos:],dtype=np.uint8).astype(np.uint16)
    if low.max(initial=0)>=(1<<shift):raise ValueError('low plane outside split alphabet')
    pixels=((high<<shift)|low).astype('<u2').tobytes()
    return meta[:offset]+pixels+meta[offset:]


def encode(data,region,shift,options):
    raw=transform(data,region,shift)
    if inverse(raw)!=data:raise ValueError('plane inversion failed')
    return MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+paq.encode_paq(raw,'v215',options),raw


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('invalid plane frame')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big');data=inverse(paq.decode(frame[pos+4:]))
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('plane checksum mismatch')
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--cpu',type=int,default=2);p.add_argument('--options',default='-4');p.add_argument('--whole',action='store_true')
    p.add_argument('--shifts',nargs='+',type=int,default=[0,4,6,8]);args=p.parse_args();os.sched_setaffinity(0,{args.cpu})
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False);source=Path('benchmark-work/silesia/x-ray');data=source.read_bytes()
    region=spatial.regions(data)[-1];w,h=region['width'],region['height'];height=64
    blocks=[(0,data,region)] if args.whole else [(y,data[region['offset']+y*w*2:region['offset']+(y+height)*w*2],dict(offset=0,width=w,height=height)) for y in (0,(h-height)//2,h-height)]
    hashes={str(Path(x).resolve()):paq.sha(Path(x).read_bytes()) for x in [*SOURCES,paq.paq_binary('v215')]}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=[]
    for y,block,r in blocks:
        for shift in args.shifts:
            folder=root/f'{y}-{shift}';folder.mkdir();t=time.perf_counter();frame,raw=encode(block,r,shift,args.options);enc=time.perf_counter()-t
            (folder/'stream.cixb').write_bytes(frame);t=time.perf_counter();restored=decode((folder/'stream.cixb').read_bytes());dec=time.perf_counter()-t
            if restored!=block or source.read_bytes()!=data:raise ValueError('plane physical restoration mismatch')
            if any(paq.sha(Path(x).read_bytes())!=v for x,v in hashes.items()):raise ValueError('plane dependencies changed')
            row=dict(row_offset=y,region=r,shift=shift,options=args.options,physical_bytes=len(frame),original_bytes=len(block),transformed_bytes=len(raw),
                input_sha256=paq.sha(block),restored_sha256=paq.sha(restored),frame_sha256=paq.sha(frame),transformed_sha256=paq.sha(raw),
                source_hashes=hashes,revision=revision,round_trip=True,complete_silesia_member=args.whole,
                encode_seconds=enc,decode_seconds=dec,numpy_version=np.__version__,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                completed_at=datetime.now(timezone.utc).isoformat())
            (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            print(json.dumps({k:row[k] for k in ('row_offset','shift','physical_bytes','round_trip')}),flush=True)
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=not args.whole,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
