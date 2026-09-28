"""Physical complete-frame tournaments for coordinate-conditioned corrections."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import record_grid_feedback as codec
from benchmarks import record_float_grid as base


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    model,mode,backend,length,root,options=spec;folder=Path(root)/f'{model}-{mode}-{backend}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed tournament')
    source=Path('benchmark-work/silesia/sao');data=source.read_bytes()[:length]
    paths=[Path(codec.__file__),Path(base.__file__)];hashes={str(p):sha(p.read_bytes()) for p in paths}
    t=time.perf_counter();frame,stats=codec.encode(data,mode,model,backend,options);enc=time.perf_counter()-t
    archive=folder/'stream.cixy';archive.write_bytes(frame);t=time.perf_counter();restored=codec.decode(archive.read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('feedback round trip mismatch')
    if hashes!={str(p):sha(p.read_bytes()) for p in paths}:raise ValueError('sources changed during tournament')
    import numpy,brotli,zstandard
    from benchmarks.competitive_codec import paq_binary
    row=dict(**stats,file='sao',offset=0,complete_silesia_member=len(data)==source.stat().st_size,round_trip=True,
        encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        input_sha256=sha(data),frame_sha256=sha(frame),restored_sha256=sha(restored),source_hashes=hashes,
        numpy_version=numpy.__version__,brotli_version=brotli.__version__,zstandard_version=zstandard.__version__,
        paq_options=options if backend==3 else None,paq_binary_sha256=sha(Path(paq_binary('v215')).read_bytes()) if backend==3 else None,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ['model','mode','backend','physical_bytes','round_trip','encode_seconds','decode_seconds']}),flush=True);return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=3)
    p.add_argument('--bytes',type=int,default=7251944);p.add_argument('--options',default='-4')
    p.add_argument('--triples',nargs='+',default=['0:1:1','0:2:1','0:3:1','1:1:1','1:2:1','1:3:1']);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(*map(int,t.split(':')),args.bytes,str(root),args.options) for t in args.triples]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
