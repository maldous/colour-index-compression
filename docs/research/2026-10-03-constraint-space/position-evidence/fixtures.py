import json,hashlib
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/position-evidence';WORK=ROOT/'benchmark-work/record-positions';OLD=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 (WORK/'inputs').mkdir(parents=True,exist_ok=True);rows=[]
 for row in json.loads((OLD/'results.json').read_text()):
  f=row['fixture'];p=Path(f['input']);assert sha(p)==f['input_sha256'];rows.append(dict(name=f['name'],split=f['split'],input=str(p),input_bytes=f['input_bytes'],input_sha256=sha(p),previous=row))
 for oldname,b,seed,split in [('weak-six',6,751,'development'),('held-out-b8-e16',8,753,'held-out')]:
  f=next(x for x in rows if x['name']==oldname);data=Path(f['input']).read_bytes();records=[data[i:i+b]for i in range(0,len(data),b)];state=seed
  for i in range(len(records)-1,0,-1):
   state^=state>>12;state^=(state<<25)&((1<<64)-1);state^=state>>27;state&=(1<<64)-1;j=(state*2685821657736338717&((1<<64)-1))%(i+1);records[i],records[j]=records[j],records[i]
  p=WORK/'inputs'/(split+'-irregular.bin');p.write_bytes(b''.join(records));rows.append(dict(name=split+'-irregular',split=split,input=str(p),input_bytes=len(data),input_sha256=sha(p),generator=dict(source=f['input_sha256'],record_bytes=b,permutation_seed=seed),diagnostic='same record multiset; irregular order; no encoder labels'))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('froze',len(rows),'inputs',flush=True)
