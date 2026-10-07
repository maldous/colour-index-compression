import fcntl,hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/home/user/src/colour-index-compression'); sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
area=root/'docs/research/2026-10-03-rust-rnd/word-palette-v2'; raw=area/'raw'; build=root/'benchmark-work/word-palette-v2/build'; runs=root/'benchmark-work/word-palette-v2/runs'
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=805306368,max_temp_bytes=2097152); s.state.mkdir(exist_ok=True)
lock=s._wave_lock_path().open('a+'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
leases=s._lease_cores([{'physical_core':[_core(20)]}])
original=subprocess.run
def quota_run(args,*pos,**kw):
    if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']: args=args[:3]+['--property=CPUQuota=100%']+args[3:]
    return original(args,*pos,**kw)
subprocess.run=quota_run
def phase(unit,command,work,wall,temp,input_bytes):
    budget={'wall_seconds':wall,'max_rss_bytes':805306368,'max_temp_bytes':temp}
    ap=raw/(unit+'.affinity'); cp=raw/(unit+'.cgroup'); tf=raw/(unit+'.time')
    command=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(tf),*command],ap,cp)
    result=a.execute_phase(unit=unit,command=command,work=work,destination=raw,budget=budget,cpu=[20],inaccessible=[],input_bytes=input_bytes)
    a.write_json(raw/(unit+'.result.json'),result)
    assert a.phase_ok(result),result
    assert a.cgroup_ok(cp.read_text(),[20],budget) and a.affinity_set(ap.read_text())==[20]
try:
    phase('cix-wpv2-build-v1',['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','-O',str(root/'rust/cix-native/experiments/word-palette-v2/main.rs'),'-o',str(build/'wpv2')],build,120,33554432,0)
    (build/'wpv2').chmod(0o555)
    binding={'source_sha256':a.sha256(root/'rust/cix-native/experiments/word-palette-v2/main.rs'),'binary_sha256':a.sha256(build/'wpv2'),'freeze_sha256':a.sha256(area/'freeze.json'),'toolchain':original(['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','-Vv'],capture_output=True,text=True,check=True).stdout,'batch_driver_sha256':a.sha256(root/'benchmark-work/word-palette-v2/run_batch.py'),'cpu':[20],'memory_bytes':805306368,'temp_bytes':2097152,'wall_seconds':1200,'cpu_quota':'100%'}
    a.write_json(area/'execution-binding.json',binding)
    phase('cix-wpv2-screen-v1',['/usr/bin/python3',str(root/'benchmark-work/word-palette-v2/run_batch.py')],runs,1200,2097152,6*8192)
    print('VERIFIED six rows',flush=True)
finally:
    for h in leases: h.close()
    lock.close()
