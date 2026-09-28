"""Bounded physical tournament for exact Markov continuation constraints."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import resource
import subprocess
import time
from benchmarks import markov_euler as codec, paq_cix_residual as residual


def sha(data):return hashlib.sha256(data).hexdigest()


def fixtures():
    rng=random.Random(20260929)
    cases=[('runs-three',bytes([0])*128+bytes([1])*128+bytes([2])*128),
           ('runs-eight',b''.join(bytes([i])*64 for i in range(8))),
           ('periodic-eight',bytes(range(8))*64),
           ('iid-binary',bytes(rng.randrange(2) for _ in range(1024))),
           ('iid-eight',bytes(rng.randrange(8) for _ in range(512)))]
    values=[];state=0
    for _ in range(1024):
        if rng.randrange(32)==0:state=(state+1)%4
        values.append(state)
    cases.append(('sticky-cycle',bytes(values)))
    folder=Path('results/leaderboard/ecoff-call-trace');proof=json.loads((folder/'complete.json').read_text());trace=(folder/'predictions.u32').read_bytes()
    if not proof['round_trip'] or not proof['trace_equals_reference'] or sha(trace)!=proof['trace_sha256']:raise ValueError('unqualified PAQ residual fixture')
    groups,_=residual.partition(trace,1)
    selected=sorted((i for i,stream in enumerate(groups) if len(stream)>=2048),key=lambda i:(-len(groups[i]),i))[:4]
    for i in selected:
        for label,offset,size in [('first',0,2048),('middle',len(groups[i])//2,512)]:
            cases.append((f'paq-error-bin{i}-{label}',groups[i][offset:offset+size]))
    for name in ('mozilla','sao','osdb'):
        data=Path('benchmark-work/silesia',name).read_bytes()[65536:65792]
        cases.append((name+'-low-nibble',bytes(x&15 for x in data)))
        cases.append((name+'-high-nibble',bytes(x>>4 for x in data)))
    return cases,dict(qualified_trace_sha256=proof['trace_sha256'],source_sha256=proof['input_sha256'],
                      selection='Four longest PAQ confidence bins; fixed first/middle windows. Fixed nibble projections are residual diagnostics, not compressed original files.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    if (root/'complete.json').exists():raise ValueError('preserve existing Markov tournament')
    sources={str(Path(p)):sha(Path(p).read_bytes()) for p in [__file__,codec.__file__,residual.__file__,'cix/multinomial.py']}
    cases,provenance=fixtures();rows=[]
    for name,data in cases:
        folder=root/name;folder.mkdir(exist_ok=True);(folder/'source.bin').write_bytes(data)
        for mode in range(4):
            target=folder/f'mode{mode}.cixw'
            if target.exists():raise ValueError('preserve existing Markov frame')
            codec.cardinality.cache_clear();started=time.perf_counter();frame,stats=codec.encode(data,mode);enc=time.perf_counter()-started;target.write_bytes(frame)
            codec.cardinality.cache_clear();started=time.perf_counter();restored=codec.decode(target.read_bytes());dec=time.perf_counter()-started
            if restored!=data:raise ValueError('Markov restoration failed')
            row=dict(stats,fixture=name,round_trip=True,input_sha256=sha(data),restored_sha256=sha(restored),frame_sha256=sha(frame),encode_seconds=enc,decode_seconds=dec)
            rows.append(row);print(json.dumps({k:row[k] for k in ['fixture','mode','physical_bytes','impossible_order_bits_removed','round_trip']}),flush=True)
    if any(sha(Path(p).read_bytes())!=h for p,h in sources.items()):raise ValueError('Markov source changed')
    report=dict(complete=True,diagnostic_only=True,physical_silesia_score=False,fixture_provenance=provenance,source_hashes=sources,
                revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,rows=rows,
                interpretation='All representations transmit identical counts and endpoints. Exact trail constraints remove impossible row orders. Conditioned arithmetic receives the same valid-completion counts; any remaining rank advantage is finite framing/precision, not a new source of information.',
                references=['https://doi.org/10.1111/j.2517-6161.1955.tb00197.x','https://www.cs.purdue.edu/homes/spa/papers/aofa10.pdf'])
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
