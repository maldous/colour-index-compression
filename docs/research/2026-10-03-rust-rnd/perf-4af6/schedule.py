import fcntl,json,subprocess,sys,hashlib
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');sys.path.insert(0,str(root))
from benchmarks import cix_rust_perf_audit as a
from benchmarks.hutter_experiment_scheduler import WaveScheduler,_core
base=root/'benchmark-work/perf-4af6';area=root/'docs/research/2026-10-03-rust-rnd/perf-4af6';raw=area/'raw';cpus=[8,10];release=root/'benchmark-work/m6-idle-4af6/final';source=root/'benchmark-work/canterbury/kennedy.xls';archive=base/'archive.cix';restored=base/'restored.bin'
freeze=json.loads((area/'freeze.json').read_text());assert a.sha256(source)==freeze['input']['sha256']
for n,h in freeze['binaries'].items():assert a.sha256(release/n)==h
s=WaveScheduler(root,max_jobs=1,max_memory_bytes=2147483648,max_temp_bytes=134217728);s.state.mkdir(exist_ok=True);lock=s._wave_lock_path().open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);leases=s._lease_cores([{'physical_core':[_core(c) for c in cpus]}]);original=subprocess.run
privileged=False
def launch(args,*pos,**kw):
 if isinstance(args,list) and args[:3]==['sudo','-n','systemd-run']:
  args=[('--property=User=root' if privileged and v=='--property=User=user' else v) for v in args];args=args[:3]+['--property=CPUQuota=200%']+args[3:]
 return original(args,*pos,**kw)
subprocess.run=launch
phases={}
def phase(unit,command,wall,memory):
 budget={'wall_seconds':wall,'max_rss_bytes':memory,'max_temp_bytes':134217728};ap=raw/(unit+'.affinity');cp=raw/(unit+'.cgroup');command=a.affinity_wrapped(command,ap,cp)
 r=a.execute_phase(unit=unit,command=command,work=base,destination=raw,budget=budget,cpu=cpus,inaccessible=[],input_bytes=source.stat().st_size);a.write_json(raw/(unit+'.result.json'),r);assert a.phase_ok(r) and a.cgroup_ok(cp.read_text(),cpus,budget),r;phases[unit]=r
try:
 command=['/usr/bin/setpriv','--reuid=user','--regid=user','--init-groups','/usr/bin/time','-v','-o',str(raw/'encoder.time'),str(release/'cix'),'--threads','2','--memory','512MiB','-f','-o',str(archive),str(source)]
 privileged=True
 phase('cix-perf4af-encode-v1',['/usr/bin/perf','stat','-x',',','-o',str(raw/'stat.csv'),'-e','cpu_core/cycles/,cpu_core/instructions/,cpu_core/cache-misses/,cpu_core/branch-misses/,context-switches,cpu-migrations','--','/usr/bin/perf','record','-F','99','-e','cpu_core/cycles/','--call-graph','dwarf,4096','-o',str(base/'perf.data'),'--',*command],180,2147483648)
 privileged=False
 phase('cix-perf4af-decode-v1',['/usr/bin/time','-v','-o',str(raw/'decoder.time'),str(release/'uncix'),'-f','-o',str(restored),str(archive)],60,268435456)
 assert a.sha256(restored)==a.sha256(source)
 report=original(['sudo','-n','/usr/bin/perf','report','--stdio','--no-children','--percent-limit','0.5','-i',str(base/'perf.data')],capture_output=True,text=True,check=True);(raw/'report.txt').write_text(report.stdout);(raw/'report.stderr').write_text(report.stderr)
 r={'status':'VERIFIED_PROFILE','source_revision':freeze['source_revision'],'input':freeze['input'],'archive_bytes':archive.stat().st_size,'archive_sha256':a.sha256(archive),'restored_sha256':a.sha256(restored),'encoder':a.parse_gnu_time(raw/'encoder.time'),'decoder':a.parse_gnu_time(raw/'decoder.time'),'flags':freeze['flags'],'phases':phases,'metric_limits':'Encoder is instrumented by nested perf stat/record, not an uninstrumented throughput comparison. Historical baseline threads/core allocation differs; size parity only. Native source input remains unchanged.'};a.write_json(area/'result.json',r);print('VERIFIED current DEFAULT profile and fresh restore',flush=True)
finally:
 for h in leases:h.close()
 lock.close()
