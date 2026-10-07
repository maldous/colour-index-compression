import json,hashlib,subprocess,os,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');base=root/'benchmark-work/closure-context';area=root/'docs/research/2026-10-03-rust-rnd/closure-queue/conditional-context-results';exe=base/'build/context'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={}
for case in ['strong','weak','absent']:
 p=base/(case+'.input');subprocess.run([str(exe),'generate',case,str(p)],check=True);inputs[case]={'bytes':p.stat().st_size,'sha256':sha(p)}
(area/'input-bindings.json').write_text(json.dumps({'before_encode':True,'binary_sha256':sha(exe),'inputs':inputs},indent=2)+'\n')
rows=[]
for case in inputs:
 for mode in ['global','context-1-4','context-2-8','raw']:
  stem=base/(case+'-'+mode);arc=stem.with_suffix('.arc');out=stem.with_suffix('.restored');row={'case':case,'mode':mode}
  for op,args in [('encode',[mode,case,str(arc)]),('decode',[str(arc),str(out)])]:
   log=stem.with_suffix('.'+op+'.time');v=subprocess.run(['/usr/bin/time','-v','-o',str(log),str(exe),op,*args],capture_output=True,text=True,timeout=60);(area/'raw'/(case+'-'+mode+'-'+op+'.stdout')).write_text(v.stdout);(area/'raw'/(case+'-'+mode+'-'+op+'.stderr')).write_text(v.stderr);(area/'raw'/log.name).write_bytes(log.read_bytes());assert v.returncode==0,v.stderr;row[op]=json.loads(v.stdout)
  assert sha(out)==inputs[case]['sha256'];row.update({'archive_bytes':arc.stat().st_size,'archive_sha256':sha(arc),'restored_sha256':sha(out)});rows.append(row)
  (area/'results.json').write_text(json.dumps({'status':'VERIFIED' if len(rows)==12 else 'PARTIAL','rows':rows},indent=2)+'\n')
arc=base/'strong-global.arc';valid=arc.read_bytes();badrows=[]
for name,data in [('header',bytes([valid[0]^1])+valid[1:]),('truncation',valid[:-1])]:
 p=base/(name+'.bad');p.write_bytes(data);v=subprocess.run([str(exe),'reject',str(p)],capture_output=True,text=True);assert v.returncode==0;badrows.append({'case':name,'reject_exit':v.returncode,'stdout':v.stdout,'stderr':v.stderr})
(area/'malformed.json').write_text(json.dumps(badrows,indent=2)+'\n')
