import os, subprocess, pathlib
area=pathlib.Path(__file__).resolve().parent
cg=pathlib.Path('/proc/self/cgroup').read_text().strip().split('::',1)[1]
base=pathlib.Path('/sys/fs/cgroup'+cg)
(area/'scope.txt').write_text('cgroup='+cg+'\n'+''.join(k+'='+str((base/k).read_text().strip())+'\n' for k in ['memory.max','memory.swap.max','cpuset.cpus.effective']))
for name in ['rescale_ceil','lowest_bit_preserves_fenwick_step']:
 cmd=['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo','test','--locked','--manifest-path','rust/cix-native/Cargo.toml','--lib','-j1',name,'--','--test-threads=1']
 with (area/(name+'.log')).open('wb') as out:
  child=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT)
  try:
   (area/(name+'.child.txt')).write_text(pathlib.Path('/proc/'+str(child.pid)+'/cgroup').read_text()+subprocess.check_output(['taskset','-pc',str(child.pid)],text=True))
  except OSError: pass
  rc=child.wait()
 (area/(name+'.exit')).write_text(str(rc)+'\n')
 if rc: raise SystemExit(rc)
(area/'peak.txt').write_text((base/'memory.peak').read_text())
