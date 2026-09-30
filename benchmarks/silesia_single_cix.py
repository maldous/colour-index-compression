#!/usr/bin/env python3
"""Single-archive adapter for complete Silesia CIX portfolio trials."""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='op',required=True)
    e=s.add_parser('encode');e.add_argument('source',type=Path);e.add_argument('archive',type=Path);e.add_argument('--profile',choices=['fast','current','size'],required=True);e.add_argument('--policy',type=Path,required=True);e.add_argument('--attempts',type=Path,required=True)
    d=s.add_parser('decode');d.add_argument('archive',type=Path);d.add_argument('restored',type=Path);d.add_argument('--policy',type=Path,required=True)
    a=p.parse_args();policy=json.loads(a.policy.read_text())
    from cix.backend_portfolio import decode_archive, encode_portfolio
    if a.op=='encode':
        report=encode_portfolio(a.source,a.archive,profile=a.profile,policy=policy,attempt_directory=a.attempts)
        result={'archive_bytes':a.archive.stat().st_size,'archive_sha256':sha(a.archive),'selected':report['selected'],
            'selection_encode_wall_seconds':report['selection_encode_wall_seconds'],
            'candidate_validation_wall_seconds':report['candidate_validation_wall_seconds'],
            'candidate_plan':report['candidate_plan'],
            'attempts':[{'name':x['name'],'status':x['status'],'archive_bytes':x.get('archive_bytes'),
                'encode_wall_seconds':x.get('wall_seconds'),'validation_wall_seconds':x.get('validation',{}).get('wall_seconds')}
                for x in report['attempts']],
            'maximum_direct_attempt_coverage':report['maximum_direct_attempt_coverage'],
            'policy_excluded':report['policy_excluded']}
    else:
        report=decode_archive(a.archive,a.restored,policy)
        result={'restored_bytes':a.restored.stat().st_size,'restored_sha256':sha(a.restored),'decoder':report}
    print(json.dumps(result,sort_keys=True),flush=True)

if __name__=='__main__':main()
