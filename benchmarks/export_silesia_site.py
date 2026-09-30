#!/usr/bin/env python3
"""Export only frozen official Silesia results to the existing benchmark Site."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'docs/research/2026-10-01-complete-benchmarks/silesia-v3'
SITE=ROOT.parent/'cix-benchmark-site'
DATA=SITE/'dist/data'
SOURCE='https://mattmahoney.net/dc/silesia.html'
METHODS=['cix','gzip','bzip2','zstd','xz','brotli','paq8px']
PROFILES=['current','fast','size']
NAMES={'cix':'CIX','gzip':'gzip','bzip2':'bzip2','zstd':'Zstandard','xz':'XZ / LZMA2','brotli':'Brotli','paq8px':'paq8px'}
PROFILE_LABELS={'current':'Current','fast':'Speed extreme','size':'Size extreme'}
PRESETS={
 'fast':{'cix':'CIX bounded portfolio · fast','gzip':'gzip -1','bzip2':'bzip2 -1','zstd':'zstd --fast=131072','xz':'XZ preset 0','brotli':'Brotli quality 0','paq8px':'paq8px v216 -1 · AVX2'},
 'current':{'cix':'CIX bounded portfolio · balanced','gzip':'gzip -9','bzip2':'bzip2 -9','zstd':'zstd -3','xz':'XZ preset 6','brotli':'Brotli quality 6','paq8px':'paq8px v216 -8 · AVX2'},
 'size':{'cix':'CIX exhaustive bounded portfolio · maximum','gzip':'gzip -9','bzip2':'bzip2 -9','zstd':'zstd --ultra -22','xz':'XZ preset 9 extreme','brotli':'Brotli quality 11','paq8px':'NOT RUN · estimated 29 GB RAM > 12 GB cap'}}

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def scrub(value):
 if isinstance(value,str):
  return value.replace(str(ROOT),'.').replace('/home/user/src/cix-benchmark-site','SITE_ROOT')
 if isinstance(value,list):return [scrub(v) for v in value]
 if isinstance(value,dict):return {k:scrub(v) for k,v in value.items()}
 return value

def timevalue(row,key):
 value=row.get(key)
 return value.get('seconds') if isinstance(value,dict) else None

def normalized_status(row):
 status=row['status']
 if status!='FAILED':return status
 record=row.get('failure') or {}
 phases=record.get('phases') or []
 stops=[p.get('stop_reason') for p in phases if isinstance(p,dict) and p.get('stop_reason')]
 if any('wall_budget_exhausted' in s for s in stops):return 'TIME_BUDGET'
 if any('temp_budget_exhausted' in s or 'memory' in s.lower() for s in stops):return 'RESOURCE_LIMIT'
 return status

def rss_mib(row,key):
 receipt=Path(row['receipt']) if row.get('receipt') else None
 if not receipt or not receipt.is_file():return None
 r=json.loads(receipt.read_text());phase_name='encode' if key=='encode_rss_mib' else 'decode'
 phase=next((p for p in r.get('phases',[]) if p.get('phase','').endswith('-'+phase_name)),None)
 if not phase:return None
 # cgroup sampled high-water is a lower bound; label remains explicit in UI.
 b=phase.get('sampled_cgroup_memory_high_water_bytes')
 return b/(1024*1024) if b else None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--research-area',type=Path,default=AREA);ap.add_argument('--site',type=Path,default=SITE);a=ap.parse_args()
 area=a.research_area.resolve();site=a.site.resolve();data_dir=site/'dist/data';data_dir.mkdir(parents=True,exist_ok=True)
 cov=json.loads((area/'coverage.json').read_text());raw=json.loads((area/'results.json').read_text())
 retry_path=area/'cix-resource-retries-v1/results.json'
 retry=json.loads(retry_path.read_text()) if retry_path.is_file() else None
 retry_by_original={r['retry_of_cell_id']:r for r in (retry or {}).get('rows',[])}
 cancellation_path=area/'cancellation.json';cancellation=json.loads(cancellation_path.read_text()) if cancellation_path.is_file() else None
 members=cov['members'];rows=[]
 receipts=data_dir/'receipts';receipts.mkdir(exist_ok=True)
 for original in raw['rows']:
  r0=dict(original);retry_row=retry_by_original.get(r0['cell_id'])
  if retry_row and retry_row['status']=='VERIFIED_SCREENING':
   r0.update(retry_row)
   r0['superseded_attempt']={'cell_id':original['cell_id'],'status':original['status'],
      'old_temp_limit_bytes':100_000_000,'failure_reason':'temp_budget_exhausted'}
  r=dict(r0);member=next(m for m in members if m['label']==r['label']);profile=r['profile'];method=r['method']
  status=normalized_status(r)
  out={'dataset':member['id'],'method':method,'profile':profile,'status':status,'reason':r.get('reason'),
    'original_bytes':member['length'],'input_sha256':member['sha256'],'repetitions':1,'preset':PRESETS[profile][method],
    'configuration':{'method':method,'profile':profile,'settings':r.get('configuration',PRESETS[profile][method]),'sample_count':1,'warmups':0},
    'encode_seconds':timevalue(r,'encode'),'decode_seconds':timevalue(r,'decode'),'encode_rss_mib':rss_mib(r,'encode_rss_mib'),'decode_rss_mib':rss_mib(r,'decode_rss_mib'),
    'receipt':None,'archive_sha256':r.get('archive_sha256'),'verification':r.get('verification')}
  if status=='VERIFIED_SCREENING':
   receipt=Path(r['receipt']);receipt=receipt if receipt.is_absolute() else area/receipt
   doc=json.loads(receipt.read_text());archive=Path(doc['artifacts']['archive']);restored=Path(doc['artifacts']['restored'])
   if not archive.is_file() or digest(archive)!=r['archive_sha256'] or archive.stat().st_size!=r['archive_bytes']:
    raise RuntimeError(f"archive readback failed: {r['label']} {profile} {method}")
   if not restored.is_file() or digest(restored)!=member['sha256'] or restored.stat().st_size!=member['length']:
    raise RuntimeError(f"restoration readback failed: {r['label']} {profile} {method}")
   out['status']='VERIFIED';out['compressed_bytes']=r['archive_bytes'];out['archive_sha256']=r['archive_sha256']
   out['ratio']=member['length']/r['archive_bytes'];out['compressed_percent']=r['archive_bytes']/member['length']*100
   out['saving_percent']=(1-r['archive_bytes']/member['length'])*100
   out['encode_mib_s']=member['length']/1048576/out['encode_seconds'] if out['encode_seconds'] else None
   out['decode_mib_s']=member['length']/1048576/out['decode_seconds'] if out['decode_seconds'] else None
   out['encode_command']=scrub(doc['phases'][0]['command']);out['decode_command']=scrub(doc['phases'][1]['command'])
   out['receipt']=f'data/receipts/{member["name"]}-{profile}-{method}.json'
   target=receipts/f'{member["name"]}-{profile}-{method}.json';target.write_text(json.dumps(scrub(doc),indent=2)+'\n')
   if r.get('retry_of_cell_id'):
    out['resource_retry']={'retry_cell_id':r['cell_id'],'supersedes_cell_id':r['retry_of_cell_id'],
      'temporary_space_limit_bytes':r['budget']['max_temp_bytes'],'previous_temporary_space_limit_bytes':100_000_000,
      'note':'CIX-only retry; same input, implementation and profile with a larger temporary-space allowance.'}
  else:
   out['compressed_bytes']=None;out['ratio']=None;out['compressed_percent']=None;out['saving_percent']=None;out['encode_mib_s']=None;out['decode_mib_s']=None
   out['encode_command']=None;out['decode_command']=None
   if r.get('failure'):
    out['reason']=r['failure'].get('verification',{}).get('error') or r.get('reason') or 'Run did not produce a verified archive; see private run record.'
  rows.append(out)
 for member in members:
  for profile in PROFILES:
   group=[x for x in rows if x['dataset']==member['id'] and x['profile']==profile and x['status']=='VERIFIED']
   group.sort(key=lambda x:(x['compressed_bytes'],METHODS.index(x['method'])))
   for i,x in enumerate(group):x['size_rank']=i+1;x['measured_methods']=len(group)
   for x in rows:
    if x['dataset']==member['id'] and x['profile']==profile:
     x.setdefault('size_rank',None);x.setdefault('measured_methods',len(group))
 datasets=[]
 for m in members:
  datasets.append({'id':m['id'],'name':m['name'],'file':m['name'],'datatype':m['datatype'],'collection':'Silesia','source':SOURCE,
    'scope':'Complete official Silesia member','stratum':'official-silesia','original_bytes':m['length'],'offset':0,'sha256':m['sha256'],
    'note':f"Publisher MD5 {m['publisher_md5']} verified before run; local SHA-256 identifies these exact bytes."})
 methods=[
  {'id':'cix','name':'CIX','settings':'Adaptive portfolio','version':'CIXB1 + frozen CIXG1','kind':'Adaptive hybrid','note':'Tests direct original-byte routes for the six reference methods, then eligible native CIX routes; keeps the smallest exact-verified complete archive within each profile budget.'},
  {'id':'gzip','name':'gzip','settings':'Profile-specific levels','version':'Python 3.12.3 / zlib 1.3','kind':'Reference','note':'Original bytes; gzip archive size is compared as a standalone reference.'},
  {'id':'bzip2','name':'bzip2','settings':'Profile-specific levels','version':'Python 3.12.3 / libbz2','kind':'Reference','note':'Original bytes; bzip2 archive size is compared as a standalone reference.'},
  {'id':'zstd','name':'Zstandard','settings':'Profile-specific levels · single-thread','version':'Pinned CLI v1.5.5','kind':'Reference','note':'Original bytes; no external dictionary.'},
  {'id':'xz','name':'XZ / LZMA2','settings':'Profile-specific presets','version':'Python 3.12.3 / liblzma','kind':'Reference','note':'Original bytes; standalone archive.'},
  {'id':'brotli','name':'Brotli','settings':'Profile-specific quality','version':'Pinned Python Brotli 1.2.0','kind':'Reference','note':'Original bytes; standard Brotli format and built-in format dictionary where used.'},
  {'id':'paq8px','name':'paq8px','settings':'-1 / -8 / -12L 5 layers','version':'Pinned v216 · AVX2','kind':'Reference','note':'Original bytes; size maximum preset excluded before launch because estimated 29 GB working memory exceeds the 12 GB wave limit.'}]
 profiles=[{'id':p,'name':PROFILE_LABELS[p],'note':('One complete encode/decode sample per cell; times include process startup and I/O. CIX evaluates its declared candidate set under a finite profile budget. PAQ size profile excluded at 29 GB estimated RAM.' if p=='size' else 'One complete encode/decode sample per cell; times include process startup and I/O. CIX candidate selection time includes all attempted routes and failed/timeout trials. These are observed single-run timings, not repeated-run estimates.')} for p in ('current','fast','size')]
 profile_lookup={p:{m:PRESETS[p][m] for m in METHODS} for p in PROFILES}
 results={'schema':3,'title':'CIX · Silesia encoder benchmark','exported_at':datetime.now(timezone.utc).isoformat(),'last_measurement_at':raw['collected_at'],
   'run_status':'CANCELLED_BY_USER' if cancellation else 'IN_PROGRESS',
   'run_summary':{'declared_cells':len(rows),'verified':sum(r['status']=='VERIFIED' for r in rows),'failed':sum(r['status']=='FAILED' for r in rows),'time_budget':sum(r['status']=='TIME_BUDGET' for r in rows),'cancelled':sum(r['status']=='CANCELLED_BY_USER' for r in rows),'pending':sum(r['status']=='PENDING' for r in rows),'resource_limit':sum(r['status']=='RESOURCE_LIMIT' for r in rows),'cix_resource_retries_verified':sum(bool(r.get('resource_retry')) for r in rows)},
   'cutoff':'Silesia-only benchmark; 12 complete official members; acquisition closed','research_commit':json.loads((area/'environment.json').read_text())['cix_commit'],
   'source_url':SOURCE,'total_input_bytes':sum(m['length'] for m in members),'methods':methods,'profiles':profiles,'presets':profile_lookup,
   'datasets':datasets,'results':rows,'collections':[{'name':'Silesia official corpus','source':SOURCE,'status':'READY','ready_artifacts':len(members),'bytes':sum(m['length'] for m in members),'note':'All 12 official files; publisher MD5s verified and local SHA-256s recorded.'}],
   'limitations':['Silesia only: no conclusions for other datasets or compression competitions.','One cold encode and one archive-only decode per row; timing rankings are provisional single observations.','PAQ -12L five-layer size preset is prelaunch resource-excluded at an estimated 29 GB RAM versus the 12 GB shared ceiling.','Per-process working-memory values are cgroup sampled high-water lower bounds, not exact peak RSS.','CIX candidates are bounded by profile budgets; a timeout is unqualified and does not prove a candidate is larger.','CIXB1 wraps selected reference streams with 47 bytes of dispatch, length and source-digest metadata; that overhead is counted.','Seven CIX-only rows (Mozilla fast/current/size, NCI fast/current/size, Samba fast) were rerun after increasing the temporary-space limit from 100 MB to 1 GB. Their original attempts remain preserved in private raw evidence; no other method or dataset was rerun.',*([f"Matrix stopped at user request: {sum(r['status']=='CANCELLED_BY_USER' for r in rows)} cells cancelled; {sum(r['status']=='VERIFIED' for r in rows)} rows completed and verified. Incomplete cells are not ranked."] if cancellation else [])],
   'cix_commit':json.loads((area/'environment.json').read_text())['cix_commit'],'dataset_manifest':'data/silesia-manifest.json','results_csv':'data/results.csv'}
 (data_dir/'benchmarks.json').write_text(json.dumps(results,indent=2)+'\n')
 (data_dir/'silesia-manifest.json').write_text(json.dumps({'source':SOURCE,'publisher':'Matt Mahoney Silesia corpus','members':[{k:m[k] for k in ('name','length','sha256','publisher_md5','datatype','source')} for m in members],'publisher_checksum_verification':'All 12 publisher MD5 values checked against official list before matrix freeze; local SHA-256 is separately recorded.'},indent=2)+'\n')
 with (data_dir/'results.csv').open('w',newline='') as f:
  fields=['dataset','method','profile','status','original_bytes','compressed_bytes','ratio','compressed_percent','saving_percent','encode_seconds','decode_seconds','encode_mib_s','decode_mib_s','encode_rss_mib','decode_rss_mib','size_rank','input_sha256','archive_sha256','receipt','reason']
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r.get(k) for k in fields} for r in rows)
 shutil.copyfile(area/'environment.json',data_dir/'silesia-environment.json')
 shutil.copyfile(area/'coverage.json',data_dir/'silesia-coverage.json')
 if cancellation:shutil.copyfile(cancellation_path,data_dir/'silesia-cancellation.json')
 print(json.dumps({'site':str(site),'datasets':len(datasets),'rows':len(rows),'verified':sum(r['status']=='VERIFIED' for r in rows),'pending':sum(r['status']=='PENDING' for r in rows),'resource_limit':sum(r['status']=='RESOURCE_LIMIT' for r in rows),'exported_at':results['exported_at']},sort_keys=True))
if __name__=='__main__':main()
