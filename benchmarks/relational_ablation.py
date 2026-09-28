"""Separate the relation-model contribution from the larger-window contribution."""
import concurrent.futures as cf
import hashlib,json,time,zlib
from pathlib import Path
from cix.multinomial import vencode
from benchmarks.relational_mixer import Native
from benchmarks.relational_portfolio import MAGIC,BLOCK_SIZE,decode


def sha(data):return hashlib.sha256(data).hexdigest()

def worker(item):
    name=item['corpus']+'-'+Path(item['path']).name
    data=Path(item['path']).read_bytes()
    if sha(data)!=item['sha256'] or len(data)!=item['size']:raise ValueError('input mismatch')
    folder=Path('results/leaderboard/relational-ablation');folder.mkdir(exist_ok=True)
    r7=Path('results/leaderboard/relational-tier1',name+'.cixr').read_bytes()
    r6=Path('results/leaderboard/mixer-ppm-large-tier1',name+'.cixr').read_bytes()
    native=Native();out=bytearray(MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big'))
    for start in range(0,len(data),BLOCK_SIZE):
        block=data[start:start+BLOCK_SIZE];best=b'\0'+block
        for bits in (0,2):
            trial=native.encode(block,bits,0)
            if native.decode(trial)!=block:raise ValueError('control failed')
            trial=b'\1'+trial
            if len(trial)<len(best):best=trial
        out.extend(vencode(len(best)));out.extend(best)
    frame=bytes(out) if len(out)<len(r6) else r6
    if decode(frame)!=data or decode(r7)!=data or len(r7)>len(frame):raise ValueError('ablation failed')
    (folder/(name+'.cixr')).write_bytes(frame)
    row=dict(corpus=item['corpus'],file=Path(item['path']).name,input_sha256=sha(data),incumbent_size=len(r6),larger_window_only_size=len(frame),relations_size=len(r7),additional_relation_saving=len(frame)-len(r7),round_trip=True,control_frame_sha256=sha(frame))
    (folder/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    items=json.loads(Path('results/corpus-manifest.json').read_text());t=time.perf_counter()
    with cf.ProcessPoolExecutor(4) as pool:rows=list(pool.map(worker,items))
    out=dict(complete=True,rows=rows,wall_seconds=time.perf_counter()-t)
    Path('results/leaderboard/relational-ablation.json').write_text(json.dumps(out,indent=2)+'\n')
    for corpus in ('canterbury','calgary'):
        group=[r for r in rows if r['corpus']==corpus]
        print(corpus,{k:sum(r[k] for r in group) for k in ('incumbent_size','larger_window_only_size','relations_size','additional_relation_saving')},flush=True)

if __name__=='__main__':main()
