#!/usr/bin/env python3
"""Freeze and queue the authorized 20-thread native CIX BEST catalog study.

Preparation never builds or benchmarks.  Dispatch is serial (one 20-core
cell) through the shared WaveScheduler and is intentionally not invoked here.
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmarks.hutter_bounded_runner import canonical, sha256, build_identity, load_manifest, NATIVE_CATALOG_AUTHORIZATION
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core
from benchmarks.cix_best_expanded_qualification import (artifact_identity, descriptor_ids_from_source, native_trial_ids,
    selector_ledger, mandatory_gnu_time, actual_status)
from benchmarks.cix_full_catalog import cca_inputs, catalog_inputs, frozen_references

AREA_ROOT=ROOT/'docs/research/2026-10-02-best20-catalog'
REGISTRY_ROOT=ROOT/'docs/research/2026-10-02-rust-full-catalog'
HOST_RUNTIME=REGISTRY_ROOT/'host-runtime.json'
# Ordinary BEST remains a 2 GiB codec policy.  Three decimal GB leaves
# allocator/output headroom while the one-cell global scheduler still retains
# space for the user-authorized Sonar server (4 GB) and scanner (1 GB).
RSS,TEMP,WALL=3_000_000_000,1_000_000_000,7_200
AUTH='2026-10-02-user-best20-catalog'

def now(): return datetime.now(timezone.utc).isoformat()
def rel(p): return str(Path(p).resolve().relative_to(ROOT))
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+'.tmp');q.write_bytes(canonical(v)+b'\n');q.replace(p)
def cpus():
 available=sorted(os.sched_getaffinity(0)); out=[]; seen=set()
 for cpu in available:
  if not 8<=cpu<=31: continue
  core=_core(cpu)
  if core not in seen: out.append(cpu);seen.add(core)
  if len(out)==20:return out
 raise RuntimeError('requires taskset -c 8-31 with twenty distinct physical CPUs; current controller affinity is insufficient')
def rows():
 refs=frozen_references();catalog,missing,_=catalog_inputs(refs)
 if missing:raise RuntimeError('catalog input unavailable')
 gate=cca_inputs(catalog,refs);tail=[x for x in catalog if x['stage']=='catalog'];allrows=gate+tail
 if len(gate)!=33 or len(tail)!=17 or len(allrows)!=50:raise RuntimeError('must freeze 33 CCA plus 17 catalog inputs')
 return allrows
def shell_phase(status, command):
 # POSIX shell writes the real child code, avoiding the transient-systemd stale
 # ExecMainStatus issue and avoiding Python imports inside a frozen snapshot.
 return ['/bin/bash','-c','p=$1; shift; "$@"; r=$?; printf "%s\\n" "$r" > "$p"; exit "$r"','cix-phase',status,*command]
def freeze_sources(area,artifact):
 d=area/'frozen-source';d.mkdir();result={}
 for source in (ROOT/'rust/cix-native/src/external.rs',ROOT/'rust/cix-native/src/portfolio_auto.rs',ROOT/'benchmarks/cix_best20_catalog.py',ROOT/'benchmarks/cix_best_expanded_qualification.py',ROOT/'benchmarks/cix_dickens_best_compare.py',ROOT/'benchmarks/cix_full_catalog.py',ROOT/'benchmarks/hutter_bounded_runner.py',ROOT/'benchmarks/hutter_experiment_scheduler.py'):
  target=d/source.name;shutil.copy2(source,target)
  if sha256(source)!=sha256(target):raise RuntimeError('source freeze mismatch')
  result[source.name]={'path':rel(target),'sha256':sha256(target),'source_path':rel(source)}
 artifact['frozen_source_paths']=result
def manifest(row,art,registry,cpu):
 cix=ROOT/art['binaries']['cix']['path'];uncix=ROOT/art['binaries']['uncix']['path']
 enc=['/usr/bin/time','-v','-o','{workdir}/encode.gnu-time.txt',str(cix),'--best','--threads','20','--verbose','-o','{workdir}/candidate.cix','{source}']
 dec=['/usr/bin/time','-v','-o','{workdir}/decode.gnu-time.txt',str(uncix),'-o','{workdir}/restored.bin','{workdir}/candidate.cix']
 return {'hypothesis':'Twenty physical CPU threads improve bounded native BEST search throughput while the automatic selector still chooses the smallest complete valid archive.',
 'matched_control':'One frozen input, `cix --best --threads 20 --verbose`, fresh archive-only uncix, one serial 20-physical-core cell, 12 GB RSS, 4 GB temporary storage and no GPU.',
 'input':{'path':str(row['path'].resolve()),'offset':0,'length':row['bytes'],'sha256':row['sha256'],'label':row['label'],'catalog_id':row['catalog_id']},
 'configuration':{'effort':'best','flags':['--best','--threads','20','--verbose'],'automatic_selection':True,'advanced_overrides':['threads=20'],'expected_descriptor_ids':art['candidate_registry'],'expected_native_trial_ids':native_trial_ids(row['bytes']),'host_runtime':{'path':rel(HOST_RUNTIME),'sha256':sha256(HOST_RUNTIME)}},
 'artifact':art,'mechanism':'Complete archive bytes include all selection, framing, metadata and integrity costs. The selector ledger is required after fresh exact restoration.',
 'budget':{'cpu':cpu,'max_rss_bytes':RSS,'max_temp_bytes':TEMP,'swap_bytes':0,'wall_seconds':WALL},'stage':'native_catalog_qualification','authorization':NATIVE_CATALOG_AUTHORIZATION,'best20_authorization':AUTH,'longer_budget_justification':'Explicit user-authorized full catalog BEST evaluation; each cached input is at most 100,000,000 bytes and one 20-core cell remains within 12 GB/4 GB aggregate limits.',
 'promotion_criteria':'Require actual zero child exit records, complete GNU Time fields, a complete archive, fresh exact native decode and complete typed selector coverage. Failures remain durable non-ranked results.',
 'encode_command':shell_phase('{workdir}/encode.exit-status.txt',enc),'decode_command':shell_phase('{workdir}/decode.exit-status.txt',dec),'artifacts':{'archive':'{workdir}/candidate.cix','restored':'{workdir}/restored.bin'},
 'build_paths':[*(x['path'] for x in art['binaries'].values()),art['metadata'],*(x['path'] for x in art['frozen_source_paths'].values()),registry['build_path'],rel(HOST_RUNTIME)],'qualification_registry':registry}
def prepare(identity,artifact_dir):
 if not HOST_RUNTIME.is_file():raise RuntimeError('missing host runtime evidence')
 area=AREA_ROOT/identity
 if area.exists():raise RuntimeError('immutable plan exists')
 cpu=cpus();art=artifact_identity(artifact_dir);data=rows();area.mkdir(parents=True);(area/'.gitignore').write_text('runs/**/work/\nruns/**/build/\n');freeze_sources(area,art)
 registry_path=REGISTRY_ROOT/(identity+'-best20')/'input-registry.json'
 if registry_path.exists():raise RuntimeError('immutable registry exists')
 write(registry_path,{'authorization':NATIVE_CATALOG_AUTHORIZATION,'best20_authorization':AUTH,'inputs':[{'label':x['label'],'path':str(x['path'].resolve()),'offset':0,'length':x['bytes'],'sha256':x['sha256']}for x in data]})
 registry={'path':str(registry_path.resolve()),'build_path':rel(registry_path),'sha256':sha256(registry_path)};manifests=area/'manifests';manifests.mkdir();cells=[]
 for row in data:
  m=manifest(row,art,registry,cpu);ms=hashlib.sha256(canonical(m)).hexdigest();cid='cix-best20-'+hashlib.sha256(identity.encode()).hexdigest()[:12]+'-'+ms[:24];p=manifests/(cid+'.json');p.write_bytes(canonical(m)+b'\n');loaded,actual=load_manifest(p)
  if actual!=ms:raise RuntimeError('manifest changed')
  cells.append({'cell_id':cid,'owner':'/root','label':row['label'],'catalog_id':row['catalog_id'],'stage':row['stage'],'profile':'best','manifest_path':rel(p),'output_dir':rel(area/'runs'/cid),'cpu':cpu,'expected_manifest_sha256':actual,'expected_build_sha256':build_identity(loaded,ROOT),'expected_descriptor_ids':m['configuration']['expected_descriptor_ids'],'expected_native_trial_ids':m['configuration']['expected_native_trial_ids'],'fresh_justification':'New 20-thread BEST artifact; no prior result reused.'})
 if len(cells)!=50 or len([x for x in cells if x['stage']=='gate'])!=33 or len([x for x in cells if x['stage']=='catalog'])!=17:raise RuntimeError('50-cell gate/catalog binding failed')
 write(area/'cells.json',{'identity':identity,'artifact':art,'cells':cells,'counts':{'total':50,'gate':33,'catalog':17},'cpu':cpu,'registry':registry})
 write(area/'plan.json',{'identity':identity,'status':'PREPARED_NOT_EXECUTED','threads':20,'cpu':cpu,'aggregate':'one serial 20-physical-core cell; 12 GB RAM; 4 GB temp; no GPU','ordering':'33 CCA before 17 catalog','artifact':art})
 print(json.dumps({'prepared':rel(area),'cells':50,'cpu':cpu,'execution':'not started'},sort_keys=True))
def collect(area):
 plan=json.loads((area/'cells.json').read_text());scheduler=WaveScheduler(ROOT,max_jobs=1,max_memory_bytes=RSS,max_temp_bytes=TEMP);out=[]
 for cell in plan['cells']:
  terminal=scheduler._terminal_path(cell['cell_id']);base={k:cell[k] for k in ('cell_id','label','catalog_id','stage','profile')}
  if not terminal.is_file():out.append({**base,'status':'PENDING'});continue
  term=json.loads(terminal.read_text());receipt_name=term.get('runner_result',{}).get('receipt')
  if not receipt_name or not Path(receipt_name).is_file():out.append({**base,'status':term.get('runner_status','FAILED')});continue
  receipt_path=Path(receipt_name);receipt=json.loads(receipt_path.read_text());work=receipt_path.parent/'work';enc,enc_ok=mandatory_gnu_time(work/'encode.gnu-time.txt');dec,dec_ok=mandatory_gnu_time(work/'decode.gnu-time.txt')
  ledger,ledger_ok=selector_ledger(receipt_path,receipt['identity']['input']['length'],receipt.get('archive_bytes'),cell['expected_descriptor_ids'],cell['expected_native_trial_ids'])
  actual=actual_status(receipt_path);bound=scheduler._plan(cell);runner=term.get('runner_status');ok=(scheduler._verified_receipt(receipt_path,bound) and (runner in {'VERIFIED_SCREENING','REUSED_VERIFIED'} or receipt.get('status')=='VERIFIED_SCREENING') and actual=={'encode':0,'decode':0} and enc_ok and dec_ok and ledger_ok)
  out.append({**base,'status':'VERIFIED_SCREENING' if ok else 'UNQUALIFIED','runner_status':runner,'child_exit_status':actual,'archive_bytes':receipt.get('archive_bytes'),'archive_sha256':receipt.get('archive_sha256'),'verification':receipt.get('verification'),'receipt':rel(receipt_path),'encode':enc,'decode':dec,'selector_ledger':ledger})
 counts={}
 for row in out:counts[row['status']]=counts.get(row['status'],0)+1
 report={'collected_at':now(),'counts':counts,'rows':out};write(area/'results.json',report);return report
def queue(identity):
 area=AREA_ROOT/identity;plan=json.loads((area/'cells.json').read_text());lock=area/'queue-controller.lock'
 with lock.open('a+') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError as e:raise RuntimeError('best20 queue already active') from e
  scheduler=WaveScheduler(ROOT,max_jobs=1,max_memory_bytes=RSS,max_temp_bytes=TEMP)
  for stage in ('gate','catalog'):
   if stage=='catalog':
    gate=[x for x in collect(area)['rows'] if x['stage']=='gate']
    if len(gate)!=33 or any(x['status']!='VERIFIED_SCREENING' for x in gate):raise RuntimeError('CCA gate incomplete')
   for cell in (x for x in plan['cells'] if x['stage']==stage):
    if scheduler._terminal_path(cell['cell_id']).is_file():
     prior=next(x for x in collect(area)['rows'] if x['cell_id']==cell['cell_id'])
     if prior['status']!='VERIFIED_SCREENING':
      write(area/'queue-state.json',{'status':'STOPPED_UNQUALIFIED','cell_id':cell['cell_id'],'updated_at':now()});return
     continue
    write(area/'results.json',{'status':'CURRENT_RUNNING','updated_at':now(),'current_cell':cell,'completed':collect(area)['rows']})
    result=scheduler.run_wave([cell])[0];report=collect(area);row=next(x for x in report['rows'] if x['cell_id']==cell['cell_id'])
    if (result.get('runner_status') not in {'VERIFIED_SCREENING','REUSED_VERIFIED'} and result.get('status') not in {'VERIFIED_SCREENING','REUSED_VERIFIED'}) or row['status']!='VERIFIED_SCREENING':
     write(area/'queue-state.json',{'status':'STOPPED_UNQUALIFIED','cell_id':cell['cell_id'],'updated_at':now()});return
  report=collect(area)
  if len(report['rows'])!=50 or any(x['status']!='VERIFIED_SCREENING' for x in report['rows']):raise RuntimeError('incomplete BEST20 result')
  write(area/'queue-state.json',{'status':'COMPLETE','updated_at':now()})
def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True);a=s.add_parser('prepare');a.add_argument('--id',required=True);a.add_argument('--artifacts',type=Path,required=True);q=s.add_parser('queue');q.add_argument('--id',required=True);c=s.add_parser('collect');c.add_argument('--id',required=True);z=p.parse_args()
 if z.op=='prepare':prepare(z.id,z.artifacts)
 if z.op=='queue':queue(z.id)
 if z.op=='collect':print(json.dumps(collect(AREA_ROOT/z.id)['counts'],sort_keys=True))
if __name__=='__main__':main()
