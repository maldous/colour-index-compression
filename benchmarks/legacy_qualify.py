"""Reproduce independent Python and existing real-frame native decoder gates."""
import random,time,json,hashlib
from pathlib import Path
from benchmarks.legacy_mixer_native import LegacyNative
from benchmarks import rounded_mixer,extended_mixer,ppm_expert_mixer
from cix.multinomial import vdecode


def main():
    n=LegacyNative();r=random.Random(61136);count=0;t=time.perf_counter()
    for module in (rounded_mixer,extended_mixer,ppm_expert_mixer):
        for data in (b'',b'x',r.randbytes(257),bytes(range(37))*21,b'abacabax'*80,bytes(r.randrange(4) for _ in range(1024))):
            for bits in (0,2,4):
                blob=module.encode(data,bits);_,pos=vdecode(blob,6)
                assert n.payload(data,bits,blob[4])==blob[pos+4:]
                assert n.decode(blob)==data
                count+=1
    out=dict(cases=count,paired_python_encoder_native_encoder=True,python_to_native_decoder=True,seconds=time.perf_counter()-t,native_source_sha256=hashlib.sha256(Path('benchmarks/native_legacy_mixer.cpp').read_bytes()).hexdigest())
    Path('results/leaderboard/legacy-native-qualification.json').write_text(json.dumps(out,indent=2)+'\n')
    rows=[]
    for path in sorted(Path('results/leaderboard/ppm-expert-scale').glob('*.Q[35]')):
        name=path.name.rsplit('.',1)[0];corpus,label=name.split('-',1);data=Path('benchmark-work',corpus,label).read_bytes()
        if label=='kennedy.xls':data=data[:262144]
        t=time.perf_counter();assert n.decode(path.read_bytes())==data
        rows.append(dict(frame=str(path),original=len(data),native_decode_seconds=time.perf_counter()-t,round_trip=True))
    assert len(rows)==6
    Path('results/leaderboard/legacy-native-real-qualification.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('54 paired small frames; 6 existing real frames verified')

if __name__=='__main__':main()
