#!/usr/bin/env python3
"""Local-only paired experiment. Corpus labels never enter the encoder.

Run against two source trees with identical settings and input bytes. A bounded
probe is explicitly not a corpus score. JSONL is flushed after every completed
case; timeouts remain failures, never invented compression results.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def source_digest(root):
    source = hashlib.sha256()
    paths = sorted((Path(root) / 'cix').glob('*.py'))
    if not paths:
        raise ValueError(f'no CIX sources in {root}')
    for path in paths:
        source.update(path.name.encode() + b'\0' + path.read_bytes())
    return source.hexdigest()


def worker(args):
    sys.path.insert(0, str(Path(args.root).resolve()))
    from cix.cli import config_for_level
    from cix.multinomial import StreamEncoder, decompress

    source = source_digest(args.root)

    data = Path(args.input).read_bytes()
    if args.limit:
        data = data[:args.limit]
    config = config_for_level(args.level)
    started = time.perf_counter()
    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()
    encoded = time.perf_counter() - started
    started = time.perf_counter()
    restored = decompress(blob)
    decoded = time.perf_counter() - started
    if restored != data:
        raise RuntimeError("round-trip mismatch")
    import resource
    print(json.dumps(dict(
        original=len(data), sha256=hashlib.sha256(data).hexdigest(),
        size=len(blob), encode_seconds=encoded, decode_seconds=decoded,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        source_tree_sha256=source,
        models=encoder.block_descriptions, round_trip=True,
    )))


def compare(args, item):
    path = Path(item['path']).resolve()
    row = dict(path=str(path), corpus=item.get('corpus'), level=args.level,
               scope='prefix-probe' if args.limit else 'complete-member',
               limit=args.limit)
    for label, root in [('baseline', args.baseline), ('candidate', args.candidate)]:
        cached = args.baseline_cache.get(str(path)) if label == 'baseline' else None
        if cached and cached.get('level') == args.level and cached.get('limit') == args.limit:
            result = cached.get('baseline', {})
            data = path.read_bytes()
            if args.limit:
                data = data[:args.limit]
            if (result.get('sha256') == hashlib.sha256(data).hexdigest()
                    and result.get('source_tree_sha256') == args.baseline_source_hash):
                row[label] = result
                continue
        command = [sys.executable, str(Path(__file__).resolve()), '--worker',
                   '--root', root, '--input', str(path), '--level', str(args.level),
                   '--limit', str(args.limit)]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=args.timeout,
                                    env={**os.environ, 'OMP_NUM_THREADS': '1'})
            if result.returncode:
                row[label] = dict(error=result.stderr[-2000:])
            else:
                row[label] = json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            row[label] = dict(error='timeout', timeout_seconds=args.timeout)
    if 'size' in row['baseline'] and 'size' in row['candidate']:
        if row['baseline']['sha256'] != row['candidate']['sha256']:
            raise RuntimeError('input changed during paired comparison')
        row['saved_bytes'] = row['baseline']['size'] - row['candidate']['size']
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker', action='store_true')
    p.add_argument('--root')
    p.add_argument('--input')
    p.add_argument('--baseline')
    p.add_argument('--baseline-results', help='reuse verified same-input baseline rows')
    p.add_argument('--candidate', default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('--manifest', default='results/corpus-manifest.json')
    p.add_argument('--output', default='results/local-compare.jsonl')
    p.add_argument('--limit', type=int, default=4096,
                   help='0 for complete members; otherwise bounded prefix probes')
    p.add_argument('--level', type=int, default=3)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--timeout', type=int, default=300)
    args = p.parse_args()
    if args.worker:
        worker(args)
        return
    if not args.baseline:
        p.error('--baseline is required')
    args.baseline_cache = {}
    args.baseline_source_hash = source_digest(args.baseline)
    if args.baseline_results:
        for line in Path(args.baseline_results).read_text().splitlines():
            row = json.loads(line)
            args.baseline_cache[row['path']] = row
    items = json.loads(Path(args.manifest).read_text())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w') as out, concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        futures = [pool.submit(compare, args, item) for item in items]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            out.write(json.dumps(row) + '\n')
            out.flush()
            print(Path(row['path']).name, row.get('saved_bytes', 'FAILED'), flush=True)


if __name__ == '__main__':
    main()
