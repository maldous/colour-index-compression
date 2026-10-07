#!/usr/bin/env python3
"""CIXB1 leaf adapter for complete-file benchmark waves.

Each repetition materializes a self-contained archive, attempts the frozen
bounded portfolio, records full accounting, and retains its physical archive
for three independent archive-only decodes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def encode(source, destination, profile, policy_path, metadata):
    from cix.backend_portfolio import encode_portfolio
    source, destination = Path(source), Path(destination)
    policy = json.loads(Path(policy_path).read_text())
    work = destination.parent / 'cix-attempts'
    work.mkdir(parents=True, exist_ok=True)
    reps=[]
    warm=work/'warm.cix'
    start=time.perf_counter()
    warm_report=encode_portfolio(source,warm,profile=profile,policy=policy,
                                 attempt_directory=work/'warm-attempts')
    warm_seconds=time.perf_counter()-start
    warm.unlink(missing_ok=True)
    for i in range(3):
        archive=work/f'archive.rep{i}.cix'
        start=time.perf_counter()
        report=encode_portfolio(source,archive,profile=profile,policy=policy,
                                attempt_directory=work/f'attempts.rep{i}')
        elapsed=time.perf_counter()-start
        reps.append({'index':i,'archive':str(archive),'bytes':archive.stat().st_size,
            'sha256':sha(archive),'selected':report['selected'],
            'selection_encode_wall_seconds':report['selection_encode_wall_seconds'],
            'candidate_validation_wall_seconds':report['candidate_validation_wall_seconds'],
            'total_audit_wall_seconds':elapsed,'candidate_plan':report['candidate_plan'],
            'candidate_results':[{'name':a['name'],'status':a['status'],
                'archive_bytes':a.get('archive_bytes'),'encode_wall_seconds':a.get('wall_seconds'),
                'validation_wall_seconds':a.get('validation',{}).get('wall_seconds')}
                for a in report['attempts']],
            'maximum_direct_attempt_coverage':report['maximum_direct_attempt_coverage'],
            'policy_excluded':report['policy_excluded']})
    primary=sorted(range(3),key=lambda i:(reps[i]['bytes'],reps[i]['index']))[1]
    selected=reps[primary]
    destination.write_bytes(Path(selected['archive']).read_bytes())
    assert destination.stat().st_size==selected['bytes'] and sha(destination)==selected['sha256']
    Path(metadata).write_text(json.dumps({'warmup_seconds':warm_seconds,
        'primary_index':primary,'primary_rule':'median complete archive size, ties by index',
        'repetitions':reps},indent=2,sort_keys=True)+'\n')
    print(json.dumps({'profile':profile,'selected':selected['selected'],
        'archive_bytes':selected['bytes'],'archive_sha256':selected['sha256'],
        'maximum_direct_attempt_coverage':selected['maximum_direct_attempt_coverage']},sort_keys=True),flush=True)


def decode(archive, destination, policy_path, metadata):
    from cix.backend_portfolio import decode_archive
    record=json.loads(Path(metadata).read_text())
    policy=json.loads(Path(policy_path).read_text())
    reps=[]
    source=Path(archive)
    primary=record['repetitions'][record['primary_index']]
    if source.stat().st_size!=primary['bytes'] or sha(source)!=primary['sha256']:
        raise ValueError('the submitted CIX candidate archive does not match the frozen primary repetition')
    for rep in record['repetitions']:
        out=Path(destination).parent/f"restored.rep{rep['index']}.bin"
        start=time.perf_counter()
        result=decode_archive(source,out,policy)
        reps.append({'index':rep['index'],'decoded_bytes':out.stat().st_size,
            'decoded_sha256':sha(out),'wall_seconds':time.perf_counter()-start,
            'source_archive_sha256':sha(source),'decoder':result})
    identities={(r['decoded_bytes'],r['decoded_sha256']) for r in reps}
    assert len(identities)==1
    restored = Path(destination).parent / f"restored.rep{record['primary_index']}.bin"
    Path(destination).write_bytes(restored.read_bytes())
    print(json.dumps({'decoded_repetitions':len(reps),'decoded_bytes':reps[0]['decoded_bytes'],
        'decoded_sha256':reps[0]['decoded_sha256'],'decode_seconds_median':statistics.median(r['wall_seconds'] for r in reps)},sort_keys=True),flush=True)


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='op',required=True)
    e=sub.add_parser('encode');e.add_argument('source');e.add_argument('destination');e.add_argument('--profile',choices=['fast','current','size'],required=True);e.add_argument('--policy',required=True);e.add_argument('--metadata',required=True)
    d=sub.add_parser('decode');d.add_argument('archive');d.add_argument('destination');d.add_argument('--policy',required=True);d.add_argument('--metadata',required=True)
    a=p.parse_args()
    if a.op=='encode':encode(a.source,a.destination,a.profile,a.policy,a.metadata)
    else:decode(a.archive,a.destination,a.policy,a.metadata)


if __name__=='__main__':main()
