"""PAQ control versus CIX permutation ranks with identical geometric candidates."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import tempfile
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode,vdecode
from benchmarks import sdf_hydrogen as codec
from benchmarks.competitive_codec import paq_binary

ROOT=Path(__file__).resolve().parents[1]
MAGIC=b'CIXQ\x01'


def sha(data):return hashlib.sha256(data).hexdigest()


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('invalid hydrogen frame')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    with tempfile.TemporaryDirectory(prefix='cix-hydrogen-') as folder:
        archive=Path(folder)/'stream.paq8px215';output=Path(folder)/'restored.sdfh';archive.write_bytes(frame[pos:])
        subprocess.run([paq_binary('v215'),'-d','-simd','AVX2',str(archive),str(output)],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        restored=codec.decode(output.read_bytes())
    if len(restored)!=n or zlib.crc32(restored)!=crc:raise ValueError('hydrogen frame checksum mismatch')
    return restored


def worker(spec):
    offset,length,model,rep,options,root=spec;folder=Path(root)/f'{offset}-{model}-{rep}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed result')
    source=(ROOT/'benchmark-work/silesia/nci').read_bytes()[offset:offset+length]
    source_hash=sha(Path(codec.__file__).read_bytes())
    start=time.perf_counter();transformed,stats=codec.encode(source,model,rep);transform_seconds=time.perf_counter()-start
    if codec.decode(transformed)!=source:raise ValueError('transform failed exact restoration')
    path=folder/'input.sdfh';path.write_bytes(transformed);archive=folder/'stream.paq8px215';metrics=folder/'encode.metrics'
    with (folder/'encode.log').open('wb') as log:
        subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(metrics),paq_binary('v215'),options,'-simd','AVX2',str(path),str(archive)],
            check=True,stdout=log,stderr=subprocess.STDOUT)
    enc,rss=metrics.read_text().split();frame=MAGIC+vencode(len(source))+zlib.crc32(source).to_bytes(4,'big')+archive.read_bytes()
    (folder/'stream.cixq').write_bytes(frame)
    start=time.perf_counter();restored=decode((folder/'stream.cixq').read_bytes());dec=time.perf_counter()-start
    if restored!=source:raise ValueError('independent hydrogen frame restoration failed')
    if sha(Path(codec.__file__).read_bytes())!=source_hash:raise ValueError('codec source changed during experiment')
    result=dict(**stats,file='nci',offset=offset,complete_silesia_member=offset==0 and len(source)==(ROOT/'benchmark-work/silesia/nci').stat().st_size,
        options=options,physical_bytes=len(frame),round_trip=True,transform_seconds=transform_seconds,encode_seconds=float(enc),decode_seconds=dec,
        peak_rss_kib=max(int(rss),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        input_sha256=sha(source),transformed_sha256=sha(transformed),frame_sha256=sha(frame),codec_source_sha256=source_hash,
        backend_sha256=sha(Path(paq_binary('v215')).read_bytes()),revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--bytes',type=int,default=65536)
    p.add_argument('--offsets',nargs='+',type=int,default=[0,16776722,33487909]);p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--models',nargs='+',type=int,default=[0,1,2]);p.add_argument('--representations',nargs='+',type=int,default=[0,1])
    p.add_argument('--options',default='-4');args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(offset,args.bytes,m,r,args.options,str(root)) for offset in args.offsets for m in args.models for r in (args.representations if m==2 else [0])]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
