"""Measure exact markup constraints against an independently restored PAQ baseline."""
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
from benchmarks import markup_columns as codec
from benchmarks.competitive_codec import paq_binary

ROOT=Path(__file__).resolve().parents[1]
MAGIC=b'CIXR\x01'


def sha(data):return hashlib.sha256(data).hexdigest()


def restore_paq(blob):
    with tempfile.TemporaryDirectory(prefix='cix-markup-') as folder:
        archive=Path(folder)/'stream.paq8px215';output=Path(folder)/'restored.bin';archive.write_bytes(blob)
        subprocess.run([paq_binary('v215'),'-d','-simd','AVX2',str(archive),str(output)],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return output.read_bytes()


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('invalid markup archive')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    restored=codec.decode(restore_paq(frame[pos:]))
    if len(restored)!=n or zlib.crc32(restored)!=crc:raise ValueError('markup archive checksum mismatch')
    return restored


def worker(spec):
    name,offset,length,mode,options,root=spec;folder=Path(root)/f'{name}-{offset}-{mode}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed experiment')
    data=(ROOT/'benchmark-work/silesia'/name).read_bytes()[offset:offset+length]
    source_hash=sha(Path(codec.__file__).read_bytes());start=time.perf_counter()
    if mode:transformed,stats=codec.encode(data,mode)
    else:transformed=data;stats=dict(mode=0,original_bytes=len(data),transformed_bytes=len(data))
    transform_seconds=time.perf_counter()-start
    if mode and codec.decode(transformed)!=data:raise ValueError('markup transform mismatch')
    source=folder/'input.bin';source.write_bytes(transformed);archive=folder/'stream.paq8px215';metrics=folder/'encode.metrics'
    with (folder/'encode.log').open('wb') as log:
        subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(metrics),paq_binary('v215'),options,'-simd','AVX2',str(source),str(archive)],
            check=True,stdout=log,stderr=subprocess.STDOUT)
    enc,rss=metrics.read_text().split();frame=archive.read_bytes()
    if mode:frame=MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+frame
    output=folder/('stream.cixr' if mode else 'baseline.paq8px215');output.write_bytes(frame)
    start=time.perf_counter();restored=decode(output.read_bytes()) if mode else restore_paq(output.read_bytes());dec=time.perf_counter()-start
    if restored!=data:raise ValueError('independent markup restoration failed')
    if sha(Path(codec.__file__).read_bytes())!=source_hash:raise ValueError('source changed during experiment')
    row=dict(**stats,file=name,offset=offset,complete_silesia_member=offset==0 and len(data)==(ROOT/'benchmark-work/silesia'/name).stat().st_size,
        physical_bytes=len(frame),options=options,round_trip=True,transform_seconds=transform_seconds,encode_seconds=float(enc),decode_seconds=dec,
        peak_rss_kib=max(int(rss),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        input_sha256=sha(data),transformed_sha256=sha(transformed),frame_sha256=sha(frame),codec_source_sha256=source_hash,
        backend_sha256=sha(Path(paq_binary('v215')).read_bytes()),revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True);return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--files',nargs='+',default=['xml','webster'])
    p.add_argument('--offsets',nargs='+',type=int,default=[0,1048576]);p.add_argument('--bytes',type=int,default=65536)
    p.add_argument('--modes',nargs='+',type=int,default=[0,1,3,4]);p.add_argument('--options',default='-4');p.add_argument('--jobs',type=int,default=4);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(name,offset,args.bytes,mode,args.options,str(root)) for name in args.files for offset in args.offsets for mode in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
