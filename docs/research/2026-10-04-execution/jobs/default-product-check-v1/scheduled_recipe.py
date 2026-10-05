#!/usr/bin/env python3
"""One offline actual-module qualification. No product tree is writable."""
import hashlib, json, os, shutil, signal, subprocess, sys, tarfile, time, gzip
from pathlib import Path

JOB = Path(__file__).resolve().parent
ROOT = Path('/home/user/src/colour-index-compression')
SCRATCH = Path(os.environ['CIX_CHECK_SCRATCH'])
RUN = SCRATCH / 'run'
BUILD = SCRATCH / 'build'
TOOLCHAIN = Path('/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin')
start = time.monotonic()
deadline = start + 200
commands = []
peak_disk = 0

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()

def write(name, value):
    (RUN / name).write_text(json.dumps(value, indent=2) + '\n')

def allocated():
    stat = os.statvfs(SCRATCH)
    return (stat.f_blocks - stat.f_bfree) * stat.f_frsize

def run(command, label):
    global peak_disk
    began = time.monotonic()
    log = RUN / (label + '.log')
    with log.open('xb') as stream:
        p = subprocess.Popen(command, cwd=BUILD/'harness', env=ENV,
                             stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        reason = None
        try:
            while p.poll() is None:
                peak_disk = max(peak_disk, allocated())
                if time.monotonic() >= deadline: reason = '200-second inner wall limit'
                elif allocated() >= 87_000_000: reason = '87MB early disk stop before 90MB hard tmpfs'
                elif log.stat().st_size >= 1_000_000: reason = '1MB log cap'
                if reason:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                    break
                time.sleep(.02)
        finally:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
    commands.append({'command': command, 'label': label, 'exit': p.returncode,
                     'seconds': time.monotonic()-began, 'stop_reason': reason})
    assert reason is None and p.returncode == 0, f'{label}: {reason or p.returncode}'

assert not RUN.exists() and not BUILD.exists()
RUN.mkdir(); BUILD.mkdir()
for n in ['cargo-home', 'tmp', 'target']: (BUILD/n).mkdir()
(BUILD/'harness').mkdir()
ENV = {'PATH':str(TOOLCHAIN)+':/usr/bin:/bin', 'HOME':str(BUILD),
       'CARGO_HOME':str(BUILD/'cargo-home'), 'CARGO_TARGET_DIR':str(BUILD/'target'),
       'RUSTC':str(TOOLCHAIN/'rustc'), 'CARGO_BUILD_JOBS':'1', 'CARGO_INCREMENTAL':'0',
       'TMPDIR':str(BUILD/'tmp'), 'PYTHONDONTWRITEBYTECODE':'1', 'LC_ALL':'C',
       'CARGO_NET_OFFLINE':'true', 'CARGO_PROFILE_DEV_DEBUG':'0', 'CARGO_PROFILE_DEV_INCREMENTAL':'false', 'CARGO_PROFILE_DEV_BUILD_OVERRIDE_DEBUG':'0', 'CARGO_HTTP_MULTIPLEXING':'false'}
result = {'scope':'full actual default library and three CLI source targets; type/buildscript check only, no link/runtime/server proof',
          'admission':os.environ['CIX_CHECK_ADMISSION'], 'benchmarks':'HOLD'}
try:
    mapping = json.loads((JOB/'crate-copy-map.json').read_text())
    for source, relative in mapping.items():
        dest=BUILD/'harness'/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
    evidence = ROOT/'benchmark-work/native-rc-check-v1/service-dependency-resolution-v2/evidence'
    shutil.copyfile(evidence/'candidate-Cargo.lock', BUILD/'harness/Cargo.lock')
    original_lock = sha(BUILD/'harness/Cargo.lock')
    shutil.copyfile(BUILD/'harness/Cargo.lock', RUN/'isolated-Cargo.lock')
    recovered = {}
    expected = json.loads((evidence/'artifact-manifest.json').read_text())
    with tarfile.open(evidence/'scratch-recovery.tar.gz','r:gz') as tar:
        for member in tar:
            if member.isfile() and member.name.startswith('run/cargo-home/registry/index/'):
                name = str(Path(member.name).relative_to('run'))
                contents = tar.extractfile(member).read()
                assert {'sha256':hashlib.sha256(contents).hexdigest(),'bytes':len(contents)} == expected[name]
                dest = BUILD/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(contents)
                recovered[name]=expected[name]
    assert recovered and any(p.endswith('config.json') for p in recovered)
    write('recovered-index-manifest.json',recovered)
    cache = BUILD/'cargo-home/registry/cache/index.crates.io-1949cf8c6b5b557f'
    cache.mkdir(parents=True)
    for package in json.loads((JOB/'archive-inputs.json').read_text()):
        src=Path(package['path']);assert sha(src)==package['checksum']
        shutil.copyfile(src,cache/src.name)
    (BUILD/'cargo-home/config.toml').write_text('[registries.crates-io]\nprotocol = "sparse"\n[net]\noffline = true\nretry = 0\n')
    # Preserve actual full source snapshot, including currently uncommitted peer
    # source, as evidence before compilation; this is not a product-tree edit.
    with (RUN/'source-snapshot.tar.gz').open('xb') as stream:
        with gzip.GzipFile(filename='',mode='wb',fileobj=stream,compresslevel=1,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w|') as tar:
                tar.add(BUILD/'harness',arcname='crate')
    cargo = str(TOOLCHAIN/'cargo')
    manifest = str(BUILD/'harness/Cargo.toml')
    run([cargo,'check','--offline','--locked','--manifest-path',manifest,'--lib','--bins','--no-default-features','--message-format=json-diagnostic-rendered-ansi'], 'default-product-check')
    assert sha(BUILD/'harness/Cargo.lock') == original_lock
    result.update(status='PASS',actual_complete_default_source=True,all_three_CLI_targets_requested=True,
                  default_features=[],server_feature_enabled=False,projected_lock_unchanged=True)
except BaseException as error:
    result.update(status='FAILED',error=repr(error))
finally:
    # Reconstructible vendor/build intermediates are bounded scratch, not evidence exports.
    # Preserve their exact identities; retain the usable native driver and all result bytes.
    features = []
    build_scripts = []
    log = RUN/'default-product-check.log'
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            try: item=json.loads(line)
            except ValueError: continue
            if item.get('reason')=='compiler-artifact': features.append({k:item.get(k) for k in ['package_id','target','features','profile','filenames','fresh']})
            if item.get('reason')=='build-script-executed': build_scripts.append(item)
    write('activated-artifacts.json',features)
    write('build-script-results.json',build_scripts)
    result['compiled_artifacts']=len(features)
    result['executed_build_scripts']=len(build_scripts)
    result['candidate_lock_unchanged_at_end']=sha(BUILD/'harness/Cargo.lock')==original_lock if 'original_lock' in globals() else None
    inventory = {str(p.relative_to(BUILD)):{'sha256':sha(p),'bytes':p.stat().st_size}
                 for p in sorted(BUILD.rglob('*')) if p.is_file() and not p.is_symlink()}
    write('build-manifest.json', inventory)
    result.update(commands=commands,elapsed_seconds=time.monotonic()-start,
                  peak_sampled_tmpfs_bytes=peak_disk,final_tmpfs_bytes=allocated(),
                  disposable_build_policy='Registry cache and compiler intermediates hash-inventoried disposable tmpfs. Exact full source snapshot, isolated lock, index provenance, actual compiled feature/artifact records, build-script records and logs retained. No final product binary was promised by cargo check.')
    write('result.json', result)
    print(json.dumps({'status':result['status'],'commands':len(commands),'error':result.get('error')}),flush=True)
sys.exit(0 if result['status']=='PASS' else 1)
