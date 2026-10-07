"""Discriminating same-prediction PAQ/CIX prefix tournament, never a full rank."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import paq_cix_residual as codec

ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def worker(spec):
    name,length,root,options=spec;folder=Path(root)/name;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise ValueError('preserve completed tournament; choose another output')
    data=(ROOT/'benchmark-work/silesia'/name).read_bytes()[:length];source=folder/'prefix.bin';source.write_bytes(data)
    archive=folder/'baseline.paq8px215';traced=folder/'traced.paq8px215';trace=folder/'predictions.u32'
    reference=ROOT/'benchmark-work/references/paq8px-v215/build-local/paq8px'
    env={k:v for k,v in os.environ.items() if k not in ('CIX_TRACE_OUT','CIX_RESIDUAL_IN')}

    def run(binary,args,label,extra=None):
        start=time.perf_counter()
        with (folder/(label+'.log')).open('wb') as log:
            subprocess.run([str(binary),*args],check=True,env={**env,**(extra or {})},stdout=log,stderr=subprocess.STDOUT)
        return time.perf_counter()-start

    enc=run(reference,[options,'-simd','AVX2',str(source),str(archive)],'baseline-encode')
    trace_time=run(codec.BINARY,[options,'-simd','AVX2',str(source),str(traced)],'trace-encode',{'CIX_TRACE_OUT':str(trace)})
    original=archive.read_bytes()
    if traced.read_bytes()!=original:raise ValueError('instrumentation changed PAQ stream; predictions not equivalent')
    baseline_decoded=folder/'baseline-restored.bin'
    dec=run(reference,['-d','-simd','AVX2',str(archive),str(baseline_decoded)],'baseline-decode')
    if baseline_decoded.read_bytes()!=data:raise ValueError('PAQ baseline round trip failed')
    rows=[];trace_data=trace.read_bytes()
    for subbits in range(4):
        for method in (0,1):
            t=time.perf_counter();frame,stats=codec.encode(trace_data,original,data,subbits,method);representation_time=time.perf_counter()-t
            path=folder/f'cix-{subbits}-{method}.cixh';path.write_bytes(frame)
            t=time.perf_counter();restored=codec.decode(path.read_bytes());restore_time=time.perf_counter()-t
            if restored!=data:raise ValueError('CIX independent restoration failed')
            row=dict(**stats,round_trip=True,frame_sha256=sha(frame),representation_encode_seconds=representation_time,
                     model_trace_encode_seconds=trace_time,decode_seconds=restore_time)
            path.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
    result=dict(file=name,prefix_bytes=len(data),complete_silesia_member=False,input_sha256=sha(data),
        paq_options=options,paq_size=len(original),paq_archive_sha256=sha(original),paq_round_trip=True,
        paq_encode_seconds=enc,paq_decode_seconds=dec,trace_sha256=sha(trace_data),trace_equals_reference_bitstream=True,
        bridge_provenance=json.loads((codec.BINARY.parent.parent/'provenance.json').read_text()),
        codec_source_sha256=sha(Path(codec.__file__).read_bytes()),
        peak_process_rss_kib=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),trials=rows)
    (folder/'complete.json').write_text(json.dumps(result,indent=2)+'\n')
    best=min(rows,key=lambda r:r['physical_bytes'])
    print(json.dumps(dict(file=name,prefix_bytes=len(data),paq_bytes=len(original),best_cix_bytes=best['physical_bytes'],
        delta=best['delta_vs_paq_bytes'],best_method=best['method'],subbits=best['subbits'],all_round_trip=True)),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bytes',type=int,default=16384)
    parser.add_argument('--files',nargs='+',default=['xml','nci','mozilla','mr']);parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--options',default='-4');parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,[(name,args.bytes,str(root),args.options) for name in args.files]))
    (root/'complete.json').write_text(json.dumps(dict(prefix_tournament=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
