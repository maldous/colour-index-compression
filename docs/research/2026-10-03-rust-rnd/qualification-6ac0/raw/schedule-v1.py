import fcntl,hashlib,json,subprocess,sys,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
base=root/'benchmark-work/qualification-6ac0';area=root/'docs/research/2026-10-03-rust-rnd/qualification-6ac0';raw=area/'raw';cpus=[8,10];reserved=[8,10,24,25];release=root/'benchmark-work/release-6ac0/final';driver=root/'rust/cix-native/experiments/stream-qualification-v2/driver.py';scan=root/'benchmark-work/sonar-4af6/run_scan.py';scanout=root/'docs/research/2026-10-03-rust-rnd/sonar-6ac0/run';scanlease=base/'scan-lease.json'
freeze=json.loads((area/'freeze.json').read_text());assert a.sha256(driver)==freeze['driver_sha256'] and a.sha256(scan)==freeze['scanner_sha256']
for n,v in freeze['release']['binaries'].items():assert a.sha256(release/n)==v['sha256']
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=8589934592,max_temp_bytes=4000000000);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(c) for c in reserved]}]);original=subprocess.run
started=time.monotonic();scanner=None

def quota(args,*pos,**kw):
 if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:args=args[:3]+['--property=CPUQuota=200%']+args[3:]
 return original(args,*pos,**kw)
subprocess.run=quota

def phase(unit,cmd,wall):
 budget={'wall_seconds':wall,'max_rss_bytes':268435456,'max_temp_bytes':134217728};ap=raw/(unit+'.affinity');cp=raw/(unit+'.cgroup');cmd=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(raw/(unit+'.time')),*cmd],ap,cp)
 cmd[2]=cmd[2].replace('> "$2"; shift 2;', '> "$2"; printf "cpu.max=%s\\ncgroup.path=%s\\n" "$(cat "$base/cpu.max")" "$cg" >> "$2"; shift 2;')
 r=a.execute_phase(unit=unit,command=cmd,work=base,destination=raw,budget=budget,cpu=cpus,inaccessible=[],input_bytes=33554432);a.write_json(raw/(unit+'.result.json'),r);assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),cpus,budget) and 'cpu.max=200000 100000' in cp.read_text(),r
try:
 a.write_json(scanlease,{'status':'ACTIVE','source_revision':freeze['release']['source_revision'],'reserved_cpus':reserved,'scanner_server_cpus':[24,25],'memory_reserved':8589934592,'temporary_max':4000000000,'swap':0,'root_wave_lock':str(s._wave_lock_path())})
 scanner=subprocess.Popen(['/usr/bin/python3',str(scan),'--lease',str(scanlease),'--source','/tmp/cix-release-6ac0','--expected-revision',freeze['release']['source_revision'],'--clippy-json',str(root/'docs/research/2026-10-03-rust-rnd/release-6ac0/raw/cix-6ac0-clippy-v1.stdout.log'),'--out',str(scanout)],stdout=(raw/'sonar-launch.stdout.log').open('w'),stderr=(raw/'sonar-launch.stderr.log').open('w'))
 for mode in ['g1','m6']:
  phase('cix-stream6ac-'+mode+'-v1',['/usr/bin/python3',str(driver),mode,str(release/'cix'),str(release/'uncix'),str(root/'benchmark-work/combined-bd2-validation/final/uncix'),str(base/mode),'--expected-source-sha',freeze['source_sha256']],180)
  result=json.loads((base/mode/'result.json').read_text());a.write_json(area/(mode+'-result.json'),result)
 timeout=max(.1,900-(time.monotonic()-started));status=scanner.wait(timeout=timeout);a.write_json(area/'sonar-launch-result.json',{'exit':status});assert status==0,'Sonar runner failed'
 print('VERIFIED large streams and current Docker Sonar qualification',flush=True)
finally:
 if scanner is not None and scanner.poll() is None:scanner.terminate();scanner.wait(timeout=5)
 original(['docker','stop','cix-scanner-4af6','cix-sonarqube-4af6'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False,timeout=30)
 a.write_json(scanlease,{'status':'RELEASED'})
 for h in leases:h.close()
 lock.close()
