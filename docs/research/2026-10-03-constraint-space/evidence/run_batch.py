import hashlib, itertools, json, subprocess, time, zlib
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression')
AREA=ROOT/'docs/research/2026-10-03-constraint-space/evidence'
BIN=ROOT/'benchmark-work/constraint-space/build/csp'
cases=[
 ('byte-none','byte',2,0,0,0,0,0,0,0,32513,65536),
 ('byte-A','byte',2,1,0,0,128,0,0,0,32513,32768),
 ('byte-B','byte',2,2,0,0,0,127,0,0,32513,33024),
 ('byte-intersection','byte',2,3,0,0,128,127,0,0,32513,256),
 ('byte-contradiction','byte',2,3,0,0,127,127,0,0,32513,0),
 ('byte-expensive','byte',2,2,0,0,0,0,0,0,32513,65536),
 ('nibble-none','nibble',5,0,0,0,0,0,0,0,0,1048576),
 ('nibble-equality','nibble',5,1,15,0,0,0,0,0,0,16),
 ('nibble-even','nibble',5,2,0,0,2,0,0,0,0,524288),
 ('nibble-intersection','nibble',5,3,15,0,2,0,0,0,0,8),
 ('nibble-singleton','nibble',5,4,0,0,0,0,0,5,0,1),
 ('nibble-redundant','nibble',5,5,15,0,0,0,0,5,0,1),
 ('nibble-mod16','nibble',2,2,0,0,16,15,0,0,255,16),
]
def run(args,name,ok=True):
 t=time.monotonic();p=subprocess.run([str(BIN),*map(str,args)],capture_output=True,text=True)
 (AREA/'raw'/f'{name}.stdout').write_text(p.stdout);(AREA/'raw'/f'{name}.stderr').write_text(p.stderr)
 if ok: assert p.returncode==0,(name,p.stderr)
 return p,time.monotonic()-t
def independent(c):
 _,domain,n,mask,eq,mp,mod,res,hv,hc,_,_=c
 base=256 if domain=='byte' else 16
 count=0
 for x in itertools.product(range(base),repeat=n):
  if domain=='byte': good=not(mask&1 and x[0]>=mod) and not(mask&2 and x[0]<res)
  else: good=not(mask&1 and any(eq&(1<<p) and x[p]!=x[p+1] for p in range(n-1))) and not(mask&2 and x[mp]%mod!=res) and not(mask&4 and x.count(hv)!=hc)
  count+=good
 return count
rows=[]
for c in cases:
 name,*rest=c;model=rest[:9];x=rest[9];expected=rest[10]
 oracle=independent(c);assert oracle==expected
 p,seconds=run(['count',*model],name+'-count');assert int(p.stdout)==expected
 domain,n=model[:2];bits=8 if domain=='byte' else 4
 original=bytes((x>>((n-1-i)*bits))&((1<<bits)-1) for i in range(n))
 for mode in ['raw','rank']:
  arc=AREA/'raw'/f'{name}-{mode}.csp';out=AREA/'raw'/f'{name}-{mode}.restored'
  p,elapsed=run(['encode',*model,mode,x,arc,out],name+'-'+mode,ok=expected!=0 or mode=='raw')
  if expected==0 and mode=='rank':assert p.returncode!=0;continue
  assert out.read_bytes()==original
  d=arc.read_bytes();assert d[:4]==b'CSP1' and int.from_bytes(d[-4:],'little')==zlib.crc32(d[4:-4])
  rows.append(dict(case=name,mode=mode,count=expected,oracle_count=oracle,complete_bytes=len(d),original_bytes=len(original),archive_sha256=hashlib.sha256(d).hexdigest(),restored_sha256=hashlib.sha256(original).hexdigest(),encode_and_fresh_decode_seconds=elapsed,settings=model,object=x))
bad=[]
sample=AREA/'raw/byte-intersection-rank.csp';d=sample.read_bytes()
for name,b in [('truncated',d[:-1]),('crc',d[:-1]+bytes([d[-1]^1])),('trailing',d+b'\0')]:
 a=AREA/'raw'/f'bad-{name}.csp';o=AREA/'raw'/f'bad-{name}.out';a.write_bytes(b)
 p,_=run(['decode',a,o],f'bad-{name}',False);assert p.returncode!=0 and not o.exists()
 bad.append(dict(case=name,exit=p.returncode))
(AREA/'results.json').write_text(json.dumps(dict(rows=rows,malformed=bad,scope='one observation; exact tiny objects; encoding includes fresh decoder; no throughput claims'),indent=2)+'\n')
print(json.dumps(dict(archives=len(rows),oracle_cases=len(cases),malformed=len(bad))))
