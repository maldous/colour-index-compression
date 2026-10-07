import fcntl,json,subprocess,sys,os
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
base=root/'benchmark-work/segmentation-masks';area=root/'docs/research/2026-10-03-constraint-space/segmentation/mask-evidence';raw=area/'raw';freeze=json.loads((area/'freeze.json').read_text())
for path,digest in freeze['hashes'].items():assert a.sha256(root/path)==digest
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=2147483648,max_temp_bytes=67108864);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(8)]}]);original=subprocess.run

def quota(args,*pos,**kw):
 if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:args=args[:3]+['--property=CPUQuota=100%']+args[3:]
 return original(args,*pos,**kw)
subprocess.run=quota

def phase(unit,cmd,wall):
 budget={'wall_seconds':wall,'max_rss_bytes':2147483648,'max_temp_bytes':67108864};cp=raw/(unit+'.cgroup');cmd=a.affinity_wrapped(['/usr/bin/time','-v','-o',str(raw/(unit+'.time')),*cmd],raw/(unit+'.affinity'),cp)
 cmd[2]=cmd[2].replace('> "$2"; shift 2;', '> "$2"; printf "cpu.max=%s\\ncgroup.path=%s\\n" "$(cat "$base/cpu.max")" "$cg" >> "$2"; shift 2;')
 r=a.execute_phase(unit=unit,command=cmd,work=base,destination=raw,budget=budget,cpu=[8],inaccessible=[],input_bytes=0);a.write_json(raw/(unit+'.result.json'),r);assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),[8],budget) and 'cpu.max=100000 100000' in cp.read_text(),r
try:
 (base/'build').mkdir(parents=True,exist_ok=True)
 raw.mkdir(exist_ok=True)
 phase('cix-mask-build-v1',['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc', '--edition=2021', '-O', '/home/user/src/colour-index-compression/rust/cix-native/experiments/constraint-space/segmentation_lane_masks.rs', '--extern', 'cix_native=/home/user/src/colour-index-compression/benchmark-work/release-d3a2/target/release-lto/deps/libcix_native.rlib', '-L', 'dependency=/home/user/src/colour-index-compression/benchmark-work/release-d3a2/target/release-lto/deps', '-L', 'native=/home/user/src/colour-index-compression/benchmark-work/release-d3a2/target/release-lto/build/cix-native-a768c5224a0384e7/out', '-o', '/home/user/src/colour-index-compression/benchmark-work/segmentation-masks/build/lanes'],120)
 phase('cix-mask-zsc-build-v1',['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc', '--edition=2021', '-O', '/home/user/src/colour-index-compression/rust/cix-native/experiments/constraint-space/lane_mask_zstd_control.rs', '-l', 'zstd', '-o', '/home/user/src/colour-index-compression/benchmark-work/segmentation-masks/build/zsc'],120)
 phase('cix-mask-inputs-v1',['/usr/bin/python3', '/home/user/src/colour-index-compression/docs/research/2026-10-03-constraint-space/segmentation/mask-evidence/fixtures.py'],40)
 phase('cix-mask-compare-v1',['/usr/bin/env', 'CIX_MASK_LEASE=1', '/usr/bin/python3', '/home/user/src/colour-index-compression/docs/research/2026-10-03-constraint-space/segmentation/mask-evidence/run.py'],240)
finally:
 for h in leases:h.close()
 lock.close()
