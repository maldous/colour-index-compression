#!/usr/bin/env python3
"""Frozen 4 MiB structural trials, four independent CPU lanes, no holdout reads."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/research/2026-09-30-wikipedia-structure'
FOLDER = BASE / 'moderate'
MODES = ('original', 'B', 'C', 'D')
CPUS = (0, 2, 4, 6)
REGIONS = {'dev0': 0, 'dev100M': 100000000, 'dev400M': 400000000}
LENGTH = 4 * 1024 * 1024
HEADER = struct.Struct('>8sBQQI')


def immutable_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True) + '\n'
    if path.exists() and path.read_text() != content:
        raise ValueError(f'immutable file mismatch: {path}')
    path.write_text(content)


def prepare():
    template = json.loads((BASE / 'remaining-manifests/dev100M-D-cpu6.json').read_text())
    source = Path(template['input']['path'])
    jobs = []
    for region_index, (name, offset) in enumerate(REGIONS.items()):
        with source.open('rb') as stream:
            stream.seek(offset)
            data = stream.read(LENGTH)
        assert len(data) == LENGTH
        for mode_index, mode in enumerate(MODES):
            cpu = CPUS[(mode_index + region_index) % len(CPUS)]
            m = copy.deepcopy(template)
            m['stage'] = 'moderate_contiguous'
            m['longer_budget_justification'] = '4 MiB continuous PAQ encode plus independent decode tests reuse beyond tiny screens; 1200s shared maximum, no automatic restart or full-size replacement.'
            m['hypothesis'] = 'At 4 MiB, reuse of repeated structure and amortization may overcome the measured 32 KiB complete-size losses; test every unchanged candidate, not only selector winners.'
            m['mechanism'] = {'original': 'unchanged-byte PAQ control', 'B': 'order-preserving closing-tag prediction', 'C': 'shared typed streams', 'D': 'shared page skeletons, values and exceptions'}[mode]
            m['input'] = dict(path=str(source), offset=offset, length=LENGTH, sha256=hashlib.sha256(data).hexdigest())
            m['configuration'].update(mode=mode, execution_boundary=f'parent and child pinned CPU{cpu}; one lane per physical core; four jobs maximum', paq_options='-4 -simd AVX2', source_filename='candidate.source.bin', selector='NOT_RUN: every physical candidate separately reported', codec_commit='6001106e25cc1dcf86b7cbfbe67c185a7daeb04c')
            m['budget'].update(wall_seconds=1200, max_rss_bytes=3000000000, max_temp_bytes=1000000000, cpu=cpu)
            m['initial_state'] = 'empty per independent contiguous region; no training or warm-up; hashes read before all jobs so source OS cache is warm; no predictor state sharing'
            m['promotion_criteria'] = 'Exact independent restore for every reported candidate. A 16 MiB follow-up requires aggregate complete-size saving and at least 2 of 3 region wins; holdouts additionally require >=0.5% aggregate saving and a frozen candidate. Failed/budget-limited rows remain visible. No full enwik9 authorized.'
            m['build_paths'] = sorted(set(m['build_paths']) - {'benchmarks/hutter_structure_batch.py'} | {'benchmarks/hutter_structure_moderate.py'})
            m['encode_command'][m['encode_command'].index('--mode')+1] = mode
            path = FOLDER / 'manifests' / f'{name}-{mode}.json'
            immutable_json(path, m)
            jobs.append(dict(region=name, mode=mode, cpu=cpu, manifest=str(path.relative_to(ROOT))))
    immutable_json(FOLDER / 'jobs.json', jobs)


def collect():
    rows = []
    for directory in sorted((FOLDER / 'runs').glob('*')):
        receipt_path = directory / 'receipt.json'
        if not receipt_path.exists():
            receipt_path = directory / 'failed.json'
        if not receipt_path.exists():
            continue
        r = json.loads(receipt_path.read_text())
        mode = r['identity']['configuration']['mode']
        inp = r['identity']['input']
        region = next(k for k, v in REGIONS.items() if v == inp['offset'])
        row = dict(region=region, mode=mode, status=r['status'], input=inp, phases=r['phases'], verification=r['verification'], receipt=str(receipt_path.relative_to(ROOT)), experiment_id=r['experiment_id'])
        if r['status'] == 'VERIFIED_SCREENING':
            archive = Path(r['artifacts']['archive']).read_bytes()
            magic, _, original, transformed, mbytes = HEADER.unpack_from(archive)
            assert magic == b'CIXSTR1\0' and len(archive) == r['archive_bytes']
            assert hashlib.sha256(archive).hexdigest() == r['archive_sha256']
            assert hashlib.sha256(Path(r['artifacts']['restored']).read_bytes()).hexdigest() == inp['sha256']
            row.update(original_bytes=original, total_bytes=len(archive), paq_payload_bytes=len(archive)-HEADER.size-mbytes, metadata_bytes=mbytes, framing_bytes=HEADER.size, transform_bytes=transformed, transform_accounting=json.loads(archive[HEADER.size:HEADER.size+mbytes]), archive_sha256=r['archive_sha256'])
        rows.append(row)
    rows.sort(key=lambda r:(list(REGIONS).index(r['region']), MODES.index(r['mode'])))
    (FOLDER / 'completed-results.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def run_region(region):
    if shutil.disk_usage(ROOT).free < 10 * 1024**3:
        raise RuntimeError('less than 10 GiB free; no jobs launched')
    jobs = [j for j in json.loads((FOLDER / 'jobs.json').read_text()) if j['region'] == region]
    assert len(jobs) == 4 and len({j['cpu'] for j in jobs}) == 4
    active = []
    failure = False
    logs = FOLDER / 'launcher-logs'; logs.mkdir(exist_ok=True)
    try:
        for j in jobs:
            log = (logs / f'{region}-{j["mode"]}.json.log').open('a')
            command = ['taskset','-c',str(j['cpu']),sys.executable,str(ROOT/'benchmarks/hutter_bounded_runner.py'),'--manifest',str(ROOT/j['manifest']),'--results',str(FOLDER/'runs'),'--root',str(ROOT)]
            active.append((j, subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log), log))
        started = time.monotonic(); next_progress = started
        while active:
            for item in list(active):
                j, process, log = item
                if process.poll() is not None:
                    log.close(); active.remove(item)
                    failure |= process.returncode != 0
                    rows = collect()
                    result = next((r for r in rows if r['region']==region and r['mode']==j['mode']), {})
                    print(json.dumps(dict(region=region, mode=j['mode'], exit_code=process.returncode, status=result.get('status'), total_bytes=result.get('total_bytes'))), flush=True)
            if time.monotonic() >= next_progress:
                print(json.dumps(dict(region=region, elapsed_seconds=round(time.monotonic()-started,1), running=[j['mode'] for j,_,_ in active], completed_bytes='not estimated; inspect cgroup progress logs')), flush=True)
                next_progress += 30
            if active:
                time.sleep(1)
    finally:
        for _, process, log in active:
            process.terminate()
        for _, process, log in active:
            try: process.wait(timeout=20)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            log.close()
    return int(failure)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',action='store_true'); p.add_argument('--region',choices=tuple(REGIONS)); p.add_argument('--collect',action='store_true')
    a=p.parse_args()
    if a.prepare: prepare()
    if a.collect: print(json.dumps(collect()))
    return run_region(a.region) if a.region else 0

if __name__ == '__main__':
    raise SystemExit(main())
