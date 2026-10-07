"""Local complete-member runner for the fixed bounded mixer experimental policy."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(args):
    from benchmarks.mixer_bounded import encode, decode, BLOCK_SIZE, CONTEXT_BITS
    from benchmarks.local_compare import source_digest
    item = json.loads(args.item)
    path = Path(item['path'])
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    label = item.get('corpus', 'silesia') + '-' + path.name
    frame_path = out / (label + '.cixr')
    result_path = out / (label + '.json')
    policy = dict(block_size=BLOCK_SIZE, context_bits=CONTEXT_BITS, history=0,
                  core_sha256=source_digest(ROOT),
                  encoder_sha256=digest(ROOT / 'benchmarks/mixer_bounded.py'),
                  native_source_sha256=digest(ROOT / 'benchmarks/native_contextual_mixer.cpp'),
                  native_wrapper_sha256=digest(ROOT / 'benchmarks/native_contextual_mixer.py'),
                  native_binary_sha256=digest(Path(args.native_mixer)),
                  arithmetic_source_sha256=digest(ROOT / 'benchmarks/native_ppm.cpp'),
                  frame_source_sha256=digest(ROOT / 'benchmarks/contextual_mixer.py'))
    identity = json.loads(json.dumps(dict(input_sha256=item['sha256'], original=item['size'], policy=policy)))
    if result_path.exists():
        row = json.loads(result_path.read_text())
        if (row['identity'] != identity or not row['round_trip'] or not frame_path.exists()
                or frame_path.stat().st_size != row['size'] or digest(frame_path) != row['frame_sha256']):
            raise ValueError('cached result mismatch')
        return
    data = path.read_bytes()
    if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('input manifest mismatch')
    start = time.perf_counter()
    frame = encode(data, library=args.native_mixer)
    encoded = time.perf_counter() - start
    frame_path.write_bytes(frame)
    start = time.perf_counter()
    if decode(frame) != data:
        raise ValueError('round-trip mismatch')
    row = dict(identity=identity, corpus=item.get('corpus', 'silesia'), file=path.name,
               original=len(data), size=len(frame), round_trip=True, experimental=True,
               frame_sha256=hashlib.sha256(frame).hexdigest(), encode_seconds=encoded,
               decode_seconds=time.perf_counter()-start,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               runtime=sys.version)
    temp = result_path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(row, indent=2) + '\n')
    temp.replace(result_path)
    print(json.dumps(row), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    parser.add_argument('--output', required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--native-mixer', default='results/leaderboard/native_contextual_mixer.so')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--item')
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return
    items = json.loads(Path(args.manifest).read_text())
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    def run(item):
        label = item.get('corpus', 'silesia') + '-' + Path(item['path']).name
        with (out / (label + '.log')).open('a') as log:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                '--worker', '--item', json.dumps(item), '--output', args.output,
                '--native-mixer', args.native_mixer], stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, 'OMP_NUM_THREADS': '1'})
        print(label, 'verified' if result.returncode == 0 else 'FAILED', flush=True)
        return result.returncode
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        codes = list(pool.map(run, items))
    if any(codes):
        raise SystemExit('some members failed; see per-member logs')


if __name__ == '__main__':
    main()
