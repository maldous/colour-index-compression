import hashlib
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('CIX_RELEASE_LEASE') == '1'
root = Path(__file__).resolve().parents[5]
w = root / 'benchmark-work/native-rc-check-v1'
src = w / 'grpc-source-v2'
out = w / 'grpc-host-v2'
out.mkdir(exist_ok=False)
binary = out / 'bin'
binary.mkdir()
sdk = w / 'sdk-bindings-relocated-cli-bindings-v8'
module = src / 'adapters/network/grpc'
rows = []
env = {**os.environ, 'GOMAXPROCS': '4', 'GOPATH': str(w / 'go-workspace'),
       'GOMODCACHE': str(w / 'go-mod-cache'), 'GOCACHE': str(w / 'go-binding-cache'),
       'GOPROXY': 'off', 'GOBIN': str(binary),
       'PATH': str(binary) + ':' + str(w / 'protoc-27.3/bin') + ':' + os.environ['PATH'],
       'PKG_CONFIG_PATH': str(sdk / 'lib/pkgconfig'), 'LD_LIBRARY_PATH': str(sdk / 'lib'),
       'CIX_NETWORK_HOST': '1', 'TMPDIR': str(out)}

def run(args, cwd=module):
    p = subprocess.run(list(map(str, args)), cwd=cwd, env=env, capture_output=True, text=True)
    rows.append(dict(argv=list(map(str, args)), cwd=str(cwd), returncode=p.returncode,
                     stdout=p.stdout, stderr=p.stderr))
    (out / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(list(map(str, args)), p.returncode, flush=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-6000:] or p.stdout[-6000:])

run(['go', 'install', '-mod=mod', 'google.golang.org/protobuf/cmd/protoc-gen-go',
     'google.golang.org/grpc/cmd/protoc-gen-go-grpc'], cwd=module / 'tools')
run(['make', 'generate'])
run(['go', 'mod', 'tidy'])
run(['go', 'test', './...', '-count=1'])
(out / 'generated.json').write_text(json.dumps({str(p.relative_to(module)):
    hashlib.sha256(p.read_bytes()).hexdigest() for p in module.rglob('*') if p.is_file()}, indent=2) + '\n')
