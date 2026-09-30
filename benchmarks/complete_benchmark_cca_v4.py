#!/usr/bin/env python3
"""Corrected, resumable 33-member CCA benchmark wave and ranked results."""
from __future__ import annotations
import argparse,hashlib,json,os,random,statistics,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.codec_profiles import SETTINGS,digest
from benchmarks.hutter_bounded_runner import build_identity,canonical,load_manifest,valid_receipt
from benchmarks.hutter_experiment_scheduler import WaveScheduler
ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'docs/research/2026-10-01-complete-benchmarks/cca-full-files-v2'
AREA=ROOT/'docs/research/2026-10-01-complete-benchmarks/cca-full-files-v4'
INPUTS=ROOT/'docs/research/2026-09-30-generic-pipeline/inputs.json';POLICY=ROOT/'docs/research/2026-09-30-codec-profiles/policy.json'
METHODS=('cix','gzip','bzip2','zstd','xz','brotli','paq8px');PROFILES=('fast','current','size')
OLD_SCHED=WaveScheduler(ROOT)

def sha_range(path,length):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  remaining=length
  while remaining:
   b=f.read(min(1<<20,remaining))
   if not b:break
   h.update(b);remaining-=len(b)
 if remaining:raise ValueError('truncated source')
 return h.hexdigest()

def old_controls(records):
 oldcells=json.loads((PREV/'cells.json').read_text());index={(x['label'],x['profile'],x['method']):x for x in oldcells}
 reused=[]
 for label,method,cpu in [('canterbury-alice29.txt','gzip',17),('canterbury-alice29.txt','bzip2',18),('canterbury-alice29.txt','zstd',19)]:
  cell=index[(label,'fast',method)];tp=OLD_SCHED._terminal_path(cell['cell_id'])
  if not tp.is_file():continue
  t=json.loads(tp.read_text());rec=t.get('runner_result',{}).get('receipt')
  if t.get('runner_status')!='VERIFIED_SCREENING' or not rec:continue
  rp=Path(rec);r=json.loads(rp.read_text());inp=next(x for x in records if x['label']==label)
  m=json.loads(Path(cell['manifest_path']).read_text())
  expected_config={'profile':'fast','method':method,'settings':SETTINGS['fast'][method],
      'backend_identity':'exact pinned reference preset; CIX is integrated CIXB1 portfolio','repetitions':3,'warmups':1}
  expected_budget={'cpu':int(m['budget']['cpu']),'max_rss_bytes':2_000_000_000,
      'max_temp_bytes':100_000_000,'wall_seconds':300,'swap_bytes':0}
  if (r['identity']['input']['sha256']!=inp['full_sha256'] or r['identity']['input']['length']!=inp['length']
      or m['configuration']!=expected_config or m['budget']!=expected_budget
      or r.get('budget')!=expected_budget or not valid_receipt(rp,r['identity'])):continue
  reps=json.loads((rp.parent/'work/encode.repetitions.json').read_text())
  dec=json.loads((rp.parent/'work/decode.repetitions.json').read_text())
  reused.append({'cell_id':'reused-'+cell['cell_id'],'label':label,'profile':'fast','method':method,
     'input_bytes':inp['length'],'input_sha256':inp['full_sha256'],'status':'VERIFIED_SCREENING',
     'archive_bytes':r['archive_bytes'],'archive_sha256':r['archive_sha256'],'verification':r['verification'],
     'receipt':str(rp),'reused_from_cell':cell['cell_id'],'reused_from_commit':'7d35339f325188a7417a6e9ea55977f2b3e375df',
     'encode':reps,'decode':dec,'reuse_basis':'same entire source SHA-256, settings, codec leaf source SHA-256, pinned policy and exact resource budgets; original cell completed before this matrix'})
 return reused

