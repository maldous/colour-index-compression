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
                elif allocated() >= 217_000_000: reason = '217MB early disk stop before 220MB hard tmpfs'
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
result = {'scope':'actual full default release library and three CLIs plus bounded CLI runtime; no server/fullRC proof',
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
    run([cargo,'build','--release','--offline','--locked','--manifest-path',manifest,'--lib','--bins','--no-default-features','--message-format=json-diagnostic-rendered-ansi'], 'default-product-release-build')
    assert sha(BUILD/'harness/Cargo.lock') == original_lock
    (RUN/'bin').mkdir();(RUN/'decoded').mkdir();(RUN/'archives').mkdir()
    binaries={}
    for name in ['cix','uncix','cixcat']:
        original_binary=BUILD/'target/release'/name
        dest=RUN/'bin'/name
        os.link(original_binary,dest)
        binaries[name]={'sha256':sha(dest),'bytes':dest.stat().st_size}
        run(['/usr/bin/ldd',str(dest)],name+'-actual-linkage')
        linkage=(RUN/(name+'-actual-linkage.log')).read_text()
        for library in ['libbrotlienc.so.1','libbrotlidec.so.1','libbrotlicommon.so.1']:
            assert f'{library} => /home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib/' in linkage
        for soname, target in json.loads((JOB/'standard-linkage.json').read_text())['runtime_resolutions'].items():
            row=next(line.strip() for line in linkage.splitlines() if line.strip().startswith(soname+' => '))
            actual=Path(row.split(' => ',1)[1].split(' (',1)[0])
            assert actual.resolve()==Path(target).resolve(), (soname,actual,target)
    write('binary-manifest.json',binaries)
    cix=str(RUN/'bin/cix');uncix=str(RUN/'bin/uncix');cixcat=str(RUN/'bin/cixcat')
    run([cix,'--help'],'cix-help')
    run([cix,'--version'],'cix-version')
    fixture=JOB/'fixtures'
    generic=fixture/'generic.input';original=generic.read_bytes()
    archive=RUN/'archives/generic.cix'
    run([cix,'--fast','--threads','1','--memory','268435456','-k','-o',str(archive),str(generic)],'ordinary-fast-encode')
    restored=RUN/'decoded/generic-uncix.output'
    run([uncix,'--memory','268435456','-k','-o',str(restored),str(archive)],'uncix-fresh-decode')
    assert restored.read_bytes()==original
    streamed=RUN/'decoded/generic-cixcat.output'
    run([cixcat,'--memory','268435456','-k',str(archive)],'cixcat-fresh-decode',stdout_path=streamed)
    assert streamed.read_bytes()==original
    standard_checks=[]
    for format_name in ['lz4','snappy']:
        frame=RUN/'archives'/('generic.'+format_name)
        restored=RUN/'decoded'/('generic-'+format_name+'.output')
        run([cix,'--output-format',format_name,'--memory','268435456','-k','-o',str(frame),str(generic)],format_name+'-ordinary-encode')
        run([cix,'-d','--input-format',format_name,'--memory','268435456','-k','-o',str(restored),str(frame)],format_name+'-fresh-decode')
        assert restored.read_bytes()==original
        standard_checks.append({'format':format_name,'frame_sha256':sha(frame),'frame_bytes':frame.stat().st_size,'output_sha256':sha(restored),'exact':True})
    write('standard-format-results.json',standard_checks)
    private_root=RUN/'private-paq'
    private_root.mkdir(mode=0o700)
    libraries='/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-cix-worker-v2-output/lib'
    checks=[]
    for backend in ['brotli','paq']:
        frame=fixture/(backend+'-native.cix');decoded=RUN/'decoded'/(backend+'-full-cli.output')
        command=[cix,'-d','--memory','6000000000','--threads','1','--private-library-dir',libraries,'--temporary-root',str(private_root),'-k','-o',str(decoded),str(frame)]
        run(command,backend+'-full-cli-archive-only-decode')
        assert decoded.read_bytes()==(fixture/'relocated.input').read_bytes()
        checks.append({'backend':backend,'frame_sha256':sha(frame),'output_sha256':sha(decoded),'input_bytes':decoded.stat().st_size,'exact':True})
    rejected=RUN/'decoded/bad-crc.rejected'
    run([cix,'-d','--memory','6000000000','--private-library-dir',libraries,'--temporary-root',str(private_root),'-k','-o',str(rejected),str(fixture/'brotli-crc.invalid')],'ordinary-cli-bad-crc',expected_error='checksum')
    assert not rejected.exists()
    write('runtime-results.json',{'generic_input_bytes':len(original),'generic_archive_bytes':archive.stat().st_size,'uncix_exact':True,'cixcat_exact':True,'full_dispatch_decodes':checks,'bad_crc_rejected_without_output':True,'private_worker_directory_after':list(map(str,private_root.iterdir()))})
    result.update(status='PASS',actual_release_library_and_bins_linked=True,cli_binaries=binaries,default_features=[],server_feature_enabled=False,isolated_lock_unchanged=True,standard_format_roundtrips=standard_checks,ordinary_fast_roundtrip=True,uncix_exact=True,cixcat_exact=True,full_dispatch_real_backend_decodes=2,bad_crc_rejected=True)
except BaseException as error:
    result.update(status='FAILED',error=repr(error))
finally:
    # Reconstructible vendor/build intermediates are bounded scratch, not evidence exports.
    # Preserve their exact identities; retain the usable native driver and all result bytes.
    features = []
    build_scripts = []
    log = RUN/'default-product-release-build.log'
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
                  disposable_build_policy='Exact original registry source/archive files exposed read-only and independently pinned; isolated metadata/compiler intermediates hash-inventoried tmpfs. Preserve three actual release CLI binaries, source snapshot, lock, features, buildscript/runtime records and complete archives/decoded outputs. Staticlib/cdylib counted and inventoried but not SDK export artifacts.')
    write('result.json', result)
    print(json.dumps({'status':result['status'],'commands':len(commands),'error':result.get('error')}),flush=True)
sys.exit(0 if result['status']=='PASS' else 1)
