"""Pinned settings comparisons, independent repetitions and archive-only decoding.

This adapter changes settings, never the frozen CIX implementation. It is run
inside the established no-swap bounded runner's immutable build snapshot.
"""
from __future__ import annotations
import argparse,bz2,gzip,hashlib,json,lzma,os,shutil,statistics,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

SETTINGS={
 'current':{'cix':{'effort':'balanced'},'gzip':{'level':9},'bzip2':{'level':9},'xz':{'level':6},'brotli':{'level':6},'zstd':{'level':3},'paq8px':{'option':'-8'}},
 'fast':{'cix':{'effort':'fast'},'gzip':{'level':1},'bzip2':{'level':1},'xz':{'level':0},'brotli':{'level':0},'zstd':{'level':-131072},'paq8px':{'option':'-1'}},
 'size':{'cix':{'effort':'maximum'},'gzip':{'level':9},'bzip2':{'level':9},'xz':{'level':9,'extreme':True},'brotli':{'level':11},'zstd':{'level':22},'paq8px':{'option':'-12L','layers':5}},
}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def time_metrics(path):
 result={}
 for line in Path(path).read_text().splitlines():
  if 'Elapsed (wall clock)' in line:
   fields=list(map(float,line.split('):',1)[1].strip().split(':')));result['seconds']=sum(v*60**(len(fields)-i-1) for i,v in enumerate(fields))
  elif 'Maximum resident set size' in line:result['peak_rss_kib']=int(line.rsplit(':',1)[1])
  elif 'User time (seconds)' in line:result['user_seconds']=float(line.rsplit(':',1)[1])
  elif 'System time (seconds)' in line:result['system_seconds']=float(line.rsplit(':',1)[1])
 return result

def leaf(a):
 setting=SETTINGS[a.profile][a.method]
 if a.operation=='encode':a.destination.unlink(missing_ok=True)
 if a.method=='cix':
  from cix.pipeline import encode_file,decode_file
  report=encode_file(a.source,a.destination,effort=setting['effort'],trace_path=a.destination.with_suffix('.blocks.jsonl')) if a.operation=='encode' else decode_file(a.source,a.destination)
  a.destination.with_suffix('.codec.json').write_text(json.dumps(report,indent=2)+'\n');return
 if a.method=='zstd':
  binary=a.policy['zstd']['path'];assert digest(binary)==a.policy['zstd']['sha256']
  args=[binary,'--single-thread','--no-asyncio','-q','-f']
  if a.operation=='encode':args+=['--ultra','-22'] if setting['level']==22 else ['--fast='+str(-setting['level'])] if setting['level']<0 else ['-'+str(setting['level'])]
  else:args+=['-d']
  subprocess.run(args+[str(a.source),'-o',str(a.destination)],check=True);return
 if a.method=='paq8px':
  original=Path(a.policy['paq8px']['path']);assert digest(original)==a.policy['paq8px']['sha256']
  # Runner snapshots deliberately chmod declared builds read-only. Make an
  # executable working copy, pinned by hash, rather than use mutable source.
  binary=a.destination.parent/'paq8px-pinned'
  if not binary.exists():shutil.copyfile(original,binary);binary.chmod(0o555)
  assert digest(binary)==a.policy['paq8px']['sha256']
  args=[str(binary),setting['option']] if a.operation=='encode' else [str(binary),'-d']
  if a.operation=='encode' and setting.get('layers'):args+=['-lstmlayers='+str(setting['layers'])]
  args+=['-simd','AVX2',str(a.source),str(a.destination)]
  subprocess.run(args,check=True);return
 data=a.source.read_bytes();enc=a.operation=='encode'
 if a.method=='gzip':out=gzip.compress(data,compresslevel=setting['level'],mtime=0) if enc else gzip.decompress(data)
 elif a.method=='bzip2':out=bz2.compress(data,compresslevel=setting['level']) if enc else bz2.decompress(data)
 elif a.method=='xz':out=lzma.compress(data,preset=setting['level']|(lzma.PRESET_EXTREME if setting.get('extreme') else 0)) if enc else lzma.decompress(data)
 elif a.method=='brotli':
  import brotli
  out=brotli.compress(data,quality=setting['level']) if enc else brotli.decompress(data)
 else:raise ValueError('unknown method')
 a.destination.write_bytes(out)

def repetitions(a):
 work=a.destination.parent
 report=[]
 base=[sys.executable,str(Path(__file__).resolve()),a.operation,'--leaf','--method',a.method,'--profile',a.profile,'--policy',str(a.policy_path)]
 if a.operation=='encode':
  warm=work/'warmup.bin';subprocess.run(base+[str(a.source),str(warm)],check=True);warm.unlink()
  for i in range(3):
   dst=work/f'archive.rep{i}.bin';timing=work/f'encode.rep{i}.time.txt'
   started=time.perf_counter();cmd=['/usr/bin/time','-v','-o',str(timing),*base,str(a.source),str(dst)]
   subprocess.run(cmd,check=True)
   report.append(dict(index=i,archive=dst.name,bytes=dst.stat().st_size,sha256=digest(dst),process_wall_seconds=time.perf_counter()-started,command=cmd,**time_metrics(timing)))
  # Predeclared primary artifact: middle size, tie by repetition index. All
  # measurements and streams retained; no best-repetition selection.
  index=sorted(range(3),key=lambda i:(report[i]['bytes'],i))[1]
  shutil.copyfile(work/report[index]['archive'],a.destination)
  codec=(work/report[index]['archive']).with_suffix('.codec.json')
  if codec.exists():shutil.copyfile(codec,work/'primary.codec.json')
  report_path=work/'encode.repetitions.json';report_path.write_text(json.dumps(dict(warmups=1,repetitions=report,primary_index=index,primary_rule='median physical size; ties by repetition index'),indent=2)+'\n')
 else:
  records=json.loads((work/'encode.repetitions.json').read_text())
  warm=work/'warmup.restored';subprocess.run(base+[str(a.source),str(warm)],check=True);warm.unlink()
  for i in range(3):
   src=work/records['repetitions'][i]['archive'];dst=work/f'restored.rep{i}.bin';timing=work/f'decode.rep{i}.time.txt'
   started=time.perf_counter();cmd=['/usr/bin/time','-v','-o',str(timing),*base,str(src),str(dst)]
   subprocess.run(cmd,check=True)
   report.append(dict(index=i,bytes=dst.stat().st_size,sha256=digest(dst),process_wall_seconds=time.perf_counter()-started,command=cmd,**time_metrics(timing)))
  assert len({(r['bytes'],r['sha256']) for r in report})==1,'repetition decoding differs'
  shutil.copyfile(work/f'restored.rep{records["primary_index"]}.bin',a.destination)
  (work/'decode.repetitions.json').write_text(json.dumps(dict(warmups=1,repetitions=report),indent=2)+'\n')
 print(json.dumps({'phase':a.operation,'method':a.method,'profile':a.profile,'repetitions':3}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['encode','decode']);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--method',required=True);p.add_argument('--profile',required=True);p.add_argument('--policy',required=True,type=Path);p.add_argument('--leaf',action='store_true');a=p.parse_args()
 a.policy_path=a.policy;a.policy=json.loads(a.policy.read_text())
 if a.leaf:leaf(a)
 else:repetitions(a)
if __name__=='__main__':main()
