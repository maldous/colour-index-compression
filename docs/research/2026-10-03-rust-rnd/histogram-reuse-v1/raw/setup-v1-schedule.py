import fcntl,json,subprocess,sys
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
area=root/'docs/research/2026-10-03-rust-rnd/histogram-reuse-v1';raw=area/'raw';build=root/'benchmark-work/histogram-reuse-v1/build';work=root/'benchmark-work/histogram-reuse-v1/runs'
f=json.loads((area/'freeze.json').read_text());source=root/'rust/cix-native/experiments/histogram-reuse-v1/histogram_reuse_v1.rs';assert a.sha256(source)==f['build']['driver_sha256']
target=root/'benchmark-work/ptt5-fixed-8439/target/release-lto'; decoder=root/'benchmark-work/conditional-cost-v1/build/conditional-cost-v1'
archives=[]
for p in sorted((root/'benchmark-work/conditional-cost-v1/runs').glob('*.cixcc')):
    case=p.name.split('-')[0];inp=p.parent/(case+'.input');archives.append({'path':str(p.relative_to(root)),'sha256':a.sha256(p),'source_sha256':a.sha256(inp)})
assert len(archives)==8
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=805306368,max_temp_bytes=1048576);s.state.mkdir(exist_ok=True); lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(20)]}])
original=subprocess.run
def quota(args,*pos,**kw):
    if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:args=args[:3]+['--property=CPUQuota=100%']+args[3:]
    return original(args,*pos,**kw)
subprocess.run=quota
def phase(unit,cmd,cwd,wall,temp,n):
    budget={'wall_seconds':wall,'max_rss_bytes':805306368,'max_temp_bytes':temp};ap=raw/(unit+'.affinity');cp=raw/(unit+'.cgroup')
    cmd=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(raw/(unit+'.time')),*cmd],ap,cp)
    r=a.execute_phase(unit=unit,command=cmd,work=cwd,destination=raw,budget=budget,cpu=[20],inaccessible=[],input_bytes=n);a.write_json(raw/(unit+'.result.json'),r)
    assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),[20],budget) and a.affinity_set(ap.read_text())==[20],r
try:
    cmd=['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','-C','opt-level=3',str(source),'--extern','cix_native='+str(target/'libcix_native.rlib'),'--extern','num_bigint='+str(next((target/'deps').glob('libnum_bigint*.rlib'))),'--extern','num_traits='+str(next((target/'deps').glob('libnum_traits*.rlib'))),'-L','dependency='+str(target/'deps')]
    for p in sorted((target/'build').glob('*/out')):cmd+=['-L','native='+str(p)]
    cmd+=['-o',str(build/'hrv')]
    phase('cix-hrv-build-v1',cmd,build,120,33554432,0);(build/'hrv').chmod(0o555)
    bind={'source_path':str(source.relative_to(root)),'source_revision':original(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout.strip(),'driver_binary_sha256':a.sha256(build/'hrv'),'decoder_sha256':a.sha256(decoder),'freeze_sha256':a.sha256(area/'freeze.json'),'rlib_sha256':a.sha256(target/'libcix_native.rlib'),'frozen_archives':archives,'scope':'three new fixtures plus eight existing frozen archives, one pack/unpack each, six malformed checks','cpu':[20],'cpu_quota':'100%','memory_bytes':805306368,'temp_bytes':1048576,'batch_wall_seconds':120,'runner_sha256':a.sha256(root/'benchmark-work/histogram-reuse-v1/run_batch.py')}
    a.write_json(area/'execution-binding.json',bind)
    phase('cix-hrv-screen-v1',['/usr/bin/python3',str(root/'benchmark-work/histogram-reuse-v1/run_batch.py')],work,120,1048576,11*16384)
    print('VERIFIED histogram reuse',flush=True)
finally:
    for h in leases:h.close()
    lock.close()
