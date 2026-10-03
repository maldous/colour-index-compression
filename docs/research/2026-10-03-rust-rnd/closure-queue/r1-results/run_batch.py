import hashlib,json,subprocess,zlib,time,os
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');base=root/'benchmark-work/closure-r1';area=root/'docs/research/2026-10-03-rust-rnd/closure-queue/r1-results';exe=base/'build/r1';cix=root/'benchmark-work/release-6ac0/final/cix';uncix=cix.with_name('uncix')
os.environ['PATH']='/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin:/usr/bin:/bin'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[]
for kind in ['strong','weak','absent']:
 d=base/kind;d.mkdir(exist_ok=True);p=d/'input.bin'
 subprocess.run(['/usr/bin/python3',str(root/'rust/cix-native/experiments/representation-closure-r1/fixtures.py'),kind,str(p)],check=True)
 inputs.append({'kind':kind,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
(area/'execution-binding.json').write_text(json.dumps({'before_codec':True,'driver_binary_sha256':sha(exe),'inputs':inputs,'backend':json.loads((root/'docs/research/2026-10-03-rust-rnd/release-6ac0/native-release.json').read_text())},indent=2)+'\n')
results=[]
for inp in inputs:
 d=Path(inp['path']).parent;p=d/'selected.r1';r=d/'rows.jsonl';start=time.monotonic()
 subprocess.run([str(exe),'screen',inp['path'],str(p),str(r),str(cix),str(uncix),'fast'],cwd=root,check=True)
 rows=[json.loads(l) for l in r.read_text().splitlines()];candidates=[v for v in rows if 'candidate' in v];assert len(candidates)==17 and all(v['verified'] for v in candidates)
 assert rows[-1]['complete_bytes']==min(v['complete_bytes'] for v in candidates) and rows[-1]['fresh_archive_only_decode']
 assert sha(d/'rsl1-scratch/selected.archive-only.restored')==inp['sha256']
 malformed=[];valid=p.read_bytes();body=valid[:-4];op=bytearray(body);op[23]=255
 for name,data in [('crc',valid[:-1]+bytes([valid[-1]^1])),('opcode',bytes(op)+zlib.crc32(op).to_bytes(4,'little')),('truncated',valid[:-1])]:
  bad=d/(name+'.bad');bad.write_bytes(data);out=d/(name+'.out');v=subprocess.run([str(exe),'decode',str(bad),str(out),str(uncix)],cwd=root,capture_output=True,text=True);assert v.returncode and 'panicked' not in v.stderr and not out.exists();malformed.append({'case':name,'exit':v.returncode,'stderr':v.stderr})
 results.append({'input':inp,'rows':rows,'archive_sha256':sha(p),'elapsed_seconds':time.monotonic()-start,'malformed':malformed})
 (area/(inp['kind']+'-rows.jsonl')).write_bytes(r.read_bytes())
 (area/'results.json').write_text(json.dumps({'status':'PARTIAL' if len(results)<3 else 'VERIFIED_SINGLE_SCREEN','controls':results},indent=2)+'\n')
