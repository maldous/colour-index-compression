import fcntl,json,subprocess,sys,zlib
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
area=root/'docs/research/2026-10-03-rust-rnd/representation-search-v1';raw=area/'raw';base=root/'benchmark-work/representation-search-v1';build=base/'build-v2';work=base/'runs';source=root/'rust/cix-native/experiments/representation-search-v1/main.rs'
f=json.loads((area/'freeze.json').read_text());assert a.sha256(source)==f['prepared_driver_sha256'];inp=root/f['input']['path'];assert a.sha256(inp)==f['input']['sha256']
for v in f['backend_control']['binaries'].values():assert a.sha256(root/v['path'])==v['sha256']
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=1073741824,max_temp_bytes=2097152);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(20)]}]);original=subprocess.run
def quota(args,*pos,**kw):
    if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:args=args[:3]+['--property=CPUQuota=100%']+args[3:]
    return original(args,*pos,**kw)
subprocess.run=quota
def phase(unit,cmd,cwd,wall,temp,n):
    budget={'wall_seconds':wall,'max_rss_bytes':1073741824,'max_temp_bytes':temp};ap=raw/(unit+'.affinity');cp=raw/(unit+'.cgroup')
    cmd=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(raw/(unit+'.time')),*cmd],ap,cp)
    r=a.execute_phase(unit=unit,command=cmd,work=cwd,destination=raw,budget=budget,cpu=[20],inaccessible=[],input_bytes=n);a.write_json(raw/(unit+'.result.json'),r)
    assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),[20],budget) and a.affinity_set(ap.read_text())==[20],r
try:
    exe=build/'rsl1';phase('cix-rsl-build-v2',['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','-O',str(source),'-o',str(exe)],build,120,33554432,0);exe.chmod(0o555)
    a.write_json(area/'execution-binding.json',{'source_revision':original(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout.strip(),'source_sha256':a.sha256(source),'binary_sha256':a.sha256(exe),'freeze_sha256':a.sha256(area/'freeze.json'),'input':f['input'],'backend':f['backend_control']['binaries'],'cpu':[20],'cpu_max':'100000 100000','memory_max':1073741824,'swap_max':0,'temp_max':2097152,'wall_seconds':60,'single_screen':True,'runner_sha256':a.sha256(base/'run_batch.py')})
    phase('cix-rsl-screen-v1',['/usr/bin/python3',str(base/'run_batch.py')],work,60,2097152,8192)
    print('VERIFIED twelve-candidate screen',flush=True)
finally:
    for h in leases:h.close()
    lock.close()
