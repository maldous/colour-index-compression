from pathlib import Path
import hashlib,json,subprocess,sys
root=Path('/home/user/src/colour-index-compression')
sys.path.insert(0,str(root))
from benchmarks.cix_rust_perf_audit import affinity_wrapped,cgroup_ok
out=root/'benchmark-work/rust-performance-audit/cgroup-readback-actual'
out.mkdir(exist_ok=False)
command=affinity_wrapped(['/bin/true'],out/'affinity.txt',out/'cgroup.txt')
r=subprocess.run(command,capture_output=True,text=True)
value={'purpose':'actual harness readback preflight, not a CIX benchmark','command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'harness_sha256':hashlib.sha256((root/'benchmarks/cix_rust_perf_audit.py').read_bytes()).hexdigest(),'affinity':(out/'affinity.txt').read_text() if (out/'affinity.txt').exists() else None,'cgroup':(out/'cgroup.txt').read_text() if (out/'cgroup.txt').exists() else None}
value['limits_match']=cgroup_ok(value['cgroup'],[8],{'max_rss_bytes':1073741824})
(out/'result.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value,indent=2))
sys.exit(0 if r.returncode==0 and value['limits_match'] else 1)
