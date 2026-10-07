import hashlib,json,subprocess,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression')
area=root/'docs/research/2026-10-03-rust-rnd/closure-queue/word-exception-results'
work=root/'benchmark-work/closure-word/runs'
exe=root/'benchmark-work/closure-word/build/wec2'
freeze=json.loads((area/'freeze.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args): subprocess.run([str(x) for x in args],cwd=root,check=True)
cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().strip().split(':')[-1])
def receipt(): return {k:(cg/k).read_text().strip() for k in ['cpu.max','cpuset.cpus.effective','memory.max','memory.current','memory.peak','memory.swap.max','memory.events']}
before=receipt(); assert before['cpu.max'].split()[0]==before['cpu.max'].split()[1]
assert before['memory.max']=='805306368' and before['memory.swap.max']=='0'
assert before['cpuset.cpus.effective']=='8'
assert sha(root/freeze['driver']['path'])==freeze['driver']['sha256']
for k in ['cix','uncix']: assert sha(root/freeze['backend'][k]['path'])==freeze['backend'][k]['sha256']
rows=[];started=time.monotonic(); inputs={}
for case in ['strong','weak','absent']:
 p=work/(case+'.input');run([exe,'generate',case,p]);inputs[case]={'sha256':sha(p),'bytes':p.stat().st_size}
(area/'input-bindings.json').write_text(json.dumps({'before_codec':True,'inputs':inputs},indent=2)+'\n')
for case in inputs:
 source=work/(case+'.input')
 for width in [2,4]:
  for variant,limit in [('identity',0),('palette',8),('palette',16)]:
   stem=work/(case+'-'+variant+'-'+str(width)+'-'+str(limit));report=stem.with_suffix('.json');archive=stem.with_suffix('.wpv2')
   run([exe,'encode',variant,str(width),str(limit),source,archive,report,root/freeze['backend']['cix']['path'],root/freeze['backend']['uncix']['path']])
   row=json.loads(report.read_text());assert row['native_candidate_fresh_archive_only_decode'] and row['selected_candidate_fresh_archive_only_decode']
   for suffix in ['.wpv2.cixg1.fresh.restored','.wpv2.selected.fresh.restored']:assert sha(archive.with_suffix(suffix))==sha(source)
   row.update(fixture=case,archive_sha256=sha(archive),native_archive_sha256=sha(Path(row['native_candidate_path'])));rows.append(row)
   assert sum(p.stat().st_size for p in work.rglob('*') if p.is_file())<=2097152
summary={'status':'VERIFIED_SINGLE_SCREEN','rows':rows,'elapsed_seconds':time.monotonic()-started,'cgroup_before':before,'cgroup_after':receipt(),'driver_binary_sha256':sha(exe),'freeze_sha256':sha(area/'freeze.json'),'retained_run_bytes':sum(p.stat().st_size for p in work.rglob('*') if p.is_file())}
(area/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
