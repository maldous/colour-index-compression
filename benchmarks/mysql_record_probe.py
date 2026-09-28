"""Independent physical-record tournaments, with complete-source restoration."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import mysql_record_constraints as codec


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    mode,backend,offset,length,output,options=spec;folder=Path(output)/f'{offset}-{mode}-{backend}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed experiment')
    source=Path('benchmark-work/silesia/osdb');data=source.read_bytes()[offset:offset+length]
    sources={str(Path(codec.__file__)):sha(Path(codec.__file__).read_bytes()),'cix/multinomial.py':sha(Path('cix/multinomial.py').read_bytes())}
    t=time.perf_counter();frame,stats=codec.encode(data,mode,backend,options);enc=time.perf_counter()-t
    path=folder/'stream.cixd';path.write_bytes(frame);t=time.perf_counter();restored=codec.decode(path.read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('record frame failed byte-for-byte restoration')
    for p,h in sources.items():
        if sha(Path(p).read_bytes())!=h:raise ValueError('source changed during experiment')
    import brotli
    from benchmarks.competitive_codec import paq_binary
    row=dict(**stats,file='osdb',offset=offset,complete_silesia_member=offset==0 and len(data)==source.stat().st_size,
        round_trip=True,input_sha256=sha(data),frame_sha256=sha(frame),restored_sha256=sha(restored),source_hashes=sources,
        encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,brotli_version=brotli.__version__,
        paq_options=options if backend else None,paq_binary_sha256=sha(Path(paq_binary('v215')).read_bytes()) if backend else None,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ['mode','backend','offset','physical_bytes','parsed_records','round_trip','encode_seconds','decode_seconds']}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=3)
    p.add_argument('--bytes',type=int,default=65536);p.add_argument('--offset',type=int,default=0);p.add_argument('--options',default='-4')
    p.add_argument('--pairs',nargs='+',default=['0:0','1:0','2:0','3:0','4:0']);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(*map(int,pair.split(':')),args.offset,args.bytes,str(root),args.options) for pair in args.pairs]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
