"""Whole-member physical tournament for reversible float-grid constraints."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import record_float_grid as codec

ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    mode,backend,offset,length,root=spec;folder=Path(root)/f'{mode}-{backend}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed tournament')
    data=(ROOT/'benchmark-work/silesia/sao').read_bytes()[offset:offset+length]
    source_hash=sha(Path(codec.__file__).read_bytes());start=time.perf_counter();frame,stats=codec.encode(data,mode,backend);enc=time.perf_counter()-start
    archive=folder/'stream.cixs';archive.write_bytes(frame);start=time.perf_counter();restored=codec.decode(archive.read_bytes());dec=time.perf_counter()-start
    if restored!=data:raise ValueError('float-grid frame did not restore every original byte')
    if sha(Path(codec.__file__).read_bytes())!=source_hash:raise ValueError('codec changed during experiment')
    import numpy,zstandard,brotli,lzma
    row=dict(**stats,file='sao',offset=offset,complete_silesia_member=offset==0 and len(data)==(ROOT/'benchmark-work/silesia/sao').stat().st_size,
        round_trip=True,encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        input_sha256=sha(data),frame_sha256=sha(frame),restored_sha256=sha(restored),codec_source_sha256=source_hash,
        numpy_version=numpy.__version__,brotli_version=brotli.__version__,zstandard_version=zstandard.__version__,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True);return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--bytes',type=int,default=7251944)
    p.add_argument('--offset',type=int,default=0);p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--pairs',nargs='+',default=['0:0','1:0','1:1','1:2','2:0','3:0']);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(*map(int,pair.split(':')),args.offset,args.bytes,str(root)) for pair in args.pairs]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
