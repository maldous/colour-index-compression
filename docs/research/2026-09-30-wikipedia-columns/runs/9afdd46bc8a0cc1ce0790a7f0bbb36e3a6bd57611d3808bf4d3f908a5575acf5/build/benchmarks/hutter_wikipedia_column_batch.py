#!/usr/bin/env python3
"""Execute only predeclared column-study manifests with bounded CPU lanes."""
import argparse,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'docs/research/2026-09-30-wikipedia-columns'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',required=True,choices=('small','dev0'));a=p.parse_args()
 manifests=sorted((FOLDER/'manifests').glob(a.phase+'-*.json'))
 if not manifests:raise ValueError('no predeclared manifests')
 budgets=[json.loads(x.read_text())['budget']['cpu'] for x in manifests]
 if len(set(budgets))!=len(budgets) or len(budgets)>4:raise ValueError('CPU overlap or oversubscription')
 logdir=FOLDER/'launcher-logs';logdir.mkdir(exist_ok=True);active=[];failed=False;started=time.monotonic();next_progress=started
 try:
  for m,cpu in zip(manifests,budgets):
   log=(logdir/(m.stem+'.log')).open('a')
   cmd=['taskset','-c',str(cpu),sys.executable,str(ROOT/'benchmarks/hutter_bounded_runner.py'),'--manifest',str(m),'--results',str(FOLDER/'runs'),'--root',str(ROOT)]
   active.append((m,subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=log),log))
  while active:
   for item in list(active):
    m,process,log=item
    if process.poll() is not None:
     log.close();active.remove(item)
     lines=(logdir/(m.stem+'.log')).read_text().splitlines()
     try:r=json.loads(lines[-1])
     except (ValueError,IndexError):r={'status':'LAUNCH_FAILED'}
     failed|=r['status'] not in ('VERIFIED_SCREENING','REUSED_VERIFIED','SIZE_REJECTED_UNVERIFIED')
     print(json.dumps({'manifest':m.name,'status':r['status'],'archive_bytes':r.get('archive_bytes'),'experiment_id':r.get('experiment_id')}),flush=True)
   if time.monotonic()>=next_progress:
    print(json.dumps({'phase':a.phase,'elapsed_seconds':round(time.monotonic()-started,1),'active':[m.stem for m,_,_ in active]}),flush=True);next_progress+=30
   if active:time.sleep(1)
 finally:
  for _,process,_ in active:process.terminate()
  for _,process,log in active:
   try:process.wait(timeout=20)
   except subprocess.TimeoutExpired:process.kill();process.wait()
   log.close()
 return int(failed)
if __name__=='__main__':raise SystemExit(main())
