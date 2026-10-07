import fcntl,json,subprocess,sys
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
area=root/'docs/research/2026-10-03-rust-rnd/chain-cache-93d1';raw=area/'raw';base=root/'benchmark-work/chain-cache-93d1';wt=Path('/tmp/cix-chain-cache-93d1');tool=Path('/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin');target=base/'target';cpus=[8,10]
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=2147483648,max_temp_bytes=1073741824);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(c) for c in cpus]}]);old_rlib=root/'benchmark-work/ptt5-fixed-8439/target/release-lto/libcix_native.rlib';reference_hash=a.sha256(old_rlib)
original=subprocess.run
def quota(args,*pos,**kw):
 if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:args=args[:3]+['--property=CPUQuota=200%']+args[3:]
 return original(args,*pos,**kw)
subprocess.run=quota
def phase(unit,cmd,wall,memory=2147483648):
 budget={'wall_seconds':wall,'max_rss_bytes':memory,'max_temp_bytes':1073741824};ap=raw/(unit+'.affinity');cp=raw/(unit+'.cgroup');cmd=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(raw/(unit+'.time')),*cmd],ap,cp)
 r=a.execute_phase(unit=unit,command=cmd,work=base,destination=raw,budget=budget,cpu=cpus,inaccessible=[],input_bytes=512);a.write_json(raw/(unit+'.result.json'),r)
 assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),cpus,budget) and a.affinity_set(ap.read_text())==cpus,r
env=['/usr/bin/env','RUSTC='+str(tool/'rustc'),'RUSTDOC='+str(tool/'rustdoc'),'CARGO_TARGET_DIR='+str(target),'PATH='+str(tool)+':/usr/bin:/bin']
cargo=[str(tool/'cargo'),'--manifest-path',str(wt/'rust/cix-native/Cargo.toml')]
try:
 assert original(['git','rev-parse','HEAD'],cwd=wt,capture_output=True,text=True,check=True).stdout.strip().startswith('93d1c0fb1')
 assert original(['git','status','--porcelain'],cwd=wt,capture_output=True,text=True,check=True).stdout==''
 # Completed build-v1 is retained; do not rebuild.
 for label,test in [('admission','cache_capture_rejects_unfunded_payload_before_retaining_it')]:
  phase('cix-chain93-'+label+'-v2',env+[cargo[0],'test',*cargo[1:],'--lib','--profile','release-lto','--all-features','--locked','--offline','-j','2','cli::chain::tests::'+test,'--','--exact'],600)
  text=(raw/('cix-chain93-'+label+'-v2.stdout.log')).read_text();assert '1 passed' in text and '0 failed' in text
 phase('cix-chain93-stream-v1',['/usr/bin/python3',str(base/'stream_check.py')],60,536870912)
 assert a.sha256(old_rlib)==reference_hash
 print('VERIFIED focused chain cache and old-decoder idle pipeline',flush=True)
finally:
 for h in leases:h.close()
 lock.close()
