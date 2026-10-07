import fcntl,json,subprocess,sys,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
base=root/'benchmark-work/sonar-6ac0-v8';area=root/'docs/research/2026-10-03-rust-rnd/sonar-6ac0';scan=root/'benchmark-work/sonar-4af6/run_scan.py';lease=base/'lease.json'
import hashlib
freeze=json.loads((area/'freeze-v8.json').read_text());assert hashlib.sha256(scan.read_bytes()).hexdigest()==freeze['scanner_sha256']
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=6442450944,max_temp_bytes=4000000000);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(c) for c in [24,25]]}])
try:
 lease.write_text(json.dumps({'status':'ACTIVE','reserved_cpus':[24,25],'memory_reserved':6442450944,'temporary_max':4000000000,'swap':0,'root_wave_lock':str(s._wave_lock_path())}))
 r=subprocess.run(['/usr/bin/python3',str(scan),'--lease',str(lease),'--source','/tmp/cix-release-6ac0','--expected-revision','6ac05f8e9fd78ff01e2f8d71e6557c5dc66bb8bb','--clippy-json',str(root/'docs/research/2026-10-03-rust-rnd/release-6ac0/raw/cix-6ac0-clippy-v1.stdout.log'),'--out',str(area/'run-v8')],stdout=(area/'launch-v8.stdout.log').open('w'),stderr=(area/'launch-v8.stderr.log').open('w'),timeout=900)
 (area/'launch-v8-result.json').write_text(json.dumps({'exit':r.returncode}));assert r.returncode==0
finally:
 subprocess.run(['docker','stop','cix-scanner-4af6','cix-sonarqube-4af6'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,check=False)
 lease.write_text(json.dumps({'status':'RELEASED'}))
 for h in leases:h.close()
 lock.close()
