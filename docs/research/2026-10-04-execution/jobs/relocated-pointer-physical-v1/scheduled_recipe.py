#!/usr/bin/env python3
"""One offline actual-module qualification. No product tree is writable."""
import hashlib, json, os, shutil, signal, subprocess, sys, tarfile, time, zlib
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

def run(command, label, expected_error=None):
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
    assert reason is None, f'{label}: {reason}'
    if expected_error is None:
        assert p.returncode == 0, f'{label}: exit {p.returncode}'
    else:
        assert p.returncode == 2 and 'CIX_PHYSICAL_ERROR:' in log.read_text() and expected_error in log.read_text(), f'{label}: unexpected rejection {p.returncode}'

assert not RUN.exists() and not BUILD.exists()
RUN.mkdir(); BUILD.mkdir()
for n in ['cargo-home', 'tmp', 'target', 'vendor']: (BUILD/n).mkdir()
for n in ['frames', 'decoded', 'payloads', 'calls']: (RUN/n).mkdir()
ENV = {'PATH':str(TOOLCHAIN)+':/usr/bin:/bin', 'HOME':str(BUILD),
       'CARGO_HOME':str(BUILD/'cargo-home'), 'CARGO_TARGET_DIR':str(BUILD/'target'),
       'RUSTC':str(TOOLCHAIN/'rustc'), 'CARGO_BUILD_JOBS':'1', 'CARGO_INCREMENTAL':'0',
       'TMPDIR':str(BUILD/'tmp'), 'PYTHONDONTWRITEBYTECODE':'1', 'LC_ALL':'C',
       'CARGO_NET_OFFLINE':'true', 'OMP_NUM_THREADS':'1',
       'RUSTFLAGS':'-L native=/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib -C link-arg=-Wl,-rpath,/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib'}
result = {'scope':'real PAQ/Brotli relocated-pointer physical framing; no full-product dispatch/service/CLI proof',
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
    run([cargo,'build','--offline','--locked','--manifest-path',manifest,'--bin','physical-driver'], 'native-physical-driver-build')
    driver = BUILD/'target/debug/physical-driver'
    shutil.copyfile(driver, RUN/'physical-driver')
    run(['/usr/bin/ldd',str(driver)], 'actual-driver-linkage')
    linkage = (RUN/'actual-driver-linkage.log').read_text()
    for name in ['libbrotlienc.so.1','libbrotlidec.so.1','libbrotlicommon.so.1']:
        assert f'{name} => /home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib/' in linkage
    fixture = JOB/'harness/tests/fixtures/ecoff_relocated_reference'
    original = (fixture/'original.tar').read_bytes()
    canonical = fixture/'mode5-shared1.raw'
    sys.path.insert(0,str(ROOT/'runtime'))
    from cix_runtime.legacy import ecoff_relocated_pointers as reference
    from cix_runtime.legacy.multinomial import vencode, vdecode
    cases = []
    negatives = []
    def invoke(operation, backend, source, target, label, error=None):
        work = RUN/'calls'/label
        work.mkdir()
        run([str(driver),operation,backend,str(source),str(target),str(work)],label,error)
        if error is not None:
            assert not target.exists(), 'rejected operation wrote final output'
            negatives.append({'label':label,'expected_error':error,'rejected':True,'output_absent':True})
    for selector, backend in enumerate(['brotli','paq']):
        frame = RUN/'frames'/(backend+'-native.cix')
        invoke('encode-frame',backend,fixture/'original.tar',frame,backend+'-native-frame-encode')
        restored = RUN/'decoded'/(backend+'-native.decoded')
        invoke('decode-frame',backend,frame,restored,backend+'-native-frame-decode')
        assert restored.read_bytes() == original
        encoded = frame.read_bytes()
        assert encoded[:6] == b'CIXB\x0a'+bytes([selector])
        length, at = vdecode(encoded,6)
        assert length == len(original)
        assert int.from_bytes(encoded[at:at+4],'big') == zlib.crc32(original)
        payload = RUN/'payloads'/(backend+'-native.payload')
        payload.write_bytes(encoded[at+4:])
        decoded_raw = RUN/'decoded'/(backend+'-raw.decoded')
        invoke('decode-payload',backend,payload,decoded_raw,backend+'-independent-payload-decode')
        assert decoded_raw.read_bytes() == canonical.read_bytes()
        reference_restored = reference.inverse(decoded_raw.read_bytes())
        assert reference_restored == original
        (RUN/'decoded'/(backend+'-reference-inverse.decoded')).write_bytes(reference_restored)
        reference_payload = RUN/'payloads'/(backend+'-reference.payload')
        invoke('encode-payload',backend,canonical,reference_payload,backend+'-reference-raw-encode')
        reference_frame = RUN/'frames'/(backend+'-reference.cix')
        reference_bytes = b'CIXB\x0a'+bytes([selector])+vencode(len(original))+zlib.crc32(original).to_bytes(4,'big')+reference_payload.read_bytes()
        reference_frame.write_bytes(reference_bytes)
        assert encoded == reference_bytes, backend+' complete native/reference frame mismatch'
        cross = RUN/'decoded'/(backend+'-reference-frame.decoded')
        invoke('decode-frame',backend,reference_frame,cross,backend+'-reference-frame-native-decode')
        assert cross.read_bytes() == original
        for mutation, position, value, reason in [('crc',at,encoded[at]^1,'checksum mismatch'),('selector',5,2,'invalid executable backend selector')]:
            bad = bytearray(encoded);bad[position]=value
            path = RUN/'frames'/(backend+'-'+mutation+'.invalid');path.write_bytes(bad)
            invoke('decode-frame',backend,path,RUN/'decoded'/(backend+'-'+mutation+'.rejected'),backend+'-reject-'+mutation,reason)
        if backend == 'brotli':
            path=RUN/'frames'/'brotli-truncated.invalid';path.write_bytes(encoded[:-1])
            invoke('decode-frame',backend,path,RUN/'decoded'/'brotli-truncated.rejected','brotli-reject-truncated','brotli truncated, invalid or oversized data')
        cases.append({'backend':backend,'input_bytes':len(original),'raw_bytes':canonical.stat().st_size,'payload_bytes':payload.stat().st_size,'framing_bytes':at+4,'archive_bytes':len(encoded),'archive_sha256':sha(frame),'native_reference_frame_equal':True,'fresh_native_archive_decodes':2,'independent_payload_reference_inverse':True})
    assert sha(BUILD/'harness/Cargo.lock') == original_lock
    write('case-results.json',cases)
    write('negative-results.json',negatives)
    result.update(status='PASS',native_physical_archives=2,reference_physical_archives=2,fresh_archive_only_decodes=4,independent_reference_inverse_crossdecodes=2,negative_checks=len(negatives),projected_lock_unchanged=True,cases=cases)
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
