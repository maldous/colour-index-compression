"""Physical PAQ-backed geometry trial with independent framed restoration."""
import argparse
import concurrent.futures
import hashlib
import json
import lzma
import resource
import subprocess
import tempfile
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode,vdecode
from benchmarks import sdf_geometry as geometry
from benchmarks.competitive_codec import paq_binary

MAGIC=b'CIXG\x01'
ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('invalid framed geometry stream')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    with tempfile.TemporaryDirectory(prefix='cix-geometry-') as folder:
        archive=Path(folder)/'stream.paq8px215';output=Path(folder)/'restored.sdfg';archive.write_bytes(frame[pos:])
        subprocess.run([paq_binary('v215'),'-d','-simd','AVX2',str(archive),str(output)],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        restored=geometry.decode(output.read_bytes())
    if len(restored)!=n or zlib.crc32(restored)!=crc:raise ValueError('geometry source checksum mismatch')
    return restored


def worker(spec):
    name,length,offset,mode,representation,root,options=spec;folder=Path(root)/f'{mode}-{representation}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed geometry trial')
    source=(ROOT/'benchmark-work/silesia'/name).read_bytes()[offset:offset+length]
    start=time.perf_counter()
    if mode<0:transformed=source;stats=dict(mode=mode,representation=representation,original_bytes=len(source))
    else:transformed,stats=geometry.encode(source,mode,representation)
    transform_seconds=time.perf_counter()-start
    if mode>=0 and geometry.decode(transformed)!=source:raise ValueError('structural transform round trip failed')
    path=folder/'input.sdfg';path.write_bytes(transformed);archive=folder/'stream.paq8px215';metrics=folder/'encode.metrics'
    with (folder/'encode.log').open('wb') as log:
        subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(metrics),paq_binary('v215'),options,
            '-simd','AVX2',str(path),str(archive)],check=True,stdout=log,stderr=subprocess.STDOUT)
    enc,rss=metrics.read_text().split();frame=archive.read_bytes()
    if mode>=0:frame=MAGIC+vencode(len(source))+zlib.crc32(source).to_bytes(4,'big')+frame
    (folder/'stream.cixg').write_bytes(frame)
    start=time.perf_counter()
    if mode<0:
        output=folder/'restored.bin'
        subprocess.run([paq_binary('v215'),'-d','-simd','AVX2',str(archive),str(output)],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        restored=output.read_bytes()
    else:restored=decode((folder/'stream.cixg').read_bytes())
    dec=time.perf_counter()-start
    if restored!=source:raise ValueError('complete geometry frame round trip failed')
    result=dict(**stats,file=name,offset=offset,complete_silesia_member=offset==0 and len(source)==(ROOT/'benchmark-work/silesia'/name).stat().st_size,options=options,
        physical_bytes=len(frame),round_trip=True,transform_seconds=transform_seconds,encode_seconds=float(enc),
        decode_seconds=dec,peak_rss_kib=max(int(rss),resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        input_sha256=sha(source),transformed_sha256=sha(transformed),frame_sha256=sha(frame),
        codec_source_sha256=sha(Path(geometry.__file__).read_bytes()),
        backend_sha256=sha(Path(paq_binary('v215')).read_bytes()),
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--bytes',type=int,default=65536)
    p.add_argument('--offset',type=int,default=0);p.add_argument('--jobs',type=int,default=3);p.add_argument('--options',default='-4')
    p.add_argument('--modes',nargs='+',type=int,default=[2]);p.add_argument('--representations',nargs='+',type=int,default=[0,1,2]);p.add_argument('--baseline',action='store_true');args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:
        specs=[('nci',args.bytes,args.offset,m,r,str(root),args.options) for m in args.modes for r in args.representations]
        if args.baseline:specs.insert(0,('nci',args.bytes,args.offset,-1,-1,str(root),args.options))
        rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
