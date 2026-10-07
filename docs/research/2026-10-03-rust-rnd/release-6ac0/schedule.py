import fcntl,json,subprocess,sys
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
area=root/'docs/research/2026-10-03-rust-rnd/release-6ac0';raw=area/'raw';base=root/'benchmark-work/release-6ac0';wt=Path('/tmp/cix-release-6ac0');tool=Path('/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin');target=base/'target';cpus=[8,10];reserved_cpus=[8,10,24,25]
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=8589934592,max_temp_bytes=4000000000);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(c) for c in reserved_cpus]}]);old_rlib=root/'benchmark-work/ptt5-fixed-8439/target/release-lto/libcix_native.rlib';reference_hash=a.sha256(old_rlib)
original=subprocess.run
def quota(args,*pos,**kw):
 if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:args=args[:3]+['--property=CPUQuota=200%']+args[3:]
 return original(args,*pos,**kw)
subprocess.run=quota
def phase(unit,cmd,wall,memory=2147483648):
 budget={'wall_seconds':wall,'max_rss_bytes':memory,'max_temp_bytes':1610612736};ap=raw/(unit+'.affinity');cp=raw/(unit+'.cgroup');cmd=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(raw/(unit+'.time')),*cmd],ap,cp)
 cmd[2]=cmd[2].replace('> "$2"; shift 2;', '> "$2"; printf "cpu.max=%s\\ncgroup.path=%s\\n" "$(cat "$base/cpu.max")" "$cg" >> "$2"; shift 2;')
 r=a.execute_phase(unit=unit,command=cmd,work=base,destination=raw,budget=budget,cpu=cpus,inaccessible=[],input_bytes=512);a.write_json(raw/(unit+'.result.json'),r)
 assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),cpus,budget) and a.affinity_set(ap.read_text())==cpus,r
env=['/usr/bin/env','RUSTC='+str(tool/'rustc'),'RUSTDOC='+str(tool/'rustdoc'),'CARGO_TARGET_DIR='+str(target),'PATH='+str(tool)+':/usr/bin:/bin']
cargo=[str(tool/'cargo'),'--manifest-path',str(wt/'rust/cix-native/Cargo.toml')]
try:
 assert original(['git','rev-parse','HEAD'],cwd=wt,capture_output=True,text=True,check=True).stdout.strip().startswith('6ac05f8e9')
 assert original(['git','status','--porcelain'],cwd=wt,capture_output=True,text=True,check=True).stdout==''
 phase('cix-6ac0-build-v1',env+[cargo[0],'build',*cargo[1:],'--profile','release-lto','--all-features','--locked','--offline','-j','2'],900)
 phase('cix-6ac0-cli-v1',['/usr/bin/python3',str(base/'cli_checks.py')],120,268435456)
 phase('cix-6ac0-clippy-v1',env+[cargo[0],'clippy',*cargo[1:],'--all-targets','--all-features','--locked','--offline','-j','2','--message-format=json'],600)
 assert a.sha256(old_rlib)==reference_hash
 print('VERIFIED focused chain cache and old-decoder idle pipeline',flush=True)
finally:
 for h in leases:h.close()
 lock.close()
