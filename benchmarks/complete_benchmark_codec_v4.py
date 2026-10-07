#!/usr/bin/env python3
"""Immutable-snapshot entry point for whole-file CIXB1 portfolio benchmarks."""
from __future__ import annotations
import argparse, hashlib, json, statistics, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def encode(source,destination,profile,policy_path,metadata):
 from cix.backend_portfolio import encode_portfolio
 source,destination=Path(source),Path(destination);policy=json.loads(Path(policy_path).read_text())
 work=destination.parent/'cix-attempts';work.mkdir(parents=True,exist_ok=True)
 warm=work/'warm.cix';start=time.perf_counter()
 warm_report=encode_portfolio(source,warm,profile=profile,policy=policy,attempt_directory=work/'warm-attempts')
 warm_seconds=time.perf_counter()-start;warm.unlink(missing_ok=True)
 reps=[]
 for i in range(3):
  archive=work/f'archive.rep{i}.cix';start=time.perf_counter()
  report=encode_portfolio(source,archive,profile=profile,policy=policy,attempt_directory=work/f'attempts.rep{i}')
  reps.append({'index':i,'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),
   'selected':report['selected'],'selection_encode_wall_seconds':report['selection_encode_wall_seconds'],
   'candidate_validation_wall_seconds':report['candidate_validation_wall_seconds'],
   'total_audit_wall_seconds':time.perf_counter()-start,'candidate_plan':report['candidate_plan'],
   'candidate_results':[{'name':a['name'],'status':a['status'],'archive_bytes':a.get('archive_bytes'),
     'encode_wall_seconds':a.get('wall_seconds'),'validation_wall_seconds':a.get('validation',{}).get('wall_seconds')}
     for a in report['attempts']],
   'maximum_direct_attempt_coverage':report['maximum_direct_attempt_coverage'],
   'policy_excluded':report['policy_excluded']})
 primary=sorted(range(3),key=lambda i:(reps[i]['bytes'],i))[1];chosen=reps[primary]
 destination.write_bytes(Path(chosen['archive']).read_bytes())
 if destination.stat().st_size!=chosen['bytes'] or sha(destination)!=chosen['sha256']:raise ValueError('primary CIXB1 archive copy hash mismatch')
 Path(metadata).write_text(json.dumps({'warmup_seconds':warm_seconds,'primary_index':primary,
  'primary_rule':'median complete archive size; ties by repetition index','repetitions':reps},indent=2,sort_keys=True)+'\n')
 print(json.dumps({'selected':chosen['selected'],'archive_bytes':chosen['bytes'],'archive_sha256':chosen['sha256'],
  'maximum_direct_attempt_coverage':chosen['maximum_direct_attempt_coverage']},sort_keys=True),flush=True)

def decode(archive,destination,policy_path):
 from cix.backend_portfolio import decode_archive
 policy=json.loads(Path(policy_path).read_text());source=Path(archive)
 reps=[]
 for i in range(3):
  out=Path(destination).parent/f'restored.rep{i}.bin';start=time.perf_counter()
  report=decode_archive(source,out,policy)
  reps.append({'index':i,'bytes':out.stat().st_size,'sha256':sha(out),'seconds':time.perf_counter()-start,'decoder':report})
 if len({(r['bytes'],r['sha256']) for r in reps})!=1:raise ValueError('independent archive-only decodes differ')
 Path(destination).write_bytes((Path(destination).parent/'restored.rep0.bin').read_bytes())
 print(json.dumps({'decode_repetitions':len(reps),'restored_bytes':reps[0]['bytes'],'sha256':reps[0]['sha256'],
  'median_seconds':statistics.median(r['seconds'] for r in reps)},sort_keys=True),flush=True)

def main():
 p=argparse.ArgumentParser();sp=p.add_subparsers(dest='op',required=True)
 e=sp.add_parser('encode');e.add_argument('source');e.add_argument('destination');e.add_argument('--profile',choices=['fast','current','size'],required=True);e.add_argument('--policy',required=True);e.add_argument('--metadata',required=True)
 d=sp.add_parser('decode');d.add_argument('archive');d.add_argument('destination');d.add_argument('--policy',required=True)
 a=p.parse_args()
 if a.op=='encode':encode(a.source,a.destination,a.profile,a.policy,a.metadata)
 else:decode(a.archive,a.destination,a.policy)
if __name__=='__main__':main()
