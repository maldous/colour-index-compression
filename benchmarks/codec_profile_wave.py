"""Predeclare and run speed/size settings under the existing shared scheduler."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,statistics,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from benchmarks.codec_profiles import SETTINGS,digest
from benchmarks.hutter_bounded_runner import build_identity,canonical,load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler
ROOT=Path(__file__).resolve().parents[1];AREA=ROOT/'docs/research/2026-09-30-codec-profiles'

def prepare():
 if (AREA/'cells.json').exists():raise RuntimeError('Settings wave already frozen; do not duplicate')
 AREA.mkdir(parents=True,exist_ok=True)
 source=json.loads((ROOT/'docs/research/2026-09-30-generic-pipeline/inputs.json').read_text())
 inputs=[x for x in source if x['stratum'] in ('development','heldout')]
 cpus=[];cores=set()
 for cpu in sorted(os.sched_getaffinity(0)):
  p=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology');key=((p/'physical_package_id').read_text(),(p/'core_id').read_text())
  if key not in cores:cpus.append(cpu);cores.add(key)
  if len(cpus)==4:break
 assert len(cpus)==4
 paq='benchmark-work/references/paq8px-v216/build-local/paq8px'
 runtime={'python':sys.version,'platform':platform.platform(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'zstd':{'path':'/bin/zstd','sha256':digest('/bin/zstd'),'version':subprocess.check_output(['/bin/zstd','--version'],text=True).strip()},
  'paq8px':{'path':str(ROOT/paq),'sha256':digest(ROOT/paq),'version':'v216, local pinned build; AVX2; no external pretraining','source':json.loads((ROOT/'benchmark-work/references/v216-source.json').read_text())},
  'settings':SETTINGS,'core_cpus':cpus,'memory_limit_bytes':12_000_000_000,'temporary_limit_bytes':4_000_000_000,'cache':'warm/uncontrolled','timing':'GNU time leaf process including Python startup, backend startup, input/output. One warmup plus three measured independent processes; median and all repetitions retained.',
  'sources':['https://github.com/hxim/paq8px/tree/v216','https://github.com/facebook/zstd/tree/v1.5.5','https://tukaani.org/xz/man/xz.1.html','https://github.com/google/brotli/blob/master/c/include/brotli/encode.h','https://docs.python.org/3/library/gzip.html','https://docs.python.org/3/library/bz2.html']}
 policy=AREA/'policy.json';policy.write_bytes(canonical(runtime)+b'\n')
 build=[str(p.relative_to(ROOT)) for p in (ROOT/'cix').glob('*.py')]+['benchmarks/codec_profiles.py',str(policy.relative_to(ROOT)),paq]
 cells=[]
 for inp in inputs:
  for profile in ('fast','size','current'):
   for method in SETTINGS[profile]:
    if profile=='size' and method=='paq8px':continue
    if profile=='current' and method not in ('zstd','paq8px'):continue
    conf={'profile':profile,'method':method,'settings':SETTINGS[profile][method],'repetitions':3,'warmups':1}
    flags=['--method',method,'--profile',profile,'--policy',str(policy)]
    cmd=[sys.executable,str(ROOT/'benchmarks/codec_profiles.py')]
    manifest={'hypothesis':'Declared speed and size presets materially change compression tradeoffs; compare identical local frozen inputs and do not equate high preset with a universal optimum.',
     'matched_control':'same immutable 16KiB input hashes, actual end-to-end leaf processes, single pinned physical core, explicit settings and repetition policy',
     'input':inp,'configuration':conf,'mechanism':'preset/effort only; CIX source and selector unchanged; external references retain their own normal content models',
     'budget':{'cpu':cpus[len(cells)%4],'max_rss_bytes':3_000_000_000 if method=='paq8px' else 2_000_000_000,'max_temp_bytes':100_000_000,'wall_seconds':180},
     'promotion_criteria':'complete self-contained physical streams; all three archives independently decoded with original inaccessible; SHA-256 and byte equality; median timing with all repetitions retained',
     'encode_command':cmd+['encode','{source}','{workdir}/candidate.bin']+flags,
     'decode_command':cmd+['decode','{workdir}/candidate.bin','{workdir}/restored.bin']+flags,
     'artifacts':{'archive':'{workdir}/candidate.bin','restored':'{workdir}/restored.bin'},'build_paths':build,'initial_state':'empty for each warmup and repetition','stage':'screening',
     'exposure':'Previously measured inputs; historical held-out roles retained, these settings comparisons are exposed screening, not fresh holdouts.'}
    identity=hashlib.sha256(canonical({'manifest':manifest,'build':build_identity(manifest,ROOT)})).hexdigest()[:24];cell_id='profiles-'+identity
    path=AREA/'manifests'/f'{cell_id}.json';path.parent.mkdir(exist_ok=True);path.write_bytes(canonical(manifest)+b'\n');_,sha=load_manifest(path)
    cells.append(dict(cell_id=cell_id,owner='/root',manifest_path=str(path),output_dir=str(AREA/'runs'/cell_id),expected_manifest_sha256=sha,expected_build_sha256=build_identity(manifest,ROOT),label=inp['label'],configuration=conf))
 (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n')
 (AREA/'blocked.json').write_text(json.dumps([{'label':i['label'],'profile':'size','method':'paq8px','status':'RESOURCE_LIMIT','settings':SETTINGS['size']['paq8px'],'reason':'Pinned v216 -12L requires approximately 29GB plus LSTM state; exceeds entire 12GB aggregate cap. Not launched; no lower preset substituted.'} for i in inputs],indent=2)+'\n')
 print(json.dumps({'frozen_cells':len(cells),'blocked':6,'cpus':cpus}),flush=True)

def collect():
 rows=[]
 for c in json.loads((AREA/'cells.json').read_text()):
  path=next(iter(Path(c['output_dir']).glob('*/receipt.json')),None) or next(iter(Path(c['output_dir']).glob('*/failed.json')),None)
  row={'label':c['label'],'config':c['configuration'],'status':'PENDING','cell_id':c['cell_id']}
  if path:
   receipt=json.loads(path.read_text());work=path.parent/'work';row.update(status=receipt['status'],receipt=str(path),bytes=receipt['archive_bytes'],archive_sha256=receipt['archive_sha256'],original_bytes=receipt['identity']['input']['length'],input_sha256=receipt['identity']['input']['sha256'],verification=receipt['verification'],completed_at=receipt['completed_at'])
   if receipt['status']=='VERIFIED_SCREENING':
    assert digest(receipt['artifacts']['archive'])==receipt['archive_sha256']
    with Path(receipt['identity']['input']['path']).open('rb') as f:f.seek(receipt['identity']['input']['offset']);original=f.read(row['original_bytes'])
    for phase in ('encode','decode'):
     repetitions=json.loads((work/f'{phase}.repetitions.json').read_text())['repetitions'];row[phase+'_repetitions']=repetitions
     row[phase]={'seconds':statistics.median(r['seconds'] for r in repetitions),'peak_rss_kib':max(r['peak_rss_kib'] for r in repetitions),'min_seconds':min(r['seconds'] for r in repetitions),'max_seconds':max(r['seconds'] for r in repetitions),'mad_seconds':statistics.median(abs(r['seconds']-statistics.median(x['seconds'] for x in repetitions)) for r in repetitions)}
    for rep in row['decode_repetitions']:
     restored=work/f'restored.rep{rep["index"]}.bin';assert restored.read_bytes()==original
     assert rep['sha256']==row['input_sha256']
    codec=work/'primary.codec.json'
    if codec.exists():row['codec']=json.loads(codec.read_text())
    row['size_range_bytes']=[min(r['bytes'] for r in row['encode_repetitions']),max(r['bytes'] for r in row['encode_repetitions'])]
  rows.append(row)
 (AREA/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
 return rows

def run():
 cells=json.loads((AREA/'cells.json').read_text());scheduler=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
 # Resume by durable terminal records, never relaunch an existing experiment.
 cells=[c for c in cells if not scheduler._terminal_path(c['cell_id']).exists()]
 while cells:
  wave=[];cpus=set()
  for c in cells:
   cpu=json.loads(Path(c['manifest_path']).read_text())['budget']['cpu']
   if cpu not in cpus:wave.append(c);cpus.add(cpu)
   if len(wave)==4:break
  results=scheduler.run_wave(wave)
  for c in wave:cells.remove(c)
  rows=collect();print(json.dumps({'completed':len(rows)-sum(r['status']=='PENDING' for r in rows),'remaining':len(cells),'verified':sum(r['status']=='VERIFIED_SCREENING' for r in rows),'wave':[{'input':c['label'],**c['configuration']} for c in wave],'status':[r.get('runner_status',r.get('status')) for r in results]}),flush=True)
  if any(r['status']=='FAILED' for r in rows):raise RuntimeError('Settings wave stopped after failed verification/command/budget; preserve and inspect')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['prepare','run','collect']);a=p.parse_args()
 if a.operation=='prepare':prepare()
 elif a.operation=='run':run()
 else:print(json.dumps({'rows':len(collect())}))
