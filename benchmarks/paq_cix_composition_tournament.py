"""Reuse qualified PAQ traces; independently restore every count/rank candidate."""
import argparse
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import paq_cix_composition as codec


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    name,input_root,output_root=spec;source=Path(input_root)/name;output=Path(output_root)/name;output.mkdir(parents=True,exist_ok=True)
    if (output/'complete.json').exists():raise ValueError('completed experiment already exists')
    qualified=json.loads((source/'complete.json').read_text());trace=(source/'predictions.u32').read_bytes()
    data=(source/'prefix.bin').read_bytes();paq=(source/'baseline.paq8px215').read_bytes()
    if (sha(trace)!=qualified['trace_sha256'] or sha(data)!=qualified['input_sha256']
        or sha(paq)!=qualified['paq_archive_sha256'] or not qualified['trace_equals_reference_bitstream']
        or not qualified['paq_round_trip']):raise ValueError('unqualified original prediction cache')
    rows=[]
    for block_size in (16,64,256):
        for mode in (0,1,2):
            start=time.perf_counter();frame,stats=codec.encode(trace,paq,data,block_size=block_size,mode=mode);enc=time.perf_counter()-start
            path=output/f'count-{block_size}-{mode}.cixh';path.write_bytes(frame)
            start=time.perf_counter();restored=codec.decode(path.read_bytes());dec=time.perf_counter()-start
            if restored!=data:raise ValueError('independent PAQ reconstruction failed')
            row=dict(**stats,frame_sha256=sha(frame),round_trip=True,encode_seconds=enc,decode_seconds=dec)
            path.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            print(json.dumps(dict(file=name,block=block_size,model=mode,size=len(frame),paq=len(paq),round_trip=True)),flush=True)
    result=dict(file=name,prefix_bytes=len(data),complete_silesia_member=False,paq_options=qualified['paq_options'],
        input_sha256=sha(data),trace_sha256=sha(trace),original_paq_bytes=len(paq),trials=rows,
        trace_equals_reference_bitstream=True,baseline_record_sha256=sha((source/'complete.json').read_bytes()),
        bridge_provenance=qualified['bridge_provenance'],codec_source_sha256=sha(Path(codec.__file__).read_bytes()),
        peak_process_rss_kib=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (output/'complete.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',default='results/leaderboard/paq-cix-prefix64k');p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=4);args=p.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,[(name,args.input,args.output) for name in ('xml','nci','mozilla','mr')]))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,prefix_tournament=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
