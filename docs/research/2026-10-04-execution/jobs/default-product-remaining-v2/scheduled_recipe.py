#!/usr/bin/env python3
"""One offline complete default release CLI qualification. No product tree is writable."""
import hashlib, json, os, shutil, signal, subprocess, sys, tarfile, time, gzip
from pathlib import Path

JOB = Path(__file__).resolve().parent
ROOT = Path('/home/user/src/colour-index-compression')
SCRATCH = Path(os.environ['CIX_CHECK_SCRATCH'])
RUN = SCRATCH / 'run'
BUILD = SCRATCH / 'build'
TOOLCHAIN = Path('/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin')
start = time.monotonic()
deadline = start + 260
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

def run(command, label, expected_error=None, stdout_path=None):
    global peak_disk
    began = time.monotonic()
    log = RUN / (label + '.log')
    with log.open('xb') as stream:
        data_stream = stdout_path.open('xb') if stdout_path is not None else None
        p = subprocess.Popen(command, cwd=BUILD/'harness', env=ENV,
                             stdout=data_stream or stream, stderr=stream if data_stream else subprocess.STDOUT, start_new_session=True)
        reason = None
        try:
            while p.poll() is None:
                peak_disk = max(peak_disk, allocated())
                if time.monotonic() >= deadline: reason = '260-second inner wall limit'
                elif allocated() >= 167_000_000: reason = '167MB early disk stop before 170MB hard tmpfs'
                elif log.stat().st_size >= 1_000_000: reason = '1MB log cap'
                if reason:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                    break
                time.sleep(.02)
        finally:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            if data_stream is not None: data_stream.close()
    commands.append({'command': command, 'label': label, 'exit': p.returncode,
                     'seconds': time.monotonic()-began, 'stop_reason': reason})
    assert reason is None, f'{label}: {reason}'
    if expected_error is None:
        assert p.returncode == 0, f'{label}: exit {p.returncode}'
    else:
        assert p.returncode == 2 and expected_error in log.read_text(), f'{label}: unexpected rejection {p.returncode}'

assert not RUN.exists() and not BUILD.exists()
RUN.mkdir(); BUILD.mkdir()
for n in ['cargo-home', 'tmp', 'target']: (BUILD/n).mkdir()
(BUILD/'harness').mkdir()
ENV = {'PATH':str(TOOLCHAIN)+':/usr/bin:/bin', 'HOME':str(BUILD),
       'CARGO_HOME':str(BUILD/'cargo-home'), 'CARGO_TARGET_DIR':str(BUILD/'target'),
       'RUSTC':str(TOOLCHAIN/'rustc'), 'CARGO_BUILD_JOBS':'1', 'CARGO_INCREMENTAL':'0',
       'TMPDIR':str(BUILD/'tmp'), 'PYTHONDONTWRITEBYTECODE':'1', 'LC_ALL':'C',
       'CARGO_NET_OFFLINE':'true', 'CARGO_HTTP_MULTIPLEXING':'false', 'CARGO_CACHE_AUTO_CLEAN_FREQUENCY':'never',
       'CIX_NATIVE_LIBRARY_DIR':'/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib',
       'RUSTFLAGS':'-C link-arg=-Wl,-rpath,/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib -L native=/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix/usr/lib/x86_64-linux-gnu'}
