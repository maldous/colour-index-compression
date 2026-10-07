from pathlib import Path
import json,hashlib
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/model-evidence';WORK=ROOT/'benchmark-work/model-descriptions';OLD=ROOT/'docs/research/2026-10-03-constraint-space/record-evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def holds(v,atom):
 op,mask,p=atom;q=(v&mask).bit_count()
 if op==0:return q==p
 if op==1:return q<=p
 if op==2:return q%2==p
 low=(mask&-mask).bit_length()-1;high=mask.bit_length()-1;return ((v>>low)^(v>>high))&1==p
NEW=[('upper-parity-dev','development',8,[[1,255,4],[2,255,1]],1536,321,(23,217)),('upper-parity-held','held-out',10,[[1,1023,5],[2,1023,0]],1280,323,(11,243)),('three-way-dev','development',8,[[1,255,4],[2,255,1],[3,255,0]],1536,325,(27,227)),('three-way-held','held-out',10,[[1,1023,5],[2,1023,0],[3,1023,1]],1280,327,(13,231))]
def source(b,atoms,r,seed,alphabet):
 table=[v for v in range(1<<b)if all(holds(v,a)for a in atoms)];state=seed;out=bytearray()
 def draw():
  nonlocal state
  state^=state>>12;state^=(state<<25)&((1<<64)-1);state^=state>>27;state&=(1<<64)-1
  return state*2685821657736338717&((1<<64)-1)
 for _ in range(r):
  while True:
   v=draw()
   if v>=(1<<64)%len(table):break
  word=table[v%len(table)];out.extend(alphabet[(word>>(b-1-j))&1]for j in range(b))
 return bytes(out),table
if __name__=='__main__':
 rows=[]
 for old in json.loads((OLD/'results.json').read_text()):
  if old['modes'].get('ec',{}).get('status')!='verified':continue
  f=old['fixture'];inp=Path(f['path']);assert sha(inp)==f['sha256'];b=old['modes']['ec']['block_width'];mask=old['modes']['ec']['equality_mask'];h=old['modes']['ec']['count']
  atoms=[[0,(1<<b)-1,h]]+[[3,(1<<(b-1-j))|(1<<(b-2-j)),0]for j in range(b-1)if mask>>j&1]
  rows.append(dict(name=f['name'],split=f['split'],b=b,atoms=atoms,input=str(inp),input_bytes=f['bytes'],input_sha256=f['sha256'],source='existing qualified ERC1 input',existing_baseline=old['L0'],existing_references=old['references']))
 for name,split,b,atoms,r,seed,alphabet in NEW:
  data,table=source(b,atoms,r,seed,alphabet);inp=WORK/'inputs'/f'{name}.bin';inp.write_bytes(data)
  rows.append(dict(name=name,split=split,b=b,atoms=atoms,input=str(inp),input_bytes=len(data),input_sha256=sha(inp),source='frozen synthetic prescribed model',generator_parameters=dict(records=r,seed=seed,alphabet=alphabet)))
 for name,data in [('empty',b''),('mono',bytes([31])*4096),('absent',bytes(range(256))*16)]:
  inp=WORK/'inputs'/f'{name}.bin';inp.write_bytes(data);rows.append(dict(name=name,split='control',b=8,atoms=[],input=str(inp),input_bytes=len(data),input_sha256=sha(inp),source='bounded fallback control'))
 for row in rows:
  b=row['b'];atoms=row['atoms'];table=[v for v in range(1<<b)if all(holds(v,a)for a in atoms)];model=WORK/'inputs'/(row['name']+'.model');model.write_text(str(b)+'\n'+''.join(' '.join(map(str,a))+'\n'for a in atoms));row.update(model=str(model),model_sha256=sha(model),exact_members=table,exact_cardinality=len(table))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('froze',len(rows),'model/input identities before encoding',flush=True)
