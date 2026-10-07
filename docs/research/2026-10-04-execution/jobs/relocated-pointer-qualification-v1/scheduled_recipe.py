#!/usr/bin/env python3
"""One offline actual-module qualification. No product tree is writable."""
import hashlib, json, os, shutil, signal, subprocess, sys, tarfile, time
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
for n in ['cargo-home', 'tmp', 'target', 'vendor']: (BUILD/n).mkdir()
for n in ['native-raw', 'decoded']: (RUN/n).mkdir()
ENV = {'PATH':str(TOOLCHAIN)+':/usr/bin:/bin', 'HOME':str(BUILD),
       'CARGO_HOME':str(BUILD/'cargo-home'), 'CARGO_TARGET_DIR':str(BUILD/'target'),
       'RUSTC':str(TOOLCHAIN/'rustc'), 'CARGO_BUILD_JOBS':'1', 'CARGO_INCREMENTAL':'0',
       'TMPDIR':str(BUILD/'tmp'), 'PYTHONDONTWRITEBYTECODE':'1', 'LC_ALL':'C',
       'CARGO_NET_OFFLINE':'true'}
result = {'scope':'eight actual modules; no full-product dispatch/service/CLI/physical codec proof',
          'admission':os.environ['CIX_CHECK_ADMISSION'], 'benchmarks':'HOLD'}
try:
    shutil.copytree(JOB/'harness', BUILD/'harness')
    original_lock = sha(BUILD/'harness/Cargo.lock')
    packages = json.loads((JOB/'archive-inputs.json').read_text())
    for package in packages:
        path = Path(package['path'])
        assert sha(path) == package['checksum']
        prefix = package['name']+'-'+package['version']
        with tarfile.open(path, 'r:gz') as tar:
            for member in tar:
                parts = Path(member.name).parts
                assert parts and parts[0] == prefix and '..' not in parts
                assert member.isfile() or member.isdir(), 'unexpected archive link/type'
                tar.extract(member, BUILD/'vendor', filter='data')
        vendor = BUILD/'vendor'/prefix
        files = {str(p.relative_to(vendor)):sha(p) for p in sorted(vendor.rglob('*')) if p.is_file()}
        (vendor/'.cargo-checksum.json').write_text(json.dumps({'files':files,'package':package['checksum']}))
    (BUILD/'cargo-home/config.toml').write_text('[source.crates-io]\nreplace-with = "frozen-vendor"\n[source.frozen-vendor]\ndirectory = '+json.dumps(str(BUILD/'vendor'))+'\n[net]\noffline = true\n')
    cargo = str(TOOLCHAIN/'cargo')
    manifest = str(BUILD/'harness/Cargo.toml')
    run([cargo,'test','--offline','--locked','--manifest-path',manifest,'--test','relocated_pointer_contract','--','--test-threads=1'], 'nine-contract-groups')
    run([cargo,'test','--offline','--locked','--manifest-path',manifest,'--lib','full_engine::address_relations::tests::','--','--test-threads=1'], 'affected-address-regressions')
    run([cargo,'build','--offline','--locked','--manifest-path',manifest,'--bin','relocated-driver'], 'native-driver-build')
    driver = BUILD/'target/debug/relocated-driver'
    shutil.copyfile(driver, RUN/'relocated-driver')
    fixture = JOB/'harness/tests/fixtures/ecoff_relocated_reference'
    original = (fixture/'original.tar').read_bytes()
    sys.path.insert(0, str(ROOT/'runtime'))
    from cix_runtime.legacy import ecoff_relocated_pointers as reference
    cases = []
    for mode in range(6):
        for shared in range(2):
            name = f'mode{mode}-shared{shared}.raw'
            native = RUN/'native-raw'/name
            run([str(driver),'encode',str(fixture/'original.tar'),str(native),str(mode),str(shared)], 'encode-'+name)
            assert native.read_bytes() == (fixture/name).read_bytes(), name+' golden mismatch'
            assert reference.inverse(native.read_bytes()) == original, name+' reference inverse mismatch'
            for origin, encoded in [('reference', fixture/name),('native',native)]:
                decoded = RUN/'decoded'/(origin+'-'+name+'.decoded')
                run([str(driver),'decode',str(encoded),str(decoded)], 'decode-'+origin+'-'+name)
                assert decoded.read_bytes() == original, name+' fresh decode mismatch'
            cases.append({'name':name,'native_sha256':sha(native),'bytes':native.stat().st_size,
                          'golden_equal':True,'reference_inverse_equal':True,'fresh_process_decodes':2})
    assert sha(BUILD/'harness/Cargo.lock') == original_lock
    write('case-results.json', cases)
    result.update(status='PASS',raw_golden_equalities=12,reference_inverse_crossdecodes=12,fresh_process_decodes=24,
                  integration_test_groups=9,projected_lock_unchanged=True)
except BaseException as error:
    result.update(status='FAILED',error=repr(error))
finally:
    # Reconstructible vendor/build intermediates are bounded scratch, not evidence exports.
    # Preserve their exact identities; retain the usable native driver and all result bytes.
    inventory = {str(p.relative_to(BUILD)):{'sha256':sha(p),'bytes':p.stat().st_size}
                 for p in sorted(BUILD.rglob('*')) if p.is_file() and not p.is_symlink()}
    write('build-manifest.json', inventory)
    result.update(commands=commands,elapsed_seconds=time.monotonic()-start,
                  peak_sampled_tmpfs_bytes=peak_disk,final_tmpfs_bytes=allocated(),
                  disposable_build_policy='Vendor and build intermediates hash-inventoried; original archive and source pins permit reconstruction. Native driver, raw vectors, exact decodes and logs retained.')
    write('result.json', result)
    print(json.dumps({'status':result['status'],'commands':len(commands),'error':result.get('error')}),flush=True)
sys.exit(0 if result['status']=='PASS' else 1)