result = {'scope':'remaining actual CLI checks using qualified V4 executable plus exact fullcfgtest libtest; no server/fullRC proof',
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
    source_cache = BUILD/'cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
    cache.mkdir(parents=True);source_cache.mkdir(parents=True)
    for package in json.loads((JOB/'readonly-cache-layout.json').read_text()):
        archive=Path(package['archive']);assert sha(archive)==package['archive_sha256']
        (cache/archive.name).symlink_to(archive)
        (source_cache/package['name']).symlink_to(package['source'],target_is_directory=True)
    write('readonly-cache-links.json', json.loads((JOB/'readonly-cache-layout.json').read_text()))
    (BUILD/'cargo-home/config.toml').write_text('[registries.crates-io]\nprotocol = "sparse"\n[net]\noffline = true\nretry = 0\n')
    # Preserve actual full source snapshot, including currently uncommitted peer
    # source, as evidence before compilation; this is not a product-tree edit.
    with (RUN/'source-snapshot.tar.gz').open('xb') as stream:
        with gzip.GzipFile(filename='',mode='wb',fileobj=stream,compresslevel=1,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w|') as tar:
                tar.add(BUILD/'harness',arcname='crate')
    cargo = str(TOOLCHAIN/'cargo')
    manifest = str(BUILD/'harness/Cargo.toml')
    run(['/usr/bin/python3','-I','-B',str(JOB/'probe.py')],'actual-namespace-combined-preflight')
    preflight=json.loads((RUN/'actual-namespace-combined-preflight.log').read_text())
    assert preflight['status']=='PASS'
    # Reuse the exact already-qualified V4 executable; do not rebuild three CLIs.
    prior=ROOT/'benchmark-work/native-rc-check-v1/default-product-runtime-v4/evidence'
    prior_manifest=json.loads((prior/'artifact-manifest.json').read_text())
    (RUN/'bin').mkdir();(RUN/'decoded').mkdir()
    with tarfile.open(prior/'scratch-recovery.tar.gz','r:gz') as tar:
        member=tar.getmember('run/bin/cix')
        assert member.isfile() and member.size==5252912
        binary=tar.extractfile(member).read()
        assert {'bytes':len(binary),'sha256':hashlib.sha256(binary).hexdigest()}==prior_manifest['bin/cix']
        assert hashlib.sha256(binary).hexdigest()=='e02ba48b7749536de5e35f667750f77be17d297db6b41af23aa8fa4ae0284747'
        (RUN/'bin/cix').write_bytes(binary);(RUN/'bin/cix').chmod(member.mode & 0o777)
    cix=str(RUN/'bin/cix')
    write('reused-cix.json',{'bytes':len(binary),'sha256':sha(RUN/'bin/cix'),'prior_recovery_sha256':sha(prior/'scratch-recovery.tar.gz'),'no_product_rebuild':True})
    run(['/usr/bin/ldd',cix],'reused-cix-actual-linkage')
    linkage=(RUN/'reused-cix-actual-linkage.log').read_text()
    for library in ['libbrotlienc.so.1','libbrotlidec.so.1','libbrotlicommon.so.1']:
        assert f'{library} => /home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib/' in linkage
    for soname,target in json.loads((JOB/'standard-linkage.json').read_text())['runtime_resolutions'].items():
        row=next(line.strip() for line in linkage.splitlines() if line.strip().startswith(soname+' => '))
        assert Path(row.split(' => ',1)[1].split(' (',1)[0]).resolve()==Path(target).resolve()
    fixture=JOB/'fixtures';private_root=RUN/'private-paq';assert private_root.is_dir() and private_root.stat().st_mode & 0o777 == 0o700
    libraries='/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-cix-worker-v2-output/lib'
    for name in ['paq-cixp.cix','paq-native.cix','brotli-crc.invalid','relocated.input']:
        shutil.copyfile(fixture/name,RUN/name)
    decoded=RUN/'decoded/paq-full-cli.output'
    common=[cix,'-d','--memory','6000000000','--threads','1','--private-library-dir',libraries,'--temporary-root',str(private_root),'-k']
    run([*common,'-o',str(decoded),str(fixture/'paq-cixp.cix')],'corrected-paq-full-cli-archive-only-decode')
    assert decoded.read_bytes()==(fixture/'relocated.input').read_bytes()
    for name,label,error in [('brotli-crc.invalid','ordinary-cli-bad-crc','checksum'),('paq-native.cix','old-raw-paq-frame-rejected','invalid CIXP frame')]:
        rejected=RUN/'decoded'/(label+'.rejected')
        run([*common,'-o',str(rejected),str(fixture/name)],label,expected_error=error)
        assert not rejected.exists()
    assert not list(private_root.iterdir())
    write('remaining-runtime-results.json',{'corrected_paq_exact':True,'input_bytes':decoded.stat().st_size,'decoded_sha256':sha(decoded),'corrected_frame_sha256':sha(fixture/'paq-cixp.cix'),'bad_crc_rejected_without_output':True,'old_raw_paq_frame_rejected_without_output':True,'private_worker_directory_empty':True})
    run([cargo,'test','--release','--offline','--locked','--manifest-path',manifest,'--lib','--no-default-features','--message-format=json-diagnostic-rendered-ansi','full_engine::io::tests::prefixes_are_exact','--','--exact','--test-threads=1'], 'prefix-regression-test')
    test_log=(RUN/'prefix-regression-test.log').read_text()
    assert 'test full_engine::io::tests::prefixes_are_exact ... ok' in test_log
    assert 'test result: ok. 1 passed; 0 failed;' in test_log
    test_artifacts=[]
    for line in test_log.splitlines():
        try: item=json.loads(line)
        except ValueError: continue
        if item.get('reason')=='compiler-artifact' and item.get('profile',{}).get('test') and item.get('executable'):
            test_artifacts.append(item)
    assert len(test_artifacts)==1, test_artifacts
    test_binary=Path(test_artifacts[0]['executable'])
    assert test_binary.is_relative_to(BUILD/'target')
    os.link(test_binary,RUN/'bin/prefix-regression-test')
    write('focused-test-artifact.json',{'artifact':test_artifacts[0],'sha256':sha(test_binary),'bytes':test_binary.stat().st_size,'one_exact_test_passed':True})
    result['focused_prefix_regression_passed']=True
    result.update(status='PASS',reused_qualified_cix=True,corrected_paq_full_cli_exact=True,bad_crc_rejected=True,old_raw_frame_rejected=True,default_features=[],server_feature_enabled=False,isolated_lock_unchanged=sha(BUILD/'harness/Cargo.lock')==original_lock)
except BaseException as error:
    result.update(status='FAILED',error=repr(error))
finally:
    # Reconstructible vendor/build intermediates are bounded scratch, not evidence exports.
    # Preserve their exact identities; retain the usable native driver and all result bytes.
    features = []
    build_scripts = []
    log = RUN/'prefix-regression-test.log'
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
    readonly_links = {str(p.relative_to(BUILD)):os.readlink(p) for p in sorted(BUILD.rglob('*')) if p.is_symlink()}
    write('readonly-link-inventory.json',readonly_links)
    write('build-manifest.json', inventory)
    result.update(commands=commands,elapsed_seconds=time.monotonic()-start,
                  peak_sampled_tmpfs_bytes=peak_disk,final_tmpfs_bytes=allocated(),
                  disposable_build_policy='Exact original registry source/archive files exposed read-only and independently pinned; isolated metadata/compiler intermediates hash-inventoried tmpfs. Preserve reused qualified V4 CIX and actual focused test binary when produced, source snapshot, lock, features, buildscript/runtime records and complete archives/decoded outputs. Staticlib/cdylib counted and inventoried but not SDK export artifacts.')
    write('result.json', result)
    print(json.dumps({'status':result['status'],'commands':len(commands),'error':result.get('error')}),flush=True)
sys.exit(0 if result['status']=='PASS' else 1)
