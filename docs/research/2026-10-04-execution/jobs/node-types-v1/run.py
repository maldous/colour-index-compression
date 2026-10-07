#!/usr/bin/env python3
import hashlib,json,os,resource,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[5];J=Path(__file__).resolve().parent
TROOT=Path('/usr/local/lib/node_modules/netlify-cli/node_modules');T=TROOT/'typescript/bin/tsc'; TYPES=TROOT/'@types'; NODE=Path('/bin/node'); CAP=1<<20
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def k(p):
 try:return str(p.relative_to(R))
 except:return str(p)
def files():
 base=[R/'rust/cix-native/bindings/node/package.json',R/'rust/cix-native/bindings/node/index.d.ts',R/'rust/cix-native/bindings/node/test/typed-consumer/index.ts',R/'rust/cix-native/bindings/node/test/typed-consumer/tsconfig.json',J/'run.py',J/'spec.json',NODE,T]
 # Pin the executable TypeScript implementation and all declaration files it
 # resolves, including undici-types used by current @types/node.
 for root,pattern in ((TROOT/'typescript/lib','*.js'),(TYPES/'node','*.d.ts'),(TROOT/'undici-types','*.d.ts')):
  base.extend(sorted(root.rglob(pattern)))
 return base
def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP))
if os.environ.get('CIX_RELEASE_LEASE')!='1':raise RuntimeError('root scheduler lease required')
if any((J/name).exists() for name in ('receipt.json','typecheck.stdout.log','typecheck.stderr.log')):raise RuntimeError('refusing overwrite evidence')
fs=files()
if any(not p.is_file() for p in fs):raise RuntimeError('required TypeScript runtime input missing')
before={k(p):h(p) for p in fs};out=J/'typecheck.stdout.log';err=J/'typecheck.stderr.log'
argv=[str(NODE),str(T),'--noEmit','--typeRoots',str(TYPES),'-p',str(R/'rust/cix-native/bindings/node/test/typed-consumer/tsconfig.json')]
try:
 with out.open('xb') as so,err.open('xb') as se:r=subprocess.run(argv,cwd=R,env={'PATH':'/usr/bin:/bin'},stdout=so,stderr=se,timeout=60,preexec_fn=limit)
 code=r.returncode;error=None
except Exception as e: code=None;error=str(e)
after={k(p):h(p) for p in fs};ok=code==0 and before==after
receipt={'status':'pass' if ok else 'fail','returncode':code,'error':error,'argv':argv,'node_version':subprocess.check_output([str(NODE),'--version'],text=True).strip(),'typescript_version':subprocess.check_output([str(NODE),str(T),'--version'],text=True).strip(),'input_sha256_before':before,'input_sha256_after':after,'file_size_cap_bytes':CAP,'wall_seconds':60,'scope':'TypeScript declarations only; native addon is not loaded'}
(J/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if not ok:raise SystemExit(1)
