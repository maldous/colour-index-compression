"""Finish verification of existing joint artifacts using qualified native mixers.

Does not change or write the running cohort; records the alternate decoder and
unavailable encode timing explicitly in a separate complete evidence directory.
"""
import hashlib,json,shutil,time
from pathlib import Path
from benchmarks.legacy_mixer_native import enable
from benchmarks.joint_parallel_decode import decode
from benchmarks.joint_position import report


def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    enable()
    src=Path('results/leaderboard/joint-silesia');out=Path('results/leaderboard/joint-parallel-verified');out.mkdir(exist_ok=True)
    items=json.loads(Path('results/silesia-manifest.json').read_text())
    oldrows=[json.loads(p.read_text()) for p in src.glob('*.json')]
    policies={json.dumps(r['identity']['policy'],sort_keys=True) for r in oldrows}
    if len(policies)!=1:raise ValueError('mixed encoder policies')
    policy=json.loads(policies.pop())
    for item in items:
        path=Path(item['path']);label='silesia-'+path.name
        blob=(src/(label+'.cixt')).read_bytes();rp=src/(label+'.json')
        if rp.exists():
            row=json.loads(rp.read_text())
            if not row['round_trip'] or row['identity']['input_sha256']!=item['sha256'] or sha(blob)!=row['frame_sha256']:raise ValueError('existing evidence mismatch')
        else:
            data=path.read_bytes()
            if len(data)!=item['size'] or sha(data)!=item['sha256']:raise ValueError('corpus mismatch')
            start=time.perf_counter();restored=decode(blob);seconds=time.perf_counter()-start
            if restored!=data:raise ValueError('fresh decode failed')
            if (src/(label+'.cixt')).read_bytes()!=blob:raise ValueError('artifact changed during verification')
            row=dict(identity=dict(input_sha256=item['sha256'],original=len(data),policy=policy),corpus='silesia',file=path.name,original=len(data),size=len(blob),round_trip=True,experimental=True,frame_sha256=sha(blob),encode_seconds=None,decode_seconds=seconds,verification=dict(method='dependency-aware four-process decoder; qualified native Q2; independent Python PPM',native_source_sha256=sha(Path('benchmarks/native_legacy_mixer.cpp').read_bytes()),native_binary_sha256=sha(Path('results/leaderboard/native_legacy_mixer.so').read_bytes()),qualification='results/leaderboard/legacy-native-qualification.json',parallel_decoder_sha256=sha(Path('benchmarks/joint_parallel_decode.py').read_bytes()),encoding_provenance='existing completed physical artifact from joint_cached_run; original Python decoder still running'))
        (out/(label+'.cixt')).write_bytes(blob)
        (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
        print(label,'verified',len(blob),flush=True)
    result=report('results/leaderboard/published.json',out,'benchmark-work/silesia')
    Path('results/leaderboard/joint-parallel-position.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['position']),flush=True)

if __name__=='__main__':main()
