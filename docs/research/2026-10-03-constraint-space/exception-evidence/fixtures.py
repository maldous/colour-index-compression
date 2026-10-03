#!/usr/bin/env python3
"""Frozen binary-record synthetic generator; no parameters passed to encoder."""
import json,hashlib
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';WORK=ROOT/'benchmark-work/record-exceptions';OLD=ROOT/'docs/research/2026-10-03-constraint-space/record-evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(b,seed,e,alphabet):
 table=[v for v in range(1<<b)if v.bit_count()==b//2 and ((v>>(b-1))&1)==((v>>(b-2))&1)];state=seed;words=[]
 for _ in range(1536):
  state^=state>>12;state^=(state<<25)&((1<<64)-1);state^=state>>27;state&=(1<<64)-1
  words.append(table[(state*2685821657736338717&((1<<64)-1))%len(table)])
 positions=[(j*97+13)%1536 for j in range(e)]
 assert len(set(positions))==e
 for p in positions:words[p]^=1<<(b-1)
 data=bytes(alphabet[(v>>(b-1-j))&1]for v in words for j in range(b))
 return data,positions
if __name__=='__main__':
 (WORK/'inputs').mkdir(parents=True,exist_ok=True);rows=[]
 for row in json.loads((OLD/'results.json').read_text()):
  if row['fixture']['name'] not in ['dev-six','weak-six','absent']:continue
  f=row['fixture'];p=Path(f['path']);assert sha(p)==f['sha256'];rows.append(dict(name=f['name'],split=f['split'],input=str(p),input_bytes=f['bytes'],input_sha256=f['sha256'],existing=row))
 for split,b,seed,alphabet in [('development',6,401,(19,231)),('held-out',8,403,(7,247))]:
  for e in [0,1,16]:
   name=f'{split}-b{b}-e{e}';data,positions=source(b,seed,e,alphabet);p=WORK/'inputs'/f'{name}.bin';p.write_bytes(data)
   rows.append(dict(name=name,split=split,input=str(p),input_bytes=len(data),input_sha256=sha(p),generator_parameters=dict(b=b,r=1536,seed=seed,e=e,alphabet=alphabet),generator_positions=positions))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('froze',len(rows),'inputs',flush=True)
