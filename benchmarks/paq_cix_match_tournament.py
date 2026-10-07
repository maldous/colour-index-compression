"""Controlled PAQ match elimination; every candidate restores independently."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import resource
import subprocess
import time
from pathlib import Path

import numpy as np
from benchmarks import paq_cix_match as codec

ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    name,input_root,output_root=spec
    source=Path(input_root).resolve()/name;output=Path(output_root).resolve()/name
    output.mkdir(parents=True,exist_ok=True)
    if (output/'complete.json').exists():raise ValueError('preserve completed experiment')
    qualified=json.loads((source/'complete.json').read_text())
    data=(source/'prefix.bin').read_bytes();original=(source/'baseline.paq8px215').read_bytes()
    trace=(source/'predictions.u32').read_bytes()
    if (sha(data)!=qualified['input_sha256'] or sha(original)!=qualified['paq_archive_sha256']
        or sha(trace)!=qualified['trace_sha256'] or not qualified['paq_round_trip']
        or not qualified['trace_equals_reference_bitstream']):raise ValueError('unqualified baseline')
    clean_env={k:v for k,v in os.environ.items() if not k.startswith('CIX_')}

    def run(label,extra):
        archive=output/(label+'.paq8px215');trace_path=output/(label+'.u32')
        env={**clean_env,'CIX_TRACE_OUT':str(trace_path),**extra};metrics=output/(label+'.metrics')
        with (output/(label+'.log')).open('wb') as log:
            subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(metrics),str(codec.BINARY),
                qualified['paq_options'],'-simd','AVX2',str(source/'prefix.bin'),str(archive)],
                check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
        seconds,rss=metrics.read_text().split()
        if trace_path.read_bytes()!=trace:raise ValueError('PAQ probability/outcome trace changed')
        return archive.read_bytes(),dict(seconds=float(seconds),peak_rss_kib=int(rss))

    normal,normal_metrics=run('normal',{})
    if normal!=original:raise ValueError('instrumented baseline differs from ordinary PAQ')
    records_path=output/'matches.bin'
    filtered,filtered_metrics=run('filtered',{'CIX_MATCH_ENCODE':str(records_path)})
    records=records_path.read_bytes();groups,events=codec.groups_from_records(records)
    values=np.frombuffer(trace,dtype='<u4');y=values>>31;p=(values&0x7fffffff).astype(np.float64)/(1<<31)
    costs=-np.log2(np.where(y,p,1-p));forced=[]
    for position,group,token in events:
        if position*8+8>len(values):raise ValueError('match position beyond trace')
        forced.extend(range(position*8,position*8+min(8,token+1)))
    forced_bits=float(costs[forced].sum()) if forced else 0.0
    rows=[]
    for method in (0,1,2):
        start=time.perf_counter();frame,stats=codec.encode(data,filtered,records,method);enc=time.perf_counter()-start
        path=output/f'match-{method}.cixw';path.write_bytes(frame)
        start=time.perf_counter();restored=codec.decode(path.read_bytes());dec=time.perf_counter()-start
        if restored!=data:raise ValueError('match representation did not restore source exactly')
        row=dict(**stats,original_paq_bytes=len(original),delta_vs_paq_bytes=len(frame)-len(original),
            raw_event_bits=len(values),original_paq_prediction_bits=float(costs.sum()),
            eliminated_original_paq_prediction_bits=forced_bits,
            retained_original_paq_prediction_bits=float(costs.sum())-forced_bits,
            paid_token_description_bits=8*(stats['token_metadata_bytes']+stats['token_payload_bytes']),
            frame_sha256=sha(frame),round_trip=True,representation_encode_seconds=enc,decode_seconds=dec)
        path.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps(dict(file=name,method=method,paq=len(original),cix=len(frame),round_trip=True)),flush=True)
    result=dict(file=name,prefix_bytes=len(data),complete_silesia_member=False,
        paq_options=qualified['paq_options'],input_sha256=sha(data),trace_sha256=sha(trace),
        original_paq_bytes=len(original),paq_archive_sha256=sha(original),filtered_archive_sha256=sha(filtered),
        records_sha256=sha(records),trace_equals_reference_bitstream=True,
        filtered_predictions_equal_original=True,normal_encode=normal_metrics,filtered_encode=filtered_metrics,
        bridge_provenance=json.loads((codec.BINARY.parent.parent/'provenance.json').read_text()),
        codec_source_sha256=sha(Path(codec.__file__).read_bytes()),
        runner_source_sha256=sha(Path(__file__).read_bytes()),
        baseline_record_sha256=sha((source/'complete.json').read_bytes()),
        peak_process_rss_kib=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),trials=rows)
    (output/'complete.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default='results/leaderboard/paq-cix-prefix64k')
    p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--files',nargs='+',default=['xml','nci','mozilla','mr']);args=p.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,[(name,args.input,args.output) for name in args.files]))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,prefix_tournament=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
