from pathlib import Path
import json,subprocess,time,hashlib
from oracle import rhc
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';WORK=ROOT/'benchmark-work/record-exceptions';rows=[]
for row in json.loads((AREA/'results.json').read_text()):
 f=row['fixture'];name=f['name'];inp=Path(f['input']);arc=WORK/'archives'/(name+'-histogram-auto.arc');out=arc.with_suffix('.restored');runs={}
 for mode,args in [('encode',[str(WORK/'build/rhc'),'encode',str(inp),str(arc)]),('decode',[str(WORK/'build/rhc'),'decode',str(arc),str(out)])]:
  start=time.monotonic()
  with (AREA/'raw'/(name+'-histogram-auto-'+mode+'.stdout')).open('wb')as stdout,(AREA/'raw'/(name+'-histogram-auto-'+mode+'.stderr')).open('wb')as stderr:
   cp=subprocess.run(['/usr/bin/time','-v','-o',str(AREA/'raw'/(name+'-histogram-auto-'+mode+'.time')),*args],stdout=stdout,stderr=stderr,timeout=20)
  assert cp.returncode==0;runs[mode]=dict(args=args,exit=cp.returncode,wall_seconds=time.monotonic()-start)
 assert out.read_bytes()==inp.read_bytes();rows.append(dict(name=name,archive=str(arc),bytes=arc.stat().st_size,archive_sha256=hashlib.sha256(arc.read_bytes()).hexdigest(),restored_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),oracle=rhc(arc,inp.read_bytes()),**runs))
(AREA/'histogram-auto-results.json').write_text(json.dumps(rows,indent=2)+'\n')
(AREA/'final-artifact-binding.json').write_text(json.dumps(dict(artifacts={str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in sorted(WORK.rglob('*'))if p.is_file()}),indent=2)+'\n')
print('qualified',len(rows),'automatichistogram controls',flush=True)
