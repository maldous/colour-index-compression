"""Prepare immutable CPI1 assets and run only inside the owning scheduler lease."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
BASE = ROOT / 'benchmark-work/predictive-information'
SOURCE = ROOT / 'rust/cix-native/experiments/predictive-information/trace.rs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def prepare():
    assert not (AREA / 'freeze.json').exists()
    for directory in ['source', 'inputs', 'traces', 'build']:
        (BASE / directory).mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ['adaptive', 'ppm', 'expertmix', 'fixedmix', 'zpaq_context', 'rank', 'limits', 'combinatorics']:
        original = subprocess.check_output(['git', 'show', f'd3a2cd416:rust/cix-native/src/{name}.rs'], cwd=ROOT)
        path = BASE / 'source' / (name + '.rs')
        path.write_bytes(b'\n'.join(b'//' + line[3:] if line.startswith(b'//!') else line for line in original.split(b'\n')))
        hashes[str(path.relative_to(ROOT))] = sha(path)
        hashes['git:d3a2cd416:' + name] = hashlib.sha256(original).hexdigest()
    registry = json.loads((ROOT / 'docs/research/2026-09-30-generic-pipeline/inputs.json').read_text())
    records = []
    for family in ['canterbury', 'calgary', 'artificial']:
        members = sorted([item for item in registry if item['stratum'] == 'generic-regression' and item['label'].startswith(family + '-')], key=lambda item: item['label'])
        for ordinal, item in enumerate(members):
            source = Path(item['path'])
            original_hash = sha(source)
            with source.open('rb') as stream:
                stream.seek(item.get('offset', 0))
                data = stream.read(min(4096, item['length']))
            target = BASE / 'inputs' / (item['label'] + '.bin')
            target.write_bytes(data)
            records.append(dict(label=item['label'], family=family, split='development' if ordinal % 2 == 0 else 'heldout',
                                source=str(source), source_sha256=original_hash, registry_sha256=item['sha256'], offset=item.get('offset', 0),
                                bytes=len(data), sha256=sha(target), path=str(target)))
    assert len(records) == 33
    write(AREA / 'inputs.json', records)
    for path in [SOURCE, AREA / 'PLAN.md', AREA / 'INVENTORY.md', AREA / 'analyse.py', AREA / 'run.py', AREA / 'schedule.py', AREA / 'inputs.json']:
        hashes[str(path.relative_to(ROOT))] = sha(path)
    write(AREA / 'freeze.json', dict(identity='CPI1', checkpoint='20e18503b', incumbent='d3a2cd416',
          utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), hashes=hashes,
          source_rewrite='Only leading //! documentation becomes // for include!; original hashes retained.',
          split_bytes={split: sum(row['bytes'] for row in records if row['split'] == split) for split in ['development', 'heldout']}))


def trace_split(split):
    assert os.environ.get('CIX_PREDICTIVE_LEASE') == '1'
    if split == 'heldout':
        assert (AREA / 'trained.json').exists()
    binary = BASE / 'build/trace'
    if (AREA / 'binary.json').exists():
        assert sha(binary) == json.loads((AREA / 'binary.json').read_text())['sha256']
    else:
        write(AREA / 'binary.json', dict(path=str(binary), sha256=sha(binary)))
    records = json.loads((AREA / 'inputs.json').read_text())
    receipts = []
    for row in records:
        if row['split'] != split:
            continue
        assert sha(Path(row['path'])) == row['sha256']
        output = BASE / 'traces' / (row['label'] + '.tsv')
        assert not output.exists() and not output.with_suffix('.tsv.gz').exists(), 'immutable trial already exists'
        timing = AREA / 'raw' / (row['label'] + '.time')
        started = time.monotonic()
        subprocess.run(['/usr/bin/time', '-v', '-o', str(timing), str(binary), row['path'], str(output)], check=True, timeout=300)
        target = output.with_suffix('.tsv.gz')
        with output.open('rb') as source, gzip.open(target, 'wb', compresslevel=1) as compressed:
            shutil.copyfileobj(source, compressed)
        output.unlink()
        receipts.append(dict(label=row['label'], trace_sha256=sha(target), summary_sha256=sha(Path(str(output) + '.summary.tsv')),
                             wall_seconds=time.monotonic() - started, compressed_trace_bytes=target.stat().st_size))
        write(AREA / (split + '-receipts.json'), receipts)
        print(json.dumps(receipts[-1]), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'development', 'heldout'])
    args = parser.parse_args()
    prepare() if args.phase == 'prepare' else trace_split(args.phase)
