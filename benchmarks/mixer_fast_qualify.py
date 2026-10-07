"""Exact native speed ablation against the separately frozen baseline binaries."""
import hashlib,json,random,time
from pathlib import Path
from benchmarks.relational_mixer import Native
from benchmarks.legacy_mixer_native import LegacyNative


def main():
    old=Native();fast=Native('results/leaderboard/native_mixer_fast.so');legacy=LegacyNative();flegacy=LegacyNative();Native.__init__(flegacy,'results/leaderboard/native_mixer_fast.so')
    r=random.Random(19271)
    cases=[('random',r.randbytes(65536)),('alice',Path('benchmark-work/canterbury/alice29.txt').read_bytes()[:65536]),('obj2',Path('benchmark-work/calgary/obj2').read_bytes()[:65536]),('rescale',b'\0'*17001)]
    rows=[]
    for name,data in cases:
        for bits in (0,2):
            for mode in range(4):
                t=time.perf_counter();a=old.encode(data,bits,mode);oe=time.perf_counter()-t
                t=time.perf_counter();b=fast.encode(data,bits,mode);fe=time.perf_counter()-t
                assert a==b
                t=time.perf_counter();assert fast.decode(b)==data;fd=time.perf_counter()-t
                rows.append(dict(case=name,mode=mode,bits=bits,old_encode_seconds=oe,fast_encode_seconds=fe,fast_decode_seconds=fd,size=len(b),round_trip=True,byte_identical=True))
        for version in (2,3,5):
            a=legacy.payload(data,2,version);b=flegacy.payload(data,2,version);assert a==b
    out=dict(complete=True,rows=rows,legacy_payload_checks=12,source_sha256=hashlib.sha256(Path('benchmarks/native_mixer_fast.cpp').read_bytes()).hexdigest())
    Path('results/leaderboard/mixer-fast-qualification.json').write_text(json.dumps(out,indent=2)+'\n')
    print('exact cases',len(rows),'legacy',12,'encode speedup',sum(r['old_encode_seconds'] for r in rows)/sum(r['fast_encode_seconds'] for r in rows),flush=True)

if __name__=='__main__':main()
