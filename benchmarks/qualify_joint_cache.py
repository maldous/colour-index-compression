"""Byte-identical direct/cached composition, plus cache-integrity rejection."""
import hashlib,json,random
from pathlib import Path
from benchmarks.native_ppm import enable
from benchmarks.local_compare import source_digest
from benchmarks import ppm_bounded as ppm,joint_bounded as joint
from benchmarks.joint_cached import encode_cached


def main():
    enable();root=Path.cwd()
    def digest(path):return hashlib.sha256((root/path).read_bytes()).hexdigest()
    policy=dict(block_size=262144,orders=[3,5,7],history=65536,core_sha256=source_digest(root),
                encoder_sha256=digest('benchmarks/ppm_bounded.py'),native_source_sha256=digest('benchmarks/native_ppm.cpp'),
                native_wrapper_sha256=digest('benchmarks/native_ppm.py'),native_binary_sha256=digest('results/leaderboard/native_ppm.so'))
    rng=random.Random(438)
    cases=(b'',b'abc',random.Random(937).randbytes(1024),bytes(rng.randrange(4) for _ in range(8192)),bytes(range(37))*7200)
    rows=[]
    for data in cases:
        frame=ppm.encode(data);assert ppm.decode(frame)==data
        record=dict(identity=dict(original=len(data),input_sha256=hashlib.sha256(data).hexdigest(),policy=policy),
                    round_trip=True,size=len(frame),frame_sha256=hashlib.sha256(frame).hexdigest())
        a=joint.encode(data);b=encode_cached(data,frame,record)
        assert a==b and joint.decode(b)==data and len(b)<=len(frame)
        try:encode_cached(data,frame+b'x',record)
        except ValueError:pass
        else:raise AssertionError('changed cache accepted')
        rows.append(dict(original=len(data),size=len(b),ppm_size=len(frame),byte_identical=True,round_trip=True))
    Path('docs/research/2026-09-28-joint-cache-qualification.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(rows)


if __name__=='__main__':main()
