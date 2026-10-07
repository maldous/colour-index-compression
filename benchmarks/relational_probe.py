"""Fixed diagnostic tournament, independent process jobs and native round trips."""
import concurrent.futures as cf
import hashlib,json,random,time
from pathlib import Path
from benchmarks.relational_mixer import Native


def task(item):
    name,data,bits,mode=item
    native=Native();start=time.perf_counter();frame=native.encode(data,bits,mode);enc=time.perf_counter()-start
    start=time.perf_counter();restored=native.decode(frame);dec=time.perf_counter()-start
    if restored!=data:raise ValueError('round trip failed')
    folder=Path('results/leaderboard/relational-probe');folder.mkdir(parents=True,exist_ok=True)
    label=f'{name}-b{bits}-m{mode}'
    (folder/(label+'.cixq')).write_bytes(frame)
    row=dict(case=name,size=len(frame),original=len(data),bits=bits,mode=mode,input_sha256=hashlib.sha256(data).hexdigest(),frame_sha256=hashlib.sha256(frame).hexdigest(),encode_seconds=enc,decode_seconds=dec,round_trip=True,diagnostic_only=True)
    (folder/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    r=random.Random(77261)
    cases=[('random',r.randbytes(65536)),('ramp',bytes(i&255 for i in range(65536))),('varying_delta',bytes((i*i//11)&255 for i in range(65536)))]
    for label in ('canterbury/alice29.txt','canterbury/kennedy.xls','calgary/obj2','calgary/geo','calgary/book1','canterbury/ptt5'):
        data=(Path('benchmark-work')/label).read_bytes()
        cases.append((label.replace('/','-'),data[:65536]))
    tasks=[(name,data,bits,mode) for name,data in cases for bits in (0,2) for mode in range(4)]
    start=time.perf_counter()
    with cf.ProcessPoolExecutor(6) as pool:
        rows=list(pool.map(task,tasks))
    out=dict(diagnostic_only=True,wall_seconds=time.perf_counter()-start,jobs=6,rows=rows)
    Path('results/leaderboard/relational-probe.json').write_text(json.dumps(out,indent=2)+'\n')
    for name,_ in cases:
        group=[row for row in rows if row['case']==name]
        print(name,[(mode,min(x['size'] for x in group if x['mode']==mode)) for mode in range(4)],flush=True)
    print('wall_seconds',out['wall_seconds'],flush=True)

if __name__=='__main__':main()
