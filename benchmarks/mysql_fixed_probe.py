"""Complete OSDB physical measurements for fixed-field constraints."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import mysql_fixed_columns as codec
from benchmarks import mysql_record_constraints,record_float_grid


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    mode,output=spec;folder=Path(output)/str(mode);folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed experiment')
    data=Path('benchmark-work/silesia/osdb').read_bytes();paths=[m.__file__ for m in (codec,mysql_record_constraints,record_float_grid)]+['cix/multinomial.py']
    sources={str(Path(p)):sha(Path(p).read_bytes()) for p in paths};t=time.perf_counter();frame,stats=codec.encode(data,mode);enc=time.perf_counter()-t
    (folder/'stream.cixd').write_bytes(frame);t=time.perf_counter();restored=codec.decode((folder/'stream.cixd').read_bytes());dec=time.perf_counter()-t
    if data!=restored:raise ValueError('fixed-column byte restoration failed')
    for path,digest in sources.items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('source changed')
    import brotli
    row=dict(**stats,file='osdb',complete_silesia_member=True,round_trip=True,source_hashes=sources,brotli_version=brotli.__version__,
        input_sha256=sha(data),frame_sha256=sha(frame),restored_sha256=sha(restored),encode_seconds=enc,decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ['mode','physical_bytes','round_trip','encode_seconds','decode_seconds']}),flush=True);return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=2);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,[(mode,str(root)) for mode in (1,2,3,4)]))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
