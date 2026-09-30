#!/usr/bin/env python3
"""Frozen full-member Silesia comparisons across the seven-method table."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.codec_profiles import SETTINGS,digest
from benchmarks.hutter_bounded_runner import build_identity,canonical,load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

ROOT=Path(__file__).resolve().parents[1]
INPUTS=ROOT/'results/silesia-manifest.json';POLICY=ROOT/'docs/research/2026-09-30-codec-profiles/policy.json'
AREA=ROOT/'docs/research/2026-10-01-complete-benchmarks/silesia-v3'
METHODS=('cix','gzip','bzip2','zstd','xz','brotli','paq8px');PROFILES=('fast','current','size')
INFO={
 'dickens':('English novels · ASCII plain text','https://mattmahoney.net/dc/silesia.html'),
 'mozilla':('Program, UNIX executables and others · tar','https://mattmahoney.net/dc/silesia.html'),
 'mr':('3-D MRI image · DICOM','https://mattmahoney.net/dc/silesia.html'),
 'nci':('Chemical database · text','https://mattmahoney.net/dc/silesia.html'),
 'ooffice':('Windows DLL','https://mattmahoney.net/dc/silesia.html'),
 'osdb':('Synthetic database · binary','https://mattmahoney.net/dc/silesia.html'),
 'reymont':('Polish text · uncompressed PDF','https://mattmahoney.net/dc/silesia.html'),
 'samba':('Source code and graphics · tar','https://mattmahoney.net/dc/silesia.html'),
 'sao':('Star catalog database · binary','https://mattmahoney.net/dc/silesia.html'),
 'webster':('English dictionary · HTML','https://mattmahoney.net/dc/silesia.html'),
 'x-ray':('16-bit grayscale · DICOM','https://mattmahoney.net/dc/silesia.html'),
 'xml':('XML files · text · tar','https://mattmahoney.net/dc/silesia.html')}
PUBLISHER_MD5={
 'dickens':'88334708559f6db57d79096bc0aca07e','mozilla':'c7789a2097f1ff944b0c737430a339b3',
 'mr':'38e623e3093b7bf2003ca4b1bbc19927','nci':'31f85bc8706f3c921104e7c169e2e2e1',
 'ooffice':'573c4ae915e36631d8f2dcffb9b9b66d','osdb':'e734b0c48e6a982adfb5802da3032ecd',
 'reymont':'d8f54d78105079775f32d76dc55fc671','samba':'154eaea7ea70e89f6339ff0abf4112ca',
 'sao':'79e95a22e18cd82b7e42bf91b380d30b','webster':'474931ad907ac27bf962c75ded46c069',
 'x-ray':'9baec32ad14ec3eff487d254382cb91c','xml':'9b09c0c80104adb8aae910b7d7db003e'}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def time_metrics(path):
 out={}
 for line in Path(path).read_text().splitlines():
  if 'Elapsed (wall clock)' in line:
   fields=list(map(float,line.split('):',1)[1].strip().split(':')));out['seconds']=sum(v*60**(len(fields)-i-1) for i,v in enumerate(fields))
  elif 'Maximum resident set size' in line:out['peak_rss_kib']=int(line.rsplit(':',1)[1])
  elif 'User time (seconds)' in line:out['user_seconds']=float(line.rsplit(':',1)[1])
  elif 'System time (seconds)' in line:out['system_seconds']=float(line.rsplit(':',1)[1])
 return out

def physical_cpus():
 result=[];seen=set()
 for cpu in sorted(os.sched_getaffinity(0)):
  p=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology');key=((p/'physical_package_id').read_text(),(p/'core_id').read_text())
  if key not in seen:result.append(cpu);seen.add(key)
  if len(result)==4:break
 return result

def prepare():
 if (AREA/'cells.json').exists():raise RuntimeError('Silesia v3 was already declared; never overwrite frozen identities')
 inputs=json.loads(INPUTS.read_text());
 if len(inputs)!=12:raise RuntimeError('The canonical Silesia manifest must contain exactly 12 full files')
 members=[]
 for x in inputs:
  p=Path(x['path']);name=p.name;raw=p.read_bytes()
  if name not in INFO or len(raw)!=x['size'] or sha(p)!=x['sha256'] or hashlib.md5(raw).hexdigest()!=PUBLISHER_MD5[name]:raise ValueError(f'Silesia identity/publisher MD5 mismatch: {name}')
  members.append({'id':'silesia-'+name,'label':'silesia-'+name,'name':name,'path':str(p.resolve()),'offset':0,
      'length':len(raw),'sha256':x['sha256'],'full_sha256':x['sha256'],'publisher_md5':PUBLISHER_MD5[name],
      'datatype':INFO[name][0],'source':INFO[name][1],'stratum':'complete-official-member'})
 if {x['name'] for x in members}!=set(INFO):raise RuntimeError('Silesia manifest member list differs from canonical 12')
 cpus=physical_cpus();mroot=AREA/'manifests';mroot.mkdir(parents=True,exist_ok=True)
 if any(mroot.iterdir()):raise RuntimeError('partial Silesia-v3 manifests exist; no overwrite')
 cells=[];coverage=[]
 for member in members:
  for profile in PROFILES:
   for method in METHODS:
    key={'method':method,'profile':profile,'settings':SETTINGS[profile][method],
         'repetitions':1,'warmups':0,'adapter_revision':'silesia-v3-source-arg-fix-all-six-cix'}
    if profile=='size' and method=='paq8px':
     coverage.append({'cell_id':'resource-'+hashlib.sha256((member['label']+'-size-paq8px').encode()).hexdigest()[:16],
       'label':member['label'],'profile':profile,'method':method,'input_bytes':member['length'],'input_sha256':member['sha256'],
       'status':'RESOURCE_LIMIT','reason':'Frozen paq8px v216 -12L five-LSTM-layer preset is estimated at about 29 GB, above the shared 12 GB RAM ceiling; not launched and no smaller substitute used.'})
     continue
    if method=='cix':
     leaf=str(ROOT/'benchmarks/silesia_single_cix.py');archive='{workdir}/candidate.cix'
     enc=['/usr/bin/time','-v','-o','{workdir}/encode.time.txt',sys.executable,leaf,'encode','{source}',archive,'--profile',profile,'--policy',str(POLICY),'--attempts','{workdir}/attempts']
     dec=['/usr/bin/time','-v','-o','{workdir}/decode.time.txt',sys.executable,leaf,'decode',archive,'{workdir}/restored.bin','--policy',str(POLICY)]
     build=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'cix').glob('*.py'))+[
       'benchmarks/silesia_single_cix.py','benchmarks/hutter_bounded_runner.py','benchmarks/hutter_experiment_scheduler.py',str(POLICY.relative_to(ROOT))]
    else:
     leaf=str(ROOT/'benchmarks/codec_profiles.py');archive='{workdir}/candidate.bin'
     flags=['--leaf','--method',method,'--profile',profile,'--policy',str(POLICY)]
     timing='{workdir}/encode.time.txt'
     enc=['/usr/bin/time','-v','-o',timing,sys.executable,leaf,'encode','{source}',archive,*flags]
     dec=['/usr/bin/time','-v','-o','{workdir}/decode.time.txt',sys.executable,leaf,'decode',archive,'{workdir}/restored.bin',*flags]
     build=['benchmarks/codec_profiles.py','benchmarks/hutter_bounded_runner.py','benchmarks/hutter_experiment_scheduler.py',str(POLICY.relative_to(ROOT))]
    config={'method':method,'profile':profile,'settings':SETTINGS[profile][method],
      'backend_identity':'CIX adaptive portfolio' if method=='cix' else 'exact direct reference preset',
      'repetitions':1,'warmups':0,'sample_policy':'one complete cold encode and one archive-only decode; no size/time selection among repetitions'}
    manifest={'hypothesis':'Produce one complete, byte-exact, same-run seven-method comparison for every original Silesia member at each declared speed/current/size preset.',
      'matched_control':'same complete official member SHA-256; one-core host and same 2 GB memory/100 MB temp/300 s phase caps; no cross-file state.',
      'input':{'path':member['path'],'offset':0,'length':member['length'],'sha256':member['sha256'],'full_asset_sha256':member['full_sha256'],'publisher_md5':member['publisher_md5'],'source':member['source'],'datatype':member['datatype']},
      'configuration':config,'initial_state':'empty encoder/decoder for every independent file; all route decisions/framing charged in archive size.',
      'mechanism':'CIX portfolio attempts all six direct backend methods when eligible, then its adaptive/native routes; direct rows encode unchanged input with the exact reference preset. Maximum-profile PAQ is explicitly excluded by the declared RAM ceiling. Each selected archive is independently decoded with the source path inaccessible to the decoder.',
      'budget':{'cpu':cpus[len(cells)%4],'max_rss_bytes':2_000_000_000,'max_temp_bytes':100_000_000,'wall_seconds':300,'swap_bytes':0},
      'stage':'screening','promotion_criteria':'Complete physical archive; decode uses archive plus pinned decoder/dependency policy only; exact length and SHA-256 restoration; incomplete/time/resource cases remain unranked.',
      'exposure':'Silesia is an established/repeated benchmark in this private project; not a fresh holdout. All 12 named members and canonical source SHA-256s are predeclared.',
      'encode_command':enc,'decode_command':dec,'artifacts':{'archive':archive,'restored':'{workdir}/restored.bin'},
      'build_paths':build,'resource_accounting':'One physical core; systemd cgroup MemoryMax 2,000,000,000; MemorySwapMax 0; work directory cap 100,000,000; phase wall max 300 seconds; aggregate 4 cores / 12 GB / 4 GB temp.'}
    mpath=mroot/f"{member['name']}-{profile}-{method}.json";mpath.write_bytes(canonical(manifest)+b'\n');_,msha=load_manifest(mpath)
    cell={'cell_id':'silesia3-'+hashlib.sha256(canonical({'input':member['sha256'],'config':config,'wave':'silesia-v3-source-arg-fix'})).hexdigest()[:16],
      'owner':'/root','manifest_path':str(mpath.relative_to(ROOT)),'output_dir':str((AREA/'runs'/f"{member['name']}-{profile}-{method}").relative_to(ROOT)),
      'fresh_justification':'The prior v2 attempt either had a malformed direct encode command or exercised CIX before its verified-fallback handling was fixed. This v3 build includes the source argument and corrected CIX six-codec integration; all output directories and cell IDs are new, and prior evidence remains unmodified.',
      'expected_manifest_sha256':msha,'expected_build_sha256':build_identity(manifest,ROOT),
      'label':member['label'],'profile':profile,'method':method,'input_bytes':member['length'],'input_sha256':member['sha256']}
    cells.append(cell);coverage.append(cell)
 (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n');(AREA/'coverage.json').write_text(json.dumps({'cells':coverage,'members':members,'manifest_sha256':digest(INPUTS)},indent=2)+'\n')
 (AREA/'environment.json').write_text(json.dumps({'frozen_at':datetime.now(timezone.utc).isoformat(),'cix_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
   'aggregate_limits':{'physical_cores':4,'ram_bytes':12_000_000_000,'temporary_bytes':4_000_000_000,'swap_bytes':0},
   'cell_limits':{'physical_cores':1,'rss_bytes':2_000_000_000,'temporary_bytes':100_000_000,'phase_wall_seconds':300},
   'member_count':len(members),'total_original_bytes':sum(x['length'] for x in members),'matrix_rows':len(coverage),
   'fresh_execution_rows':len(cells),'resource_exclusions':sum(x.get('status')=='RESOURCE_LIMIT' for x in coverage),
   'sample_count':1,'sample_policy':'One complete encode and one archive-only decode per codec/member/profile; no warmup, cache state may vary; raw timings and resources retained.',
   'members':members,'profiles':{p:{m:SETTINGS[p][m] for m in METHODS} for p in PROFILES},
   'references':{'official_silesia':'https://mattmahoney.net/dc/silesia.html','old_measured_six_method_reference':'results/leaderboard/silesia-speed-reference-20260928/complete.json (kept as separately-versioned historical comparison, not silently merged)'},
   'limitations':['PAQ maximum (-12L, five LSTM layers) excluded prelaunch on RAM; fast/current PAQ candidates remain bounded and may time out.','CIX tests all eligible direct reference routes plus native routes under finite budgets; fast/current are bounded and do not guarantee exhaustive search.','One encode/decode sample gives measurements, not stable timing estimates.'],
   'cca_status':'The broader CCA full-file wave was cancelled on explicit user scope change; completed results and cancellation ledger remain in the CCA-v4 area.'},indent=2)+'\n')
 print(json.dumps({'members':len(members),'input_bytes':sum(x['length'] for x in members),'coverage_rows':len(coverage),'scheduled':len(cells),'resource_exclusions':sum(x.get('status')=='RESOURCE_LIMIT' for x in coverage),'cpus':cpus},sort_keys=True),flush=True)

def collect():
 cov=json.loads((AREA/'coverage.json').read_text());rows=[];scheduler=WaveScheduler(ROOT)
 for c in cov['cells']:
  if c.get('status')=='RESOURCE_LIMIT':rows.append({k:c[k] for k in ('cell_id','label','profile','method','input_bytes','input_sha256','status','reason')});continue
  row={k:c[k] for k in ('cell_id','label','profile','method','input_bytes','input_sha256')};row['status']='PENDING'
  tp=scheduler._terminal_path(c['cell_id'])
  if tp.exists():
   t=json.loads(tp.read_text());res=t.get('runner_result',{});rp=res.get('receipt')
   row['scheduler_status']=t.get('runner_status')
   if rp and Path(rp).is_file():
    r=json.loads(Path(rp).read_text());terminal_status=r['status']
    if terminal_status=='FAILED':
     stops=[p.get('stop_reason') for p in (r.get('phases') or []) if p.get('stop_reason')]
     if any('wall_budget_exhausted' in x for x in stops):terminal_status='TIME_BUDGET'
     elif any('temp_budget_exhausted' in x or 'memory' in x.lower() for x in stops):terminal_status='RESOURCE_LIMIT'
    row.update(status=terminal_status,archive_bytes=r.get('archive_bytes'),archive_sha256=r.get('archive_sha256'),verification=r.get('verification'),phases=r.get('phases'),budget=r.get('budget'),receipt=rp)
    w=Path(rp).parent/'work'
    if c['method']=='cix' and (w/'attempts').exists():
     # CIX adapter emits the selector and complete candidate accounting to stdout; retain stdout as a sidecar too.
     row['candidate_summary']=r.get('codec')
    for phase in ('encode','decode'):
     f=w/f'{phase}.time.txt'
     if f.exists():row[phase]=time_metrics(f);row[phase+'_time_log']=str(f)
    if c['method']=='cix' and r.get('phases'):
     log=Path(rp).parent/(r['phases'][0]['phase']+'.stdout.log')
     if log.is_file():
      try:row['candidate_summary']=json.loads(log.read_text().strip().splitlines()[-1])
      except (json.JSONDecodeError,IndexError):row['candidate_summary_error']='CIX candidate summary log was not valid JSON'
   else:row.update(status=t.get('runner_status','FAILED'),failure=res)
  rows.append(row)
 counts={}
 for r in rows:counts[r['status']]=counts.get(r['status'],0)+1
 (AREA/'results.json').write_text(json.dumps({'collected_at':datetime.now(timezone.utc).isoformat(),'counts':counts,'rows':rows,'members':cov['members']},indent=2)+'\n')
 print(json.dumps({'rows':len(rows),'counts':counts,'pending':counts.get('PENDING',0)},sort_keys=True),flush=True)

def run():
 cells=json.loads((AREA/'cells.json').read_text());sched=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
 pending=[c for c in cells if not sched._terminal_path(c['cell_id']).exists()]
 while pending:
  wave=[];cores=set()
  for c in pending:
   m,_=load_manifest(ROOT/c['manifest_path']);cpu=m['budget']['cpu'];p=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology');key=((p/'physical_package_id').read_text(),(p/'core_id').read_text())
   if key not in cores:wave.append(c);cores.add(key)
   if len(wave)==4:break
  out=sched.run_wave(wave)
  for c in wave:pending.remove(c)
  print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'remaining':len(pending),'cells':[{'input':c['label'],'profile':c['profile'],'method':c['method']} for c in wave],'statuses':[x['runner_status'] for x in out]},sort_keys=True),flush=True)
  collect()
 collect()

def main():
 p=argparse.ArgumentParser();p.add_argument('op',choices=['prepare','run','collect']);a=p.parse_args()
 {'prepare':prepare,'run':run,'collect':collect}[a.op]()
if __name__=='__main__':main()
