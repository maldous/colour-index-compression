import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('CIX_RELEASE_LEASE') == '1'
root = Path(__file__).resolve().parents[5]
w = root / 'benchmark-work/native-rc-check-v1'
out = w / 'rocksdb-host-v1'
out.mkdir(exist_ok=False)
upstream = w / 'rocksdb-source-v1'
sdk = w / 'sdk-bindings-relocated-cli-bindings-v8'
rows = []

def run(args, env=None):
    p = subprocess.run(list(map(str, args)), cwd=out, env={**os.environ, **(env or {})},
                       capture_output=True, text=True)
    rows.append(dict(argv=list(map(str, args)), env_extra=env or {}, returncode=p.returncode,
                     stdout=p.stdout, stderr=p.stderr))
    (out / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(list(map(str, args)), p.returncode, flush=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-7000:] or p.stdout[-7000:])

build = out / 'upstream-build'
run(['cmake', '-S', upstream, '-B', build, '-DCMAKE_BUILD_TYPE=Release',
     '-DPORTABLE=ON', '-DWITH_LIBURING=OFF', '-DWITH_GFLAGS=OFF',
     '-DWITH_TESTS=OFF', '-DWITH_BENCHMARK_TOOLS=OFF', '-DWITH_CORE_TOOLS=OFF',
     '-DWITH_TOOLS=OFF', '-DWITH_TRACE_TOOLS=OFF', '-DWITH_EXAMPLES=OFF',
     '-DWITH_SNAPPY=OFF', '-DWITH_LZ4=OFF', '-DWITH_ZLIB=OFF', '-DWITH_ZSTD=OFF'])
run(['cmake', '--build', build, '--target', 'rocksdb-shared', '-j4'])
adapter = out / 'adapter'
run(['cmake', '-S', w / 'rocksdb-adapter-source-v1', '-B', adapter,
     '-DCIX_NATIVE_INCLUDE_DIR=' + str(sdk / 'include'),
     '-DCIX_NATIVE_LIBRARY=' + str(sdk / 'lib/libcix_native.so'),
     '-DROCKSDB_INCLUDE_DIR=' + str(upstream / 'include'),
     '-DROCKSDB_LIBRARY=' + str(build / 'librocksdb.so')])
run(['cmake', '--build', adapter, '-j4'])
run(['ctest', '--test-dir', adapter, '--output-on-failure'], {'TMPDIR': str(out)})
