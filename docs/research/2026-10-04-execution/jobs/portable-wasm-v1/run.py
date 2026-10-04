import os,json,subprocess,tarfile,hashlib
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
w=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1');src=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/portable-source-v1');out=w/'portable-wasm-v1';out.mkdir(exist_ok=False);rows=[]
archive=w/'rust-std-1.98.1-wasm32-unknown-unknown.tar.xz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='cf1fcf68880d8b2b90128cede7416cfb82ad3584357ce9fb668f2b6244c26e55'
with tarfile.open(archive) as t:t.extractall(out,filter='data')
sysroot=out/'rust-std-1.98.1-wasm32-unknown-unknown/rust-std-wasm32-unknown-unknown'
def run(args,env={}):
 p=subprocess.run(list(map(str,args)),env={**os.environ,**env},capture_output=True,text=True,cwd=out);rows.append(dict(argv=list(map(str,args)),env_extra=env,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));(out/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n');print(args,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stderr[-6000:] or p.stdout[-6000:])
cargo='/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo';manifest=src/'cix-portable/Cargo.toml'
run([cargo,'generate-lockfile','--offline','--manifest-path',manifest])
run([cargo,'test','--offline','--locked','--manifest-path',manifest,'--lib','--','--test-threads=1'])
run([cargo,'build','--release','--offline','--locked','--manifest-path',manifest,'--target','wasm32-unknown-unknown'],{'RUSTFLAGS':'--sysroot='+str(sysroot)})
wasm=w/'target/wasm32-unknown-unknown/release/cix_portable.wasm';helper=src/'cix-native/adapters/wasm'
run(['/usr/bin/node',helper/'portable_streaming.mjs',wasm])
fixture=out/'input.bin';fixture.write_bytes(bytes((i%13 if i%97<73 else (i*29>>3)&255) for i in range(4096)))
run(['python3',helper/'differential.py','--wasm',wasm,'--node','/usr/bin/node','--cix',w/'target/debug/cix','--cixcat',w/'target/debug/cixcat','--input',fixture],{'TMPDIR':str(out)})
