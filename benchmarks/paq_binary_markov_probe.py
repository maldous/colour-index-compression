"""Complete original-input restoration through PAQ and Markov residual packets."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import time
from benchmarks import paq_binary_markov as codec
from benchmarks.competitive_codec import sha


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    parser.add_argument('--trace',default='results/leaderboard/ecoff-call-trace');args=parser.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True);folder=Path(args.trace);proof=json.loads((folder/'complete.json').read_text())
    source=(folder/'source.bin').read_bytes();trace=(folder/'predictions.u32').read_bytes();reference=(folder/'baseline.paq8px215').read_bytes()
    if (not proof['round_trip'] or not proof['trace_equals_reference'] or sha(source)!=proof['input_sha256']
        or sha(trace)!=proof['trace_sha256'] or sha(reference)!=proof['frame_sha256']):raise ValueError('unqualified original-input trace')
    paths=[Path(__file__),Path(codec.__file__),Path(codec.base.__file__),Path(codec.runmodel.__file__),Path(codec.base.BINARY),Path('cix/multinomial.py')]
    sources={str(p):sha(p.read_bytes()) for p in paths};revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=[]
    for method in (0,2,3):
        target=root/f'method{method}.cixh'
        if target.exists():raise ValueError('preserve existing Markov residual stream')
        t=time.perf_counter();frame,stats=codec.encode(trace,reference,source,method);enc=time.perf_counter()-t;target.write_bytes(frame)
        print(json.dumps(dict(method=method,encoded_bytes=len(frame),selected_markov_groups=stats['selected_markov_groups'],status='verification pending')),flush=True)
        t=time.perf_counter();restored=codec.decode(target.read_bytes());dec=time.perf_counter()-t
        if restored!=source:raise ValueError('full original PAQ/Markov restoration failed')
        if any(sha(Path(p).read_bytes())!=h for p,h in sources.items()):raise ValueError('Markov residual dependency changed')
        row=dict(stats,input_bytes=len(source),input_sha256=sha(source),restored_sha256=sha(restored),frame_sha256=sha(frame),
                 round_trip=True,encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        (root/f'method{method}.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps({k:row[k] for k in ['method','physical_bytes','delta_vs_paq_bytes','round_trip']}),flush=True)
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=True,full_silesia_member=False,
        original_input_restored=True,trace_provenance=proof,source_hashes=sources,revision=revision,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
