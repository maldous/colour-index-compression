"""Locally verify every complete bounded-grid candidate and its provenance."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import record_grid_integer as codec
from benchmarks import record_grid_feedback,record_float_grid


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    policy,block,root=spec;folder=Path(root)/f'{policy}-{block}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed experiment')
    data=Path('benchmark-work/silesia/sao').read_bytes()
    paths=[Path(m.__file__) for m in (codec,record_grid_feedback,record_float_grid)]
    hashes={str(p):sha(p.read_bytes()) for p in paths}
    t=time.perf_counter();frame,stats=codec.encode(data,policy,block);enc=time.perf_counter()-t
    archive=folder/'stream.cixi';archive.write_bytes(frame);t=time.perf_counter();restored=codec.decode(archive.read_bytes());dec=time.perf_counter()-t
    if data!=restored:raise ValueError('bounded-grid round trip mismatch')
    if hashes!={str(p):sha(p.read_bytes()) for p in paths}:raise ValueError('source changed during experiment')
    import numpy,brotli
    row=dict(**stats,file='sao',complete_silesia_member=True,round_trip=True,encode_seconds=enc,decode_seconds=dec,
        input_sha256=sha(data),frame_sha256=sha(frame),restored_sha256=sha(restored),source_hashes=hashes,
        numpy_version=numpy.__version__,brotli_version=brotli.__version__,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ['policy','block','physical_bytes','round_trip','encode_seconds','decode_seconds']}),flush=True);return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=3)
    p.add_argument('--pairs',nargs='+',default=['1:256','2:256','3:256']);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(*map(int,p.split(':')),str(root)) for p in args.pairs]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
