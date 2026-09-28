"""Frozen 29-member prerequisite experiment with hash-qualified R6 cache."""
import concurrent.futures as cf
import hashlib,json,time
from pathlib import Path
from benchmarks.relational_portfolio import encode,decode,BLOCK_SIZE,BITS,MODES

FOLDER=Path('results/leaderboard/relational-tier1')
CACHE=Path('results/leaderboard/mixer-ppm-large-tier1')

def sha(data):return hashlib.sha256(data).hexdigest()

def worker(item):
    name=item['corpus']+'-'+Path(item['path']).name
    data=Path(item['path']).read_bytes()
    if len(data)!=item['size'] or sha(data)!=item['sha256']:raise ValueError('input mismatch')
    row=json.loads((CACHE/(name+'.json')).read_text());incumbent=(CACHE/(name+'.cixr')).read_bytes()
    policy=row['identity']['policy']
    if (row['identity']['input_sha256']!=sha(data) or not row['round_trip'] or len(incumbent)!=row['size'] or sha(incumbent)!=row['frame_sha256'] or policy['block_size']!=262144 or policy['models']!=[2,3,5] or policy['context_bits']!=[0,2] or policy['encoder_sha256']!=sha(Path('benchmarks/mixer_ppm_large.py').read_bytes())):raise ValueError('cache mismatch')
    if decode(incumbent)!=data:raise ValueError('incumbent failed fresh decode')
    t=time.perf_counter();frame=encode(data,incumbent=incumbent);enc=time.perf_counter()-t
    t=time.perf_counter();restored=decode(frame);dec=time.perf_counter()-t
    if restored!=data or len(frame)>len(incumbent):raise ValueError('verification failed')
    (FOLDER/(name+'.cixr')).write_bytes(frame)
    result=dict(corpus=item['corpus'],file=Path(item['path']).name,original=len(data),input_sha256=sha(data),size=len(frame),incumbent_size=len(incumbent),frame_sha256=sha(frame),round_trip=True,encode_seconds=enc,decode_seconds=dec,magic=frame[:5].hex(),policy=dict(block_size=BLOCK_SIZE,bits=BITS,modes=MODES,encoder_sha256=sha(Path('benchmarks/relational_portfolio.py').read_bytes()),model_source_sha256=sha(Path('benchmarks/native_relational_mixer.cpp').read_bytes()),model_binary_sha256=sha(Path('results/leaderboard/native_relational_mixer.so').read_bytes())),incumbent_policy=policy)
    (FOLDER/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    FOLDER.mkdir(parents=True,exist_ok=True)
    items=json.loads(Path('results/corpus-manifest.json').read_text())
    assert len(items)==29
    t=time.perf_counter();rows=[]
    with cf.ProcessPoolExecutor(6) as pool:
        for row in pool.map(worker,items):
            rows.append(row);print(row['corpus'],row['file'],row['incumbent_size'],'->',row['size'],flush=True)
    report=dict(complete=True,members=29,jobs=6,wall_seconds=time.perf_counter()-t,rows=rows)
    Path('results/leaderboard/relational-tier1.json').write_text(json.dumps(report,indent=2)+'\n')
    for corpus in ('canterbury','calgary'):
        group=[r for r in rows if r['corpus']==corpus]
        print(corpus,sum(r['incumbent_size'] for r in group),'->',sum(r['size'] for r in group),flush=True)

if __name__=='__main__':main()
