"""Reproduce the fixed 253,952-byte exploratory call-target trace.

Choose a fresh output directory before rerunning: completed traces are preserved.
"""
import os, json, time, hashlib, subprocess, resource, argparse
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    source=out/'source.bin';data=(root/'benchmark-work/silesia/mozilla').read_bytes()[43270656:43270656+253952];source.write_bytes(data)
    ref=root/'benchmark-work/references/paq8px-v215/build-local/paq8px';bridge=root/'benchmark-work/references/paq8px-cix-bridge/build-local/paq8px'
    sha=lambda b:hashlib.sha256(b).hexdigest()
    hashes={str(p):sha(p.read_bytes()) for p in (ref,bridge,Path(__file__))}
    env={k:v for k,v in os.environ.items() if k not in ('CIX_TRACE_OUT','CIX_RESIDUAL_IN')};times={}
    for label,binary,args,extra in [('trace',bridge,['-4','-simd','AVX2',str(source),str(out/'traced.paq8px215')],{'CIX_TRACE_OUT':str(out/'predictions.u32')}),('reference',ref,['-4','-simd','AVX2',str(source),str(out/'baseline.paq8px215')],{}),('decode',ref,['-d','-simd','AVX2',str(out/'baseline.paq8px215'),str(out/'restored.bin')],{})]:
        if label!='decode' and Path(args[-1]).exists():raise ValueError('preserve existing trial')
        t=time.perf_counter()
        with (out/(label+'.log')).open('wb') as f:subprocess.run([str(binary),*args],check=True,stdout=f,stderr=subprocess.STDOUT,env={**env,**extra})
        times[label]=time.perf_counter()-t;print(label,times[label],flush=True)
    assert (out/'restored.bin').read_bytes()==data
    assert (out/'baseline.paq8px215').read_bytes()==(out/'traced.paq8px215').read_bytes()
    assert all(sha(Path(p).read_bytes())==h for p,h in hashes.items())
    result=dict(complete=True,diagnostic_only=True,offset=43270656,bytes=len(data),input_sha256=sha(data),physical_paq_bytes=(out/'baseline.paq8px215').stat().st_size,frame_sha256=sha((out/'baseline.paq8px215').read_bytes()),round_trip=True,trace_equals_reference=True,trace_sha256=sha((out/'predictions.u32').read_bytes()),binary_hashes=hashes,times=times,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip())
    (out/'complete.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
