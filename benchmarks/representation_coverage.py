"""Fill only untested frozen CIX representations; preserve previous failures."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
from benchmarks.hutter_bounded_runner import canonical,build_identity,load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.generic_research import _timing
from cix.pipeline import ROUTES
ROOT=Path(__file__).resolve().parents[1];AREA=ROOT/'docs/research/2026-09-30-representation-coverage'
OLD=ROOT/'docs/research/2026-09-30-generic-pipeline'

def prepare():
 if (AREA/'cells.json').exists():raise RuntimeError('Coverage already frozen')
 AREA.mkdir(parents=True,exist_ok=True)
 inputs=[x for x in json.loads((OLD/'inputs.json').read_text()) if x['stratum'] in ('development','heldout')]
 prior=json.loads((OLD/'results.json').read_text());policy=json.loads((ROOT/'docs/research/2026-09-30-codec-profiles/policy.json').read_text())
 builds=[str(p.relative_to(ROOT)) for p in (ROOT/'cix').glob('*.py')]+['benchmarks/generic_probe.py']
 cells=[];reused=[]
 for inp in inputs:
  for route in ROUTES.values():
   configuration={'mode':'pipeline','effort':'maximum','force':route,'backend':'hybrid'}
   previous=next((r for r in prior if r['label']==inp['label'] and r['config']==configuration),None)
   if previous:reused.append(previous);continue
   cpu=policy['core_cpus'][len(cells)%4]
   flags=['--mode','pipeline','--effort','maximum','--force',route,'--backend','hybrid']
   base=['/usr/bin/time','-v','-o','{workdir}/encode.time.txt',sys.executable,str(ROOT/'benchmarks/generic_probe.py')]
   manifest={'hypothesis':'Every implemented representation must expose its complete physical cost independently of adaptive raw/PAQ fallback. Fill missing hybrid-route screens without retrying preserved failed configurations.',
    'matched_control':'Same immutable input bytes and frozen CIX implementation; original-byte PAQ v216 -8 settings wave and unchanged same-representation backend controls remain separate attribution evidence.',
    'input':inp,'configuration':configuration,'mechanism':route+' forced before portfolio selection; paid dictionary/count/stream boundaries/checksums and framing',
    'budget':{'cpu':cpu,'max_rss_bytes':2_000_000_000,'max_temp_bytes':100_000_000,'wall_seconds':60},
    'promotion_criteria':'finished physical archive; independent source-inaccessible decode; SHA-256 and full equality; a timed-out forced candidate remains unqualified and is not raw fallback',
    'encode_command':base+['encode','{source}','{workdir}/candidate.bin']+flags,
    'decode_command':['/usr/bin/time','-v','-o','{workdir}/decode.time.txt',sys.executable,str(ROOT/'benchmarks/generic_probe.py'),'decode','{workdir}/candidate.bin','{workdir}/restored.bin','--mode','pipeline'],
    'artifacts':{'archive':'{workdir}/candidate.bin','restored':'{workdir}/restored.bin'},'build_paths':builds,'initial_state':'empty','stage':'screening','exposure':'All six ranges previously exposed; these are settings/representation screens, not fresh holdouts.'}
   identity=hashlib.sha256(canonical({'manifest':manifest,'build':build_identity(manifest,ROOT)})).hexdigest()[:24];id='representation-'+identity
   path=AREA/'manifests'/f'{id}.json';path.parent.mkdir(exist_ok=True);path.write_bytes(canonical(manifest)+b'\n');_,sha=load_manifest(path)
   cells.append(dict(cell_id=id,owner='/root',manifest_path=str(path),output_dir=str(AREA/'runs'/id),expected_manifest_sha256=sha,expected_build_sha256=build_identity(manifest,ROOT),label=inp['label'],config=configuration))
 (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n');(AREA/'reused.json').write_text(json.dumps(reused,indent=2)+'\n')
 print(json.dumps({'missing_cells':len(cells),'retained_prior_cells':len(reused),'routes':list(ROUTES.values()),'inputs':len(inputs)}),flush=True)

def collect():
 rows=json.loads((AREA/'reused.json').read_text())
 for c in json.loads((AREA/'cells.json').read_text()):
  path=next(iter(Path(c['output_dir']).glob('*/receipt.json')),None) or next(iter(Path(c['output_dir']).glob('*/failed.json')),None)
  row={'label':c['label'],'config':c['config'],'status':'PENDING','cell_id':c['cell_id']}
  if path:
   r=json.loads(path.read_text());work=path.parent/'work';row.update(status=r['status'],receipt=str(path),bytes=r['archive_bytes'],archive_sha256=r['archive_sha256'],original_bytes=r['identity']['input']['length'],input_sha256=r['identity']['input']['sha256'],verification=r['verification'],encode=_timing(work/'encode.time.txt'),decode=_timing(work/'decode.time.txt'))
   if row['status']=='VERIFIED_SCREENING':
    codec=work/'encode.codec.json';row['codec']=json.loads(codec.read_text())
    trace=json.loads((work/'blocks.jsonl').read_text().splitlines()[0]);row['accounting']=trace['accounting']
    with Path(r['identity']['input']['path']).open('rb') as f:f.seek(r['identity']['input']['offset']);original=f.read(row['original_bytes'])
    assert Path(r['artifacts']['restored']).read_bytes()==original
   else:
    errors='\n'.join(p.read_text() for p in path.parent.glob('*.stderr.log'));row['failure_reason']='ROUTE_TIME_BUDGET' if 'TIME_BUDGET' in errors else 'COMMAND_OR_VERIFICATION_FAILURE'
  rows.append(row)
 (AREA/'results.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def run():
 scheduler=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
 cells=[c for c in json.loads((AREA/'cells.json').read_text()) if not scheduler._terminal_path(c['cell_id']).exists()]
 while cells:
  wave=[];cpus=set()
  for c in cells:
   cpu=json.loads(Path(c['manifest_path']).read_text())['budget']['cpu']
   if cpu not in cpus:wave.append(c);cpus.add(cpu)
   if len(wave)==4:break
  scheduler.run_wave(wave)
  for c in wave:cells.remove(c)
  rows=collect();print(json.dumps({'remaining':len(cells),'verified':sum(r['status']=='VERIFIED_SCREENING' for r in rows),'failed_budget':sum(r.get('failure_reason')=='ROUTE_TIME_BUDGET' for r in rows)}),flush=True)
  if any(r['status']=='FAILED' and r.get('failure_reason')!='ROUTE_TIME_BUDGET' for r in rows):raise RuntimeError('Unexpected command or verification failure; stop and inspect')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['prepare','run','collect']);a=p.parse_args()
 if a.operation=='prepare':prepare()
 elif a.operation=='run':run()
 else:print(json.dumps({'rows':len(collect())}))
