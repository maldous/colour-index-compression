"""Frozen synthetic controls; labels never appear in codec CLI arguments."""
from pathlib import Path
import json,hashlib,random
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/latent-evidence';WORK=ROOT/'benchmark-work/latent-layout'
def draw(seed,n):return random.Random(seed).randbytes(n)
def structured(seed,w,r):
 b=draw(seed,r);noise=draw(seed+1,w*r)
 return bytes(noise[i*w+j]if i%29==0 else((b[i]+7*j)&255)if j<w-1 else 0 for i in range(r)for j in range(w))
def fixtures():
 # Discovery inputs from previous immutable bank remain exposed.
 old=json.loads((AREA.parent/'mask-evidence/results.json').read_text())
 for row in old:
  if row['fixture']['name']in ['fresh-held-mask-width3','fresh-held-mask-width4','fresh-held-mask-width5']:
   f=row['fixture'];yield f['name'],'exposed-attribution',Path(f['input']).read_bytes(),dict(existing=f,existing_controls=row['references'])
 # Held-out specification fixed before generation; geometry labels diagnostics only.
 yield 'alias-3-6','held-out',structured(2501,3,251),dict(seed=2501,width=3,alias=6)
 yield 'shift-prefix','held-out',draw(2510,2)+structured(2511,4,181)+draw(2512,3),dict(seed=2511,prefix=2,width=4,tail=3)
 yield 'partial-width5','held-out',structured(2521,5,147)+draw(2522,3),dict(seed=2521,width=5,tail=3)
 r=draw(2531,128);noise=draw(2532,768)
 yield 'subset-correlations','held-out',bytes((r[i]+j)&255 if j in (0,1)else noise[i*6+j] for i in range(128)for j in range(6)),dict(seed=2531,width=6)
 yield 'changing-correlation','held-out',structured(2541,3,127)+bytes(b^((i%3)*53)for i,b in enumerate(structured(2543,3,127))),dict(seed=2541,changes_at=381)
 q=structured(2551,4,183);q=q[:181]+b'\x93'+q[181:];q=q[:507]+q[508:]
 yield 'alignment-edits','held-out',q,dict(seed=2551,insert_at=181,delete_at=507)
 yield 'mixed-local','held-out',draw(2561,181)+structured(2562,3,127)+draw(2563,193),dict(seed=2562,local_offset=181)
 a=structured(2571,3,95)
 yield 'separated-ABA','held-out',a+draw(2572,193)+a,dict(seed=2571,shared_regions=True)
 vals=draw(2581,251);q=bytes(vals[i]if j==0 else(vals[i-1]if i else 0)for i in range(251)for j in range(3))
 yield 'cross-row-dependencies','held-out',q,dict(seed=2581,width=3)
 yield 'absent-random','held-out',draw(2591,767),dict(seed=2591)
 # Exact tiny candidate-family checks; no generator geometry assigned.
 yield 'tiny-empty','tiny',b'',{}
 for n in range(1,9):yield 'tiny-'+str(n),'tiny',bytes((i*i+3*i+17)%256 for i in range(n)),dict(length=n)
if __name__=='__main__':
 (WORK/'inputs').mkdir(parents=True,exist_ok=True);rows=[]
 for name,split,data,diagnostic in fixtures():
  p=WORK/'inputs'/(name+'.bin');assert not p.exists();p.write_bytes(data)
  rows.append(dict(name=name,split=split,input=str(p),input_bytes=len(data),input_sha256=hashlib.sha256(data).hexdigest(),diagnostic=diagnostic))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('Frozen',len(rows),'synthetic inputs',flush=True)
