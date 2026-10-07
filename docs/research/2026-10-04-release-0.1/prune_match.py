from pathlib import Path
import subprocess,json,hashlib,time
A=Path(__file__).resolve().parent; R=A.parents[2]; W=R/'benchmark-work/release-prune-matched-v1';W.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=Path('/home/user/src/cix-0.1-artifacts/bin');new=R/'benchmark-work/release-prune-build/target/release'
cases=[('small-native',R/'benchmark-work/canterbury/grammar.lsp',['--best','--block-size','4096']),('medium-predictor',R/'benchmark-work/canterbury/kennedy.xls',['--best','--format','cixg1','--route','predictor'])]
plan={'cases':[{'id':n,'input':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'flags':f} for n,p,f in cases],'binaries':{n:sha(p/'cix') for n,p in [('before',old),('after',new)]},'policy':'One observation each, fixedCPU8, samecomplete winningarchive+freshrestore required; deadline omissions disqualify exactcompleted-set comparison; noclaimofgeneral speedup'}
freeze=A/'prune-match-freeze.json'
if freeze.exists(): assert json.loads(freeze.read_text())==plan
else: freeze.write_text(json.dumps(plan,indent=2)+'\n')
rows=[]
for name,src,flags in cases:
 for arm,binpath in [('before',old),('after',new)]:
  key=f'{name}-{arm}'; arc=W/f'{key}.cix'; tm=W/f'{key}.time';cmd=['/usr/bin/time','-v','-o',str(tm),str(binpath/'cix'),*flags,'--threads','1','--verbose','-f','-o',str(arc),str(src)];
  if arc.exists():
   assert key=='small-native-before', 'Only preserved initial control may be reused'
   r=subprocess.CompletedProcess(cmd,0,stdout=(W/f'{key}.stdout').read_text(),stderr=(W/f'{key}.stderr').read_text())
  else:
   r=subprocess.run(cmd,capture_output=True,text=True);(W/f'{key}.stderr').write_text(r.stderr);(W/f'{key}.stdout').write_text(r.stdout)
  if r.returncode:raise RuntimeError(f'{key} encode failed')
  restored=W/f'{key}.restored';d=subprocess.run([str(new/'uncix'),'-f','-o',str(restored),str(arc)],capture_output=True,text=True)
  row={'case':name,'arm':arm,'command':cmd,'archive_bytes':arc.stat().st_size,'archive_sha256':sha(arc),'restore_ok':d.returncode==0 and sha(restored)==sha(src),'log':str(W/f'{key}.stderr'),'time':str(tm),'deadline_omission':('CIX candidate deadline exceeded' in r.stderr or 'family deadline allocation exhausted' in r.stderr)};rows.append(row)
  if not row['restore_ok'] or row['deadline_omission']:raise RuntimeError(f'{key} failed qualification')
 prior,current=rows[-2:]
 if prior['archive_sha256']!=current['archive_sha256']:raise RuntimeError(f'{name} archive mismatch')
(A/'prune-match-results.json').write_text(json.dumps({'status':'PASS','rows':rows},indent=2)+'\n')
