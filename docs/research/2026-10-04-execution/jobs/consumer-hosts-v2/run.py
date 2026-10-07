import hashlib
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('CIX_RELEASE_LEASE') == '1'
root = Path(__file__).resolve().parents[5]
w = root / 'benchmark-work/native-rc-check-v1'
src = w / 'consumer-hosts-source-v2'
out = w / 'consumer-hosts-v2'
out.mkdir(exist_ok=False)
sdk = w / 'sdk-bindings-relocated-cli-bindings-v8'
receipt = {'components': {}, 'native_sha256': hashlib.sha256((sdk / 'lib/libcix_native.so').read_bytes()).hexdigest()}
active = None

def run(args, env=None, cwd=None):
    result = subprocess.run(list(map(str, args)), env={**os.environ, **(env or {})},
                            cwd=cwd or out, capture_output=True, text=True)
    receipt['components'][active]['commands'].append(dict(
        argv=list(map(str, args)), env_extra=env or {}, cwd=str(cwd or out),
        returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    save()
    print(active, list(map(str, args)), result.returncode, flush=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-5000:] or result.stdout[-5000:])

def save():
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def sevenzip():
    upstream = w / 'sevenzip-source-v1'
    build = out / 'sevenzip-adapter'
    prefix = out / 'sevenzip-prefix'
    run(['cmake', '-S', src / 'adapters/sevenzip', '-B', build,
         '-DCIX_NATIVE_INCLUDE_DIR=' + str(sdk / 'include'),
         '-DCIX_NATIVE_LIBRARY=' + str(sdk / 'lib/libcix_native.so'),
         '-DCIX_7ZIP_SDK_ROOT=' + str(upstream),
         '-DCIX_7ZIP_SDK_ARCHIVE_SHA256=9cbde5099c6deb73691b0579063da5827522ccbbcba3f0020fd04e8c8c16c0d4',
         '-DCIX_7ZIP_BUILD_CONTRACT=ON', '-DCMAKE_INSTALL_PREFIX=' + str(prefix)])
    run(['cmake', '--build', build, '-j4'])
    run([build / 'cix_7zip_contract'])
    run(['cmake', '--install', build])
    # Each official makefile already declares Z7_EXTERNAL_CODECS. Object output
    # is outside the pinned, unchanged upstream source tree.
    for name, rel in [('console', 'CPP/7zip/UI/Console'), ('format', 'CPP/7zip/Bundles/Format7zF')]:
        objects = out / ('sevenzip-' + name)
        objects.mkdir()
        run(['make', '-f', 'makefile.gcc', '-j4', 'O=' + str(objects)], cwd=upstream / rel)
    run(['sh', src / 'adapters/sevenzip/host-closure.sh',
         out / 'sevenzip-console/7z', out / 'sevenzip-format/7z.so',
         prefix / 'Codecs/libcix_7zip_experimental_module.so',
         prefix / 'Codecs/libcix_native.so', out / 'sevenzip-host-closure', '/usr/bin/sha256sum'])

def http():
    run(['/usr/bin/go', '-C', src / 'adapters/network', 'test', './...', '-count=1'], {
        'PKG_CONFIG_PATH': str(sdk / 'lib/pkgconfig'), 'LD_LIBRARY_PATH': str(sdk / 'lib'),
        'GOCACHE': str(w / 'go-binding-cache'), 'GOPROXY': 'off', 'CIX_NETWORK_HOST': '1'})

def wasm():
    binary = w / 'target/wasm32-unknown-unknown/release/cix_portable.wasm'
    run(['/usr/bin/node', src / 'adapters/wasm/portable_streaming.mjs', binary])
    run(['python3', src / 'adapters/wasm/run_browser_streaming.py', '--wasm', binary,
         '--chromium', '/opt/google/chrome/chrome'], {'TMPDIR': str(out)})

for name, function in [('sevenzip', sevenzip), ('http', http), ('wasm', wasm)]:
    active = name
    receipt['components'][name] = {'status': 'running', 'commands': []}
    try:
        function()
        receipt['components'][name]['status'] = 'pass'
    except Exception as error:
        receipt['components'][name].update(status='fail', error=str(error))
    save()
raise SystemExit(int(any(v['status'] != 'pass' for v in receipt['components'].values())))
