#!/usr/bin/env python3
"""Freeze and execute full-file Canterbury / Calgary / Artificial benchmarks."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, statistics, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.codec_profiles import SETTINGS, digest
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'docs/research/2026-10-01-complete-benchmarks/cca-full-files-v2'
INPUTS=ROOT/'docs/research/2026-09-30-generic-pipeline/inputs.json'
POLICY=ROOT/'docs/research/2026-09-30-codec-profiles/policy.json'
REPS=('fast','current','size')
METHODS=('cix','gzip','bzip2','zstd','xz','brotli','paq8px')

def sha_range(path,offset,length):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  f.seek(offset);remaining=length
  while remaining:
   b=f.read(min(1<<20,remaining))
   if not b:break
   h.update(b);remaining-=len(b)
 if remaining:raise ValueError('source shorter than its declared range')
 return h.hexdigest()

def prepare():
 if (AREA/'cells.json').exists():raise RuntimeError('frozen benchmark wave exists; will not duplicate')
 records=[r for r in json.loads(INPUTS.read_text()) if r.get('stratum')=='generic-regression']
 if len(records)!=33:raise RuntimeError('expected the 33 retained CCA benchmark members')
 cpus=[];seen=set()
 for cpu in sorted(os.sched_getaffinity(0)):
  t=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology');key=((t/'physical_package_id').read_text(),(t/'core_id').read_text())
  if key not in seen:cpus.append(cpu);seen.add(key)
  if len(cpus)==4:break
 cells=[];manifests=AREA/'manifests';manifests.mkdir(parents=True,exist_ok=True)
 if any(manifests.iterdir()):raise RuntimeError('partial immutable manifest directory exists; do not overwrite frozen manifests')
 build=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'cix').glob('*.py'))
 build+=['benchmarks/codec_profiles.py','benchmarks/complete_benchmark_codec.py','benchmarks/complete_benchmark_wave.py',
         'benchmarks/hutter_bounded_runner.py','benchmarks/hutter_experiment_scheduler.py',str(POLICY.relative_to(ROOT))]
 for ordinal,inp0 in enumerate(records):
  inp=dict(inp0);inp['full_sha256']=sha_range(inp['path'],0,inp['length'])
  for profile in REPS:
   for method in METHODS:
    if profile=='size' and method=='paq8px':continue
    config={'profile':profile,'method':method,'settings':SETTINGS[profile].get(method,{'effort':'CIXB1 '+profile}),
            'backend_identity':'exact pinned reference preset; CIX is integrated CIXB1 portfolio','repetitions':3,'warmups':1}
    name=f"{inp['label']}-{profile}-{method}"
    slug=hashlib.sha256(canonical({'input':{'path':inp['path'],'bytes':inp['length'],'sha256':inp['full_sha256']},'config':config})).hexdigest()[:16]
    if method=='cix':
     encode=[sys.executable,str(ROOT/'benchmarks/complete_benchmark_codec.py'),'encode','{source}','{workdir}/candidate.cix','--profile',profile,'--policy',str(POLICY),'--metadata','{workdir}/cix-repetitions.json']
     decode=[sys.executable,str(ROOT/'benchmarks/complete_benchmark_codec.py'),'decode','{workdir}/candidate.cix','{workdir}/restored.bin','--policy',str(POLICY),'--metadata','{workdir}/cix-repetitions.json']
    else:
     flags=['--method',method,'--profile',profile,'--policy',str(POLICY)]
     encode=[sys.executable,str(ROOT/'benchmarks/codec_profiles.py'),'encode','{source}','{workdir}/candidate.bin',*flags]
     decode=[sys.executable,str(ROOT/'benchmarks/codec_profiles.py'),'decode','{workdir}/candidate.bin','{workdir}/restored.bin',*flags]
    budget={'cpu':cpus[len(cells)%4],'max_rss_bytes':2_000_000_000,'max_temp_bytes':100_000_000,
            'wall_seconds':300,'swap_bytes':0}
    manifest={'hypothesis':'Full canonical-file results fill the CCA benchmark gap and compare the integrated CIXB1 selector with the six exact reference presets under each declared profile.',
      'matched_control':'same complete canonical file hash and boundary; same-machine one-core execution; three independent encodes and archive-only decodes with one warmup',
      'input':{'path':inp['path'],'offset':0,'length':inp['length'],'sha256':inp['full_sha256'],'full_asset_sha256':inp['full_sha256']},
      'configuration':config,'initial_state':'empty at every repetition; one input-local stream; no carry between files',
      'mechanism':'original bytes directly through exact reference compressor; CIX uses the integrated bounded CIXB1 direct-backend + CIXG1 portfolio for files <=16 MiB',
      'budget':budget,'stage':'screening','longer_budget_justification':'Canonical input sizes are <=1.03 MiB. A five-minute cell allowance covers warmup, three complete physical archives and three independent archive-only decodes while the shared scheduler enforces 2 GB RAM, 100 MB temporary disk and zero swap.',
      'promotion_criteria':'complete physical archive in each of three runs; all three source-inaccessible decodes byte-identical and SHA-256 equal; retain resource exclusions/timeouts; rank only verified results',
      'exposure':'The CIX gate previously processed these full CCA files. The cross-codec full-file measurements are new and settings were frozen before execution; results are exposed benchmark evidence, not an untouched holdout.',
      'encode_command':encode,'decode_command':decode,
      'artifacts':{'archive':'{workdir}/'+('candidate.cix' if method=='cix' else 'candidate.bin'),'restored':'{workdir}/restored.bin'},
      'build_paths':build,'resource_accounting':'one physical core, 2 GB MemoryMax, 100 MB temporary directory cap, 300 s each encode/decode phase, MemorySwapMax=0'}
    mpath=manifests/f'{name}-{slug}.json';mpath.write_bytes(canonical(manifest)+b'\n');_,msha=load_manifest(mpath)
    cells.append({'cell_id':'fullcca-'+slug,'owner':'/root','manifest_path':str(mpath.relative_to(ROOT)),
      'output_dir':str((AREA/'runs'/f'{name}-{slug}').relative_to(ROOT)),
      'expected_manifest_sha256':msha,'expected_build_sha256':build_identity(manifest,ROOT),
      'label':inp['label'],'profile':profile,'method':method,'input_bytes':inp['length'],
      'input_sha256':inp['full_sha256']})
 area_runtime={'frozen_at':datetime.now(timezone.utc).isoformat(),'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'baseline_pipeline_sha256':digest(ROOT/'cix/pipeline.py'),'backend_portfolio_sha256':digest(ROOT/'cix/backend_portfolio.py'),
  'backend_profile':digest(ROOT/'docs/research/2026-09-30-codec-profiles/policy.json'),'hardware_cpus':cpus,
  'limits':{'cores':4,'ram_bytes':12_000_000_000,'temporary_bytes':4_000_000_000,'cell_rss_bytes':2_000_000_000,'cell_temp_bytes':100_000_000,'cell_phase_seconds':300,'swap_bytes':0},
  'input_count':len(records),'dataset_total_bytes':sum(r['length'] for r in records),'profiles':list(REPS),'methods':list(METHODS),
  'cells':len(cells),'size_paq8px':'RESOURCE_LIMIT: frozen -12L + five LSTM layers exceed the shared 12 GB RAM cap; not launched; no substitute preset',
  'missing_other_ready_corpora':'This wave is only the completed 33-member Canterbury/Calgary/Artificial gate. Silesia, FCBench, Golf, RAI and GDCC are not silently counted as complete.'}
 (AREA/'environment.json').write_bytes(canonical(area_runtime)+b'\n')
 (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n')
 (AREA/'coverage.json').write_text(json.dumps({'members':records,'expected_measurements':len(cells),'status':'FROZEN_NOT_YET_RUN'},indent=2)+'\n')
 print(json.dumps({'frozen_cells':len(cells),'datasets':len(records),'bytes':area_runtime['dataset_total_bytes'],'cpus':cpus,'cell_caps':area_runtime['limits']}),flush=True)

def run():
 cells=json.loads((AREA/'cells.json').read_text())
 scheduler=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
 pending=[c for c in cells if not scheduler._terminal_path(c['cell_id']).exists()]
 while pending:
  wave=[];used=set()
  for c in pending:
   cpu=load_manifest(ROOT/c['manifest_path'])[0]['budget']['cpu']
   if cpu not in used:wave.append(c);used.add(cpu)
   if len(wave)==4:break
  results=scheduler.run_wave(wave)
  for c in wave:pending.remove(c)
  terminal=[json.loads(scheduler._terminal_path(c['cell_id']).read_text()) for c in wave]
  print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'wave_cells':len(wave),'remaining':len(pending),
       'wave':[{'dataset':c['label'],'profile':c['profile'],'method':c['method']} for c in wave],
       'statuses':[x['runner_status'] for x in terminal]},sort_keys=True),flush=True)
  failed=[x for x in terminal if x['runner_status']=='FAILED']
  if failed:raise RuntimeError('Wave stopped on verification or command failure; no automatic retries')
  if any(x['runner_status']=='RUNNING' for x in terminal):raise RuntimeError('Scheduler returned while a cell remains active')
  collect()
 collect()

def collect():
 scheduler=WaveScheduler(ROOT)
 rows=[]
 for cell in json.loads((AREA/'cells.json').read_text()):
  tp=scheduler._terminal_path(cell['cell_id'])
  row={'cell_id':cell['cell_id'],'label':cell['label'],'profile':cell['profile'],'method':cell['method'],
       'input_bytes':cell['input_bytes'],'input_sha256':cell['input_sha256'],'status':'PENDING'}
  if tp.exists():
   t=json.loads(tp.read_text());result=t.get('runner_result',{});receipt=result.get('receipt')
   row['scheduler_status']=t.get('runner_status');row['receipt']=receipt
   if receipt and Path(receipt).exists():
    r=json.loads(Path(receipt).read_text());row.update(status=r['status'],archive_bytes=r.get('archive_bytes'),archive_sha256=r.get('archive_sha256'),verification=r.get('verification'),phases=r.get('phases'),budget=r.get('budget'))
    work=Path(receipt).parent/'work'
    if cell['method']=='cix' and (work/'cix-repetitions.json').exists():row['portfolio']=json.loads((work/'cix-repetitions.json').read_text())
    if cell['method']!='cix':
     for phase in ('encode','decode'):
      rp=work/f'{phase}.repetitions.json'
      if rp.exists():row[phase]=json.loads(rp.read_text())
   else:
    row['terminal_result']=t.get('runner_result')
    out=ROOT/cell['output_dir']
    for failed in out.glob('*/failed.json'):
     row['failure']=json.loads(failed.read_text());row['status']=row['failure'].get('status','FAILED');break
  if cell['method']=='paq8px' and cell['profile']=='size':
   row.update(status='RESOURCE_LIMIT',reason='Frozen PAQ8PX v216 -12L with five LSTM layers excluded before launch: exceeds 12 GB shared RAM.')
  rows.append(row)
 (AREA/'results.json').write_text(json.dumps({'collected_at':datetime.now(timezone.utc).isoformat(),'counts':__import__('collections').Counter(r['status'] for r in rows),'rows':rows},indent=2,default=dict)+'\n')
 counts={}
 for row in rows:counts[row['status']]=counts.get(row['status'],0)+1
 print(json.dumps({'cells':len(rows),'counts':counts,'pending':counts.get('PENDING',0)},sort_keys=True),flush=True)
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('op',choices=['prepare-cca','run-cca','collect']);a=p.parse_args()
 if a.op=='prepare-cca':prepare()
 elif a.op=='run-cca':run()
 else:collect()
if __name__=='__main__':main()
