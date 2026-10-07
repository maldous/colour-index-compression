#!/usr/bin/env python3
"""Prepared ONLY. Root must admit a fresh capacity/path lease before invocation."""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression')
JOB=Path(__file__).resolve().parent
OUT=ROOT/'benchmark-work/native-rc-check-v1/graph-residual-parity-v1'
TOOLCHAIN=Path('/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin')
parser=argparse.ArgumentParser()
parser.add_argument('--root-admission',required=True,help='Exact newly read-back ROOT resource/path lease comment ID')
args=parser.parse_args()
assert args.root_admission.strip()

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def verify():
    for name,expected in json.loads((JOB/'candidate-manifest.json').read_text()).items():
        assert digest(Path(name))==expected,name
    for name,expected in json.loads((JOB/'read-only-inputs.json').read_text()).items():
        assert digest(Path(name))==expected,name
    for name,expected in json.loads((JOB/'tool-inputs.json').read_text()).items():
        assert digest(Path(name))==expected,name
verify()
RUN=OUT/'root-run'
assert not RUN.exists(), 'Each candidate receives one admitted run; successor lease required to retry.'
RUN.mkdir()
for name in ['tmp','cargo-home','target','native-frames','decoded']:(RUN/name).mkdir()
start=time.monotonic(); deadline=start+180
os.sched_setaffinity(0,{8})
resource.setrlimit(resource.RLIMIT_AS,(500_000_000,500_000_000))
resource.setrlimit(resource.RLIMIT_FSIZE,(1_000_000,1_000_000))
sys.dont_write_bytecode=True
ENV={'PATH':str(TOOLCHAIN)+':/usr/bin:/bin','HOME':str(RUN),
     'CARGO_HOME':str(RUN/'cargo-home'),'CARGO_TARGET_DIR':str(RUN/'target'),
     'RUSTC':str(TOOLCHAIN/'rustc'),'CARGO_BUILD_JOBS':'1','CARGO_INCREMENTAL':'0',
     'TMPDIR':str(RUN/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C',
     'CIX_GRAPH_NATIVE_OUTPUT':str(RUN/'native-frames')}

def allocated():
    return sum(p.stat().st_blocks*512 for p in [RUN,*RUN.rglob('*')] if not p.is_symlink())
def process_rss(group):
    total=0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
            if int(stat[2])==group:total+=int(stat[21])*os.sysconf('SC_PAGE_SIZE')
        except (OSError,ValueError,IndexError):pass
    return total + int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')

def limits():
    os.sched_setaffinity(0,{8})
    resource.setrlimit(resource.RLIMIT_AS,(1_000_000_000,1_000_000_000))
    resource.setrlimit(resource.RLIMIT_FSIZE,(140_000_000,140_000_000))
    resource.setrlimit(resource.RLIMIT_CPU,(180,180))

commands=[]; peak_disk=0;peak_rss=0

def run(command,label):
    global peak_disk,peak_rss
    assert time.monotonic()<deadline
    log=RUN/(label+'.log')
    with log.open('wb') as stream:
        p=subprocess.Popen(command,cwd=JOB/'harness',env=ENV,stdout=stream,stderr=subprocess.STDOUT,
                           start_new_session=True,preexec_fn=limits)
        reason=None
        try:
            while p.poll() is None:
                disk=allocated();rss=process_rss(p.pid)
                peak_disk=max(peak_disk,disk);peak_rss=max(peak_rss,rss)
                if time.monotonic()>=deadline:reason='180s aggregate wall limit'
                elif disk>=140_000_000:reason='140MB early stop before 150MB allocation ceiling'
                elif rss>=950_000_000:reason='950MB early stop before 1GB aggregate RSS ceiling'
                elif log.stat().st_size>=1_000_000:reason='1MB log limit'
                if reason:
                    os.killpg(p.pid,signal.SIGKILL);p.wait();raise RuntimeError(reason)
                time.sleep(.02)
        finally:
            # A build command may leave a descendant after its parent exits.
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        commands.append(dict(label=label,command=command,exit=p.returncode))
        assert p.returncode==0, f'{label} exit {p.returncode}; inspect bounded log'
    assert allocated()<150_000_000

result={'admission':args.root_admission,'scope':'five-module qualification only','benchmarks':'STOPPED'}
try:
    cargo=str(TOOLCHAIN/'cargo')
    run([cargo,'test','--offline','--locked','--manifest-path',str(JOB/'harness/Cargo.toml'),
         '--test','graph_residual_parity','--','--test-threads=1'],'focused-tests')
    run([cargo,'build','--offline','--locked','--manifest-path',str(JOB/'harness/Cargo.toml'),
         '--bin','parity-driver'],'decoder-build')
    fx=JOB/'harness/tests/fixtures/graph_residual_parity'
    sys.path.insert(0,str(ROOT/'runtime'))
    from cix_runtime.legacy import sdf_geometry,sdf_hydrogen
    frames=sorted(fx.glob('*.frame'));assert len(frames)==28
    for frame in frames:
        name=frame.name
        kind='hydrogen' if name.startswith('hydrogen-') else 'graph'
        input_name='hydrogen.input' if kind=='hydrogen' else ('palette-boundary.input' if name.startswith('palette-boundary-') else ('palette.input' if name.startswith('palette-') else 'graph.input'))
        expected=(fx/input_name).read_bytes()
        native=RUN/'native-frames'/name
        assert native.read_bytes()==frame.read_bytes(),name
        decoder=sdf_hydrogen.decode if kind=='hydrogen' else sdf_geometry.decode
        assert decoder(native.read_bytes())==expected, 'reference crossdecode '+name
        for origin,archive in [('reference',frame),('native',native)]:
            dest=RUN/'decoded'/(origin+'-'+name+'.decoded')
            run([str(RUN/'target/debug/parity-driver'),kind,str(archive),str(dest),str(len(expected))],origin+'-'+name)
            assert dest.read_bytes()==expected, 'fresh-process decode '+name
    verify()
    result.update(status='PASS',native_frames=28,fresh_process_decodes=56,reference_crossdecodes=28)
except BaseException as e:
    result.update(status='STOPPED_OR_FAILED',error=str(e))
finally:
    result.update(commands=commands,elapsed_seconds=time.monotonic()-start,allocated_bytes=allocated(),
                  peak_sampled_allocated_bytes=peak_disk,peak_sampled_group_rss=peak_rss,
                  guards='Per-process AS/CPU/file ceilings plus 20ms process-group RSS/disk/log/wall watchdog; sampled aggregate guards are not filesystem/cgroup quotas.')
    (RUN/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if result['status']!='PASS':sys.exit(1)