def prepare():
 if (AREA/'cells.json').exists():raise RuntimeError('CCA-v3 declarations already frozen')
 inp=[dict(x) for x in json.loads(INPUTS.read_text()) if x.get('stratum')=='generic-regression']
 if len(inp)!=33:raise RuntimeError('expected the 33 existing CCA files')
 for x in inp:x['full_sha256']=sha_range(x['path'],x['length'])
 cpus=[];cores=set()
 for c in sorted(os.sched_getaffinity(0)):
  p=Path(f'/sys/devices/system/cpu/cpu{c}/topology');key=((p/'physical_package_id').read_text(),(p/'core_id').read_text())
  if key not in cores:cpus.append(c);cores.add(key)
  if len(cpus)==4:break
 reused=old_controls(inp);reusekeys={(x['label'],x['profile'],x['method']) for x in reused}
 manifests=AREA/'manifests';manifests.mkdir(parents=True,exist_ok=True)
 if any(manifests.iterdir()):raise RuntimeError('partial CCA-v3 manifests present; no overwrite')
 cells=[];allcells=[]
 for x in inp:
  for profile in PROFILES:
   for method in METHODS:
    config={'profile':profile,'method':method,'settings':SETTINGS[profile].get(method,{'effort':'CIXB1 '+profile}),
      'backend_identity':'exact pinned reference preset; CIX is integrated CIXB1 portfolio','repetitions':3,'warmups':1,'adapter_revision':'cca-full-v4-archive-only-decoder'}
    key=(x['label'],profile,method)
    if profile=='size' and method=='paq8px':
     allcells.append({'cell_id':'resource-'+hashlib.sha256((x['label']+'-size-paq8px').encode()).hexdigest()[:16],
       'label':x['label'],'profile':'size','method':'paq8px','input_bytes':x['length'],
       'input_sha256':x['full_sha256'],'status':'RESOURCE_LIMIT',
       'reason':'Frozen PAQ8PX v216 -12L with five LSTM layers exceeds the shared 12 GB RAM cap; not launched; no substitute preset.'})
     continue
    if key in reusekeys:
     r=next(c for c in reused if (c['label'],c['profile'],c['method'])==key)
     allcells.append({'cell_id':r['cell_id'],'label':x['label'],'profile':profile,'method':method,'input_bytes':x['length'],
        'input_sha256':x['full_sha256'],'status':'REUSED_VERIFIED','receipt':r['receipt'],'reuse_source_cell':r['reused_from_cell']})
     continue
    name=f"{x['label']}-{profile}-{method}";slug=hashlib.sha256(canonical({'wave':'cca-full-v4','input':x['full_sha256'],'config':config})).hexdigest()[:16]
    if method=='cix':
     leaf=str(ROOT/'benchmarks/complete_benchmark_codec_v4.py');out='{workdir}/candidate.cix'
     enc=[sys.executable,leaf,'encode','{source}',out,'--profile',profile,'--policy',str(POLICY),'--metadata','{workdir}/cix-repetitions.json']
     dec=[sys.executable,leaf,'decode',out,'{workdir}/restored.bin','--policy',str(POLICY)]
     build=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'cix').glob('*.py'))
     build+=['benchmarks/complete_benchmark_codec_v4.py','benchmarks/hutter_bounded_runner.py','benchmarks/hutter_experiment_scheduler.py',str(POLICY.relative_to(ROOT))]
    else:
     flags=['--method',method,'--profile',profile,'--policy',str(POLICY)];leaf=str(ROOT/'benchmarks/codec_profiles.py')
     out='{workdir}/candidate.bin';enc=[sys.executable,leaf,'encode','{source}',out,*flags]
     dec=[sys.executable,leaf,'decode',out,'{workdir}/restored.bin',*flags]
     build=['benchmarks/codec_profiles.py','benchmarks/hutter_bounded_runner.py','benchmarks/hutter_experiment_scheduler.py',str(POLICY.relative_to(ROOT))]
    manifest={'hypothesis':'Measure all full-file CCA results across exact six reference presets and integrated CIXB1 to finish the canonical format-agnostic gate.',
      'matched_control':'same complete source file bytes/hash; same one-core machine and resource caps; equal profile and repetition policy',
      'input':{'path':x['path'],'offset':0,'length':x['length'],'sha256':x['full_sha256'],'full_asset_sha256':x['full_sha256']},
      'configuration':config,'initial_state':'empty per encode and decode repetition; no cross-file history',
      'mechanism':'Original bytes -> one direct reference preset, or CIX -> every profile-eligible CIXB1 backend and native CIXG1 candidates; select smallest complete exact-verified archive.',
      'budget':{'cpu':cpus[len(cells)%4],'max_rss_bytes':2_000_000_000,'max_temp_bytes':100_000_000,'wall_seconds':300,'swap_bytes':0},
      'stage':'screening','longer_budget_justification':'The complete CCA set is <=1.03 MiB/file. 300 seconds per encode or archive-only decode phase covers one warm-up and three physical repetitions, including selector discarded trials; aggregate wave ceilings remain 4 cores, 12 GB RAM, 4 GB temporary bytes, no swap.',
      'promotion_criteria':'Every measured archive independently decodes without source access. All three output sizes/hashes and restored SHA-256 values must agree with the frozen full source. Timeout/resource failures stay visible; ranking uses verified complete archives only.',
      'exposure':'The existing CIX gate previously read these files. The all-reference full-file measurements are exposed comparisons; presets were frozen before the added reference runs. Not an untouched holdout.',
      'encode_command':enc,'decode_command':dec,'artifacts':{'archive':out,'restored':'{workdir}/restored.bin'},
      'build_paths':build,'resource_accounting':'one physical core; cgroup MemoryMax=2,000,000,000; 100,000,000-byte work cap; 300 seconds each phase; swap disabled'}
    mp=manifests/f'{name}-{slug}.json';mp.write_bytes(canonical(manifest)+b'\n');_,msha=load_manifest(mp)
    cell={'cell_id':'fullcca3-'+slug,'owner':'/root','manifest_path':str(mp.relative_to(ROOT)),
      'output_dir':str((AREA/'runs'/f'{name}-{slug}').relative_to(ROOT)),
      'expected_manifest_sha256':msha,'expected_build_sha256':build_identity(manifest,ROOT),
      'label':x['label'],'profile':profile,'method':method,'input_bytes':x['length'],'input_sha256':x['full_sha256']}
    cells.append(cell);allcells.append(cell)
 (AREA/'reused-controls.json').write_text(json.dumps(reused,indent=2)+'\n')
 (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n')
 (AREA/'coverage.json').write_text(json.dumps({'cells':allcells,'input_manifest_sha256':digest(INPUTS)},indent=2)+'\n')
 (AREA/'environment.json').write_text(json.dumps({'frozen_at':datetime.now(timezone.utc).isoformat(),
  'supersedes':'cca-full-files-v2 had one wrapper import-path failure and three reusable exact controls; cca-full-files-v3 was frozen but never launched after audit found the decoder wrapper read encoder-side repetition metadata. This v4 decoder consumes only the selected archive plus the pinned versioned decoder policy; v2/v3 artifacts remain retained.',
  'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'coordinator_sha256':digest(Path(__file__)),
  'cix_wrapper_sha256':digest(ROOT/'benchmarks/complete_benchmark_codec_v4.py'),
  'archive_only_decoder':'CIX decode command requires only the selected archive, the versioned CIX decoder code and its pinned policy/dependency manifest. It never reads encoder repetition metadata or original source.',
  'build_pipeline_sha256':digest(ROOT/'cix/pipeline.py'),'backend_portfolio_sha256':digest(ROOT/'cix/backend_portfolio.py'),
  'cores':cpus,'aggregate_limits':{'cores':4,'ram_bytes':12_000_000_000,'temporary_bytes':4_000_000_000,'swap_bytes':0},
  'cell_limits':{'ram_bytes':2_000_000_000,'temporary_bytes':100_000_000,'phase_wall_seconds':300},
  'dataset_count':33,'dataset_bytes':sum(x['length'] for x in inp),'measurement_cells':len(allcells),
  'new_execution_cells':len(cells),'reused_prior_cells':len(reused),'datasets':inp,
  'size_Paq8px':'RESOURCE_LIMIT, excluded pre-launch: v216 -12L with 5 LSTM layers requires about 29 GB; no weaker preset substituted.'},indent=2)+'\n')
 print(json.dumps({'datasets':len(inp),'dataset_bytes':sum(x['length'] for x in inp),'cells':len(allcells),
   'new_executions':len(cells),'reused_controls':len(reused),'cpus':cpus},sort_keys=True),flush=True)

def collect():
 cells=json.loads((AREA/'coverage.json').read_text())['cells'];rows=[];reuse={x['cell_id']:x for x in json.loads((AREA/'reused-controls.json').read_text())}
 scheduler=WaveScheduler(ROOT)
 for c in cells:
  row={k:c[k] for k in ('cell_id','label','profile','method','input_bytes','input_sha256')};row['status']='PENDING'
  if c.get('status')=='RESOURCE_LIMIT':
   row.update(status='RESOURCE_LIMIT',reason=c['reason'])
  elif c.get('status')=='REUSED_VERIFIED':
   source=reuse[c['cell_id']];row.update({k:source[k] for k in ('status','archive_bytes','archive_sha256','verification','receipt','reuse_basis','encode','decode','reused_from_commit')})
  else:
   tpath=scheduler._terminal_path(c['cell_id'])
   if tpath.exists():
    t=json.loads(tpath.read_text());res=t.get('runner_result',{});receipt=res.get('receipt')
    row['scheduler_status']=t['runner_status']
    if receipt and Path(receipt).is_file():
     r=json.loads(Path(receipt).read_text());row.update(status=r['status'],archive_bytes=r.get('archive_bytes'),archive_sha256=r.get('archive_sha256'),verification=r.get('verification'),phases=r.get('phases'),budget=r.get('budget'),receipt=receipt)
     w=Path(receipt).parent/'work'
     if c['method']=='cix' and (w/'cix-repetitions.json').is_file():row['portfolio']=json.loads((w/'cix-repetitions.json').read_text())
     else:
      for phase in ('encode','decode'):
       rp=w/f'{phase}.repetitions.json'
       if rp.is_file():row[phase]=json.loads(rp.read_text())
    else:
     for fail in (ROOT/c['output_dir']).glob('*/failed.json'):
      obj=json.loads(fail.read_text());row.update(status=obj.get('status','FAILED'),failure=json.loads(fail.read_text()));break
  rows.append(row)
 counts={}
 for r in rows:counts[r['status']]=counts.get(r['status'],0)+1
 (AREA/'results.json').write_text(json.dumps({'collected_at':datetime.now(timezone.utc).isoformat(),'counts':counts,'rows':rows},indent=2)+'\n')
 print(json.dumps({'cells':len(rows),'counts':counts,'pending':counts.get('PENDING',0)},sort_keys=True),flush=True)
 return rows

def run():
 plan=json.loads((AREA/'cells.json').read_text());s=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
 pending=[c for c in plan if not s._terminal_path(c['cell_id']).exists()]
 while pending:
  wave=[];used=set()
  for c in pending:
   cpu=load_manifest(ROOT/c['manifest_path'])[0]['budget']['cpu']
   t=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology');key=((t/'physical_package_id').read_text(),(t/'core_id').read_text())
   if key not in used:wave.append(c);used.add(key)
   if len(wave)==4:break
  s.run_wave(wave)
  for c in wave:pending.remove(c)
  records=[json.loads(s._terminal_path(c['cell_id']).read_text()) for c in wave]
  print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'wave_cells':len(wave),'remaining':len(pending),
   'work':[{'input':c['label'],'profile':c['profile'],'method':c['method']} for c in wave],
   'statuses':[r['runner_status'] for r in records]},sort_keys=True),flush=True)
  collect()
 collect()

def main():
 p=argparse.ArgumentParser();p.add_argument('op',choices=['prepare','run','collect']);a=p.parse_args()
 if a.op=='prepare':prepare()
 elif a.op=='run':run()
 else:collect()
if __name__=='__main__':main()
