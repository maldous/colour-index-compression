import fcntl,json,subprocess,sys,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
base=root/'benchmark-work/sonar-d3a2-v1';area=root/'docs/research/2026-10-03-rust-rnd/sonar-d3a2';scan=root/'benchmark-work/sonar-4af6/run_scan.py';lease=base/'lease.json'
import hashlib
freeze=json.loads((area/'freeze-v1.json').read_text());assert hashlib.sha256(scan.read_bytes()).hexdigest()==freeze['scanner_sha256']
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=6442450944,max_temp_bytes=4000000000);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(c) for c in [24,25]]}])
try:
 lease.write_text(json.dumps({'status':'ACTIVE','reserved_cpus':[24,25],'memory_reserved':6442450944,'temporary_max':4000000000,'swap':0,'root_wave_lock':str(s._wave_lock_path())}))
 r=subprocess.run(['/usr/bin/python3',str(scan),'--lease',str(lease),'--source','/tmp/cix-release-d3a2','--expected-revision','d3a2cd416e49f93403d1dbd348a3e9a45db66ec6','--clippy-json',str(root/'docs/research/2026-10-03-rust-rnd/release-d3a2/raw/cix-d3a2-clippy-v1.stdout.log'),'--out',str(area/'run-v1')],stdout=(area/'launch-v1.stdout.log').open('w'),stderr=(area/'launch-v1.stderr.log').open('w'),timeout=900)
 (area/'launch-v1-result.json').write_text(json.dumps({'exit':r.returncode}));assert r.returncode==0
finally:
 subprocess.run(['docker','stop','cix-scanner-4af6','cix-sonarqube-4af6'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,check=False)
 lease.write_text(json.dumps({'status':'RELEASED'}))
 for h in leases:h.close()
 lock.close()
