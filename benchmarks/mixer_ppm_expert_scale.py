"""Larger byte-only mixer diagnostic, never a complete-corpus score."""
import hashlib
import json
from pathlib import Path
import time


def main():
    from benchmarks import extended_mixer as old, ppm_expert_mixer as new, ppm_bounded
    from benchmarks.native_ppm import enable
    enable('results/leaderboard/native_ppm.so')
    encoders=[('Q3',old.native_encoder(),old.decode),('Q5',new.native_encoder(),new.decode),
              ('P2',lambda data,bits:ppm_bounded.encode(data),ppm_bounded.decode)]
    output=Path('results/leaderboard/ppm-expert-scale');output.mkdir(exist_ok=True)
    sources=['benchmarks/ppm_expert_mixer.py','benchmarks/native_mixer_ppm.cpp',
             'results/leaderboard/native_mixer_ppm.so','benchmarks/extended_mixer.py',
             'benchmarks/ppm_bounded.py','benchmarks/native_ppm.cpp']
    hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources}
    for case in ('canterbury/alice29.txt','canterbury/kennedy.xls','calgary/obj2'):
        whole=(Path('benchmark-work')/case).read_bytes();data=whole[:262144]
        for name,encode,decode in encoders:
            start=time.perf_counter();frame=encode(data,2);encoded=time.perf_counter()-start
            start=time.perf_counter();assert decode(frame)==data;decoded=time.perf_counter()-start
            artifact=output/(case.replace('/','-')+'.'+name);artifact.write_bytes(frame)
            row=dict(case=case,model=name,context_bits=2 if name!='P2' else None,
                     input_sha256=hashlib.sha256(data).hexdigest(),bytes_tested=len(data),
                     complete_member=len(data)==len(whole),diagnostic_only=True,size=len(frame),
                     frame_sha256=hashlib.sha256(frame).hexdigest(),round_trip=True,
                     encode_seconds=encoded,decode_seconds=decoded,source_hashes=hashes)
            artifact.with_suffix('.'+name+'.json').write_text(json.dumps(row,indent=2)+'\n')
            print(json.dumps(row),flush=True)


if __name__=='__main__':main()
