#!/usr/bin/env python3
"""Prepared ONLY. Root must admit a fresh capacity/path lease before invocation."""
import argparse,hashlib,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression')
JOB=Path('/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/graph-residual-parity-v3')
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
    for manifest in [JOB/'candidate-manifest.json', JOB/'read-only-reference-manifest.json',
                     JOB.parent/'graph-residual-parity-v1/tool-inputs.json']:
        for name,expected in json.loads(manifest.read_text()).items():
            assert digest(Path(name))==expected,name
verify()
RUN=Path(os.environ['CIX_GRAPH_SCRATCH'])/'run'
assert not RUN.exists(), 'Each candidate receives one admitted run; successor lease required to retry.'
RUN.mkdir()
for name in ['tmp','cargo-home','target','native-frames','decoded']:(RUN/name).mkdir()
start=time.monotonic(); deadline=start+145
os.sched_setaffinity(0,{8})
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
    resource.setrlimit(resource.RLIMIT_CPU,(180,180))

commands=[]; peak_disk=0;peak_rss=0

def run(command,label,expected_rejection=None):
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
                if time.monotonic()>=deadline:reason='145s inner wall limit, preserving outer evidence budget'
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
        if expected_rejection is None:
            assert p.returncode==0, f'{label} exit {p.returncode}; inspect bounded log'
        else:
            assert p.returncode==101, f'{label}: expected driver unwrap rejection, got {p.returncode}'
            diagnostic=log.read_text()
            assert 'on an `Err` value:' in diagnostic and expected_rejection in diagnostic, label+' unexpected failure'
    assert allocated()<150_000_000

variant_results=[]
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
    variants=json.loads((JOB/'variant-manifest.json').read_text())
    assert variants['text_sources']==15 and len(variants['cases'])==45
    for case in variants['cases']:
        archive=Path(case['archive_path']); source=Path(case['source_frame_path'])
        expected_path=Path(case['expected_input_path'])
        assert digest(archive)==case['archive_sha256'] and digest(source)==case['source_frame_sha256']
        assert digest(expected_path)==case['expected_input_sha256']
        expected=expected_path.read_bytes(); assert len(expected)==case['output_cap_bytes']
        kind=case['native_driver_kind']; assert kind in ('graph','hydrogen')
        decoder=sdf_hydrogen.decode if kind=='hydrogen' else sdf_geometry.decode
        accepts=case['expected_outcome']=='ACCEPT_EXACT_INPUT'
        assert accepts or case['expected_outcome']=='REJECT'
        raw=archive.read_bytes(); assert len(raw)==case['archive_bytes']
        dest=RUN/'decoded'/('variant-'+case['id']+'.decoded')
        label='variant-'+case['id']
        if accepts:
            assert decoder(raw)==expected, 'reference variant identity '+case['id']
            run([str(RUN/'target/debug/parity-driver'),kind,str(archive),str(dest),str(len(expected))],label)
            assert dest.read_bytes()==expected, 'native variant identity '+case['id']
            evidence={'reference':'ACCEPT_EXACT_INPUT','native':'ACCEPT_EXACT_INPUT','output_sha256':digest(dest)}
        else:
            try:
                decoder(raw)
            except ValueError as error:
                reference_error=str(error)
            else:
                raise AssertionError('reference accepted invalid variant '+case['id'])
            reason='invalid coordinate list' if kind=='graph' else ('invalid residual vector' if case['mutation']=='empty-final-component' else 'missing coordinate residual')
            run([str(RUN/'target/debug/parity-driver'),kind,str(archive),str(dest),str(len(expected))],label,expected_rejection=reason)
            assert not dest.exists(), 'rejected driver wrote output '+case['id']
            evidence={'reference':'REJECT','reference_error':reference_error,'native':'REJECT','native_error':reason}
        variant_results.append({'id':case['id'],'archive_sha256':case['archive_sha256'],**evidence})
    (RUN/'variant-results.json').write_text(json.dumps(variant_results,indent=2)+'\n')
    assert sum(row['native']=='ACCEPT_EXACT_INPUT' for row in variant_results)==15
    assert sum(row['native']=='REJECT' for row in variant_results)==30
    verify()
    result.update(status='PASS',native_frames=28,fresh_process_decodes=56,reference_crossdecodes=28,
                  variant_native_accepts=15,variant_native_rejections=30,variant_reference_accepts=15,variant_reference_rejections=30)
except BaseException as e:
    result.update(status='STOPPED_OR_FAILED',error=str(e))
finally:
    result.update(commands=commands,variant_results=variant_results,elapsed_seconds=time.monotonic()-start,allocated_bytes=allocated(),
                  peak_sampled_allocated_bytes=peak_disk,peak_sampled_group_rss=peak_rss,
                  guards='Hard outer CPU/memory/no-swap cgroup and size-limited scratch tmpfs; additional per-process CPU and 20ms diagnostic RSS/disk/log/wall watchdog. Exact enclosing enforcement is in execution spec and scheduler receipt.')
    (RUN/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if result['status']!='PASS':sys.exit(1)
