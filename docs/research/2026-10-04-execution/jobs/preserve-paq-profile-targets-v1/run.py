#!/usr/bin/env python3
"""Lease-gated, two-root cache preservation using the reviewed XZ helper."""
from __future__ import annotations
import contextlib, hashlib, importlib.util, json, os, shutil, stat
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
WORK=ROOT/'benchmark-work/native-rc-check-v1'
OUT=Path(__file__).resolve().parent
LIMIT=4_000_000_000
SONAR=620_756_992
MARGIN=1_048_576
OUTPUT_CAP=80_000_000
PAQ=WORK/'paq-loader-slice1-v1/target'
PROFILE=WORK/'squashfs-profile-alignment-v2/cargo-target'
PRESERVED=WORK/'preserved-paq-profile-targets-v1'
PAQ_RECEIPT=PAQ.parent/'receipt.json'
PAQ_RAW=ROOT/'docs/research/2026-10-04-execution/jobs/paq-loader-slice1-v1/raw/result.json'
PROFILE_RECEIPT=PROFILE.parent/'receipt.json'
PROFILE_RAW=ROOT/'docs/research/2026-10-04-execution/jobs/squashfs-profile-alignment-v2/raw/result.json'
CIX='debug/cix'

spec=importlib.util.spec_from_file_location('verified_target_helper',ROOT/'docs/research/2026-10-04-execution/jobs/preserve-native-final-v3-target-v1/run.py')
helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def du():
 import subprocess
 return int(subprocess.check_output(['du','-sx','-B1',str(WORK)],text=True).split()[0])
def active(root):
 import subprocess
 r=subprocess.run(['lsof','+D',str(root)],text=True,capture_output=True)
 if r.returncode not in (0,1) or r.stdout.strip():raise RuntimeError('active or uninspectable target: '+str(root))
def terminal(receipt,raw):
 a=json.loads(receipt.read_text()); b=json.loads(raw.read_text())
 if a.get('status')!='pass' or b.get('exit_code')!=0 or b.get('child_status',{}).get('child_exit_code')!=0:raise RuntimeError('nonterminal prerequisite')
@contextlib.contextmanager
def bound(root,name,cap):
 old={k:getattr(helper,k) for k in ('WORK','TARGET','PRESERVED','ARCHIVE','MANIFEST','ARCHIVE_CAP','MANIFEST_CAP','RETAINED_BINARIES')}
 try:
  helper.WORK=WORK;helper.TARGET=root;helper.PRESERVED=PRESERVED/name;helper.ARCHIVE=helper.PRESERVED/'target.tar.xz';helper.MANIFEST=helper.PRESERVED/'manifest.json';helper.ARCHIVE_CAP=cap;helper.MANIFEST_CAP=4_000_000;helper.RETAINED_BINARIES={}
  yield
 finally:
  for k,v in old.items():setattr(helper,k,v)
def main():
 if os.environ.get('CIX_RELEASE_LEASE')!='1':raise RuntimeError('root scheduler lease required')
 if ROOT!=Path('/home/user/src/colour-index-compression') or PRESERVED.exists():raise RuntimeError('unexpected root or prior evidence')
 terminal(PAQ_RECEIPT,PAQ_RAW);terminal(PROFILE_RECEIPT,PROFILE_RAW)
 active(PAQ);active(PROFILE)
 if du()+OUTPUT_CAP>=LIMIT:raise RuntimeError('aggregate output cap cannot be admitted')
 inputs={str(p):sha(p) for p in (Path(__file__),Path(spec.origin),PAQ_RECEIPT,PAQ_RAW,PROFILE_RECEIPT,PROFILE_RAW)}
 records=[]; manifests=[]
 for root,name,cap in ((PAQ,'paq',60_000_000),(PROFILE,'profile',20_000_000)):
  with bound(root,name,cap):
   manifest,links=helper.collect_manifest();helper.PRESERVED.mkdir(parents=True,mode=0o700)
   if root==PAQ:
    src=root/CIX; row=next(x for x in manifest['entries'] if x['path']==CIX and x['type']=='file'); dst=PRESERVED/'cix'
    shutil.copy2(src,dst)
    if sha(dst)!=row['sha256'] or stat.S_IMODE(dst.stat().st_mode)!=row['mode']:raise RuntimeError('cix preservation failed')
   # Both archives, uncompressed manifests and the separate binary share one cap.
   used=sum(p.stat().st_size for p in PRESERVED.rglob('*') if p.is_file())
   helper.ARCHIVE_CAP=min(cap,OUTPUT_CAP-used-len(helper.encoded_manifest(manifest)))
   if helper.ARCHIVE_CAP<=0:raise RuntimeError('no archive capacity remains')
   helper.write_archive(manifest,links); archive_sha=helper.verify_archive(manifest)
   if not helper.unchanged(manifest):raise RuntimeError('target changed after archive')
   records.append({'root':str(root),'archive':str(helper.ARCHIVE),'archive_sha256':archive_sha,'archive_bytes':helper.ARCHIVE.stat().st_size,'manifest':str(helper.MANIFEST),'selected_allocated_bytes':manifest['selected_allocated_bytes']})
   manifests.append((root,name,cap,manifest))
 size=sum(p.stat().st_size for p in PRESERVED.rglob('*') if p.is_file())
 if size>OUTPUT_CAP:raise RuntimeError('combined preservation output exceeds cap')
 active(PAQ);active(PROFILE)
 for root,name,cap,manifest in manifests:
  with bound(root,name,cap):
   if not helper.unchanged(manifest):raise RuntimeError('target changed before reclaim')
 if any(sha(Path(p))!=value for p,value in inputs.items()):raise RuntimeError('preservation inputs changed')
 for item in records:shutil.rmtree(Path(item['root']))
 if PAQ.exists() or PROFILE.exists():raise RuntimeError('selected target removal incomplete')
 after=du(); receipt={'status':'pass','records':records,'inputs_sha256':inputs,'separate_cix_sha256':sha(PRESERVED/'cix'),'preservation_output_bytes':size,'retained_work_after_bytes':after,'sonar_admission':after+SONAR<=LIMIT,'sonar_reservation_bytes':SONAR}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':
 try:
  main()
 except Exception as error:
  (OUT/'receipt.json').write_text(json.dumps({'status':'failed','error':str(error),'paq_target':str(PAQ),'profile_target':str(PROFILE)},indent=2)+'\n')
  raise
