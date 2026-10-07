import fcntl,hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/home/user/src/colour-index-compression'); sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
area=root/'docs/research/2026-10-03-rust-rnd/closure-queue/word-exception-results'; raw=area/'raw'; build=root/'benchmark-work/closure-word/build'; runs=root/'benchmark-work/closure-word/runs'
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=805306368,max_temp_bytes=2097152); s.state.mkdir(exist_ok=True)
lock=s._wave_lock_path().open('a+'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
leases=s._lease_cores([{'physical_core':[_core(8)]}])
original=subprocess.run
def quota_run(args,*pos,**kw):
    if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']: args=args[:3]+['--property=CPUQuota=100%']+args[3:]
    return original(args,*pos,**kw)
subprocess.run=quota_run
def phase(unit,command,work,wall,temp,input_bytes):
    budget={'wall_seconds':wall,'max_rss_bytes':805306368,'max_temp_bytes':temp}
    ap=raw/(unit+'.affinity'); cp=raw/(unit+'.cgroup'); tf=raw/(unit+'.time')
    command=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(tf),*command],ap,cp)
    command[2]=command[2].replace('> "$2"; shift 2;', '> "$2"; printf "cpu.max=%s\\ncgroup.path=%s\\n" "$(cat "$base/cpu.max")" "$cg" >> "$2"; shift 2;')
    result=a.execute_phase(unit=unit,command=command,work=work,destination=raw,budget=budget,cpu=[8],inaccessible=[],input_bytes=input_bytes)
    a.write_json(raw/(unit+'.result.json'),result)
    assert a.phase_ok(result),result
    assert a.cgroup_ok(cp.read_text(),[8],budget) and a.affinity_set(ap.read_text())==[8]
try:
    phase('cix-wec2-build-v1',['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','-O',str(root/'rust/cix-native/experiments/word-exception-closure/main.rs'),'-o',str(build/'wec2')],build,120,33554432,0)
    (build/'wec2').chmod(0o555)
    binding={'source_sha256':a.sha256(root/'rust/cix-native/experiments/word-exception-closure/main.rs'),'binary_sha256':a.sha256(build/'wec2'),'freeze_sha256':a.sha256(area/'freeze.json'),'toolchain':original(['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','-Vv'],capture_output=True,text=True,check=True).stdout,'batch_driver_sha256':a.sha256(root/'benchmark-work/closure-word/run_batch.py'),'cpu':[8],'memory_bytes':805306368,'temp_bytes':2097152,'wall_seconds':1200,'cpu_quota':'100%'}
    a.write_json(area/'execution-binding.json',binding)
    phase('cix-wec2-screen-v1',['/usr/bin/python3',str(root/'benchmark-work/closure-word/run_batch.py')],runs,1200,2097152,18*8192)
    print('VERIFIED eighteen rows',flush=True)
finally:
    for h in leases: h.close()
    lock.close()
