from pathlib import Path
import json,hashlib
ROOT=Path('/home/user/src/colour-index-compression')
WORK=ROOT/'benchmark-work/equality-records'
# Frozen before development and held-out execution. No empirical tuning.
CASES=[
 ('dev-six','development',6,3,1,2048,101,(0,255),'strong'),
 ('dev-eight','development',8,4,1,1536,103,(31,211),'strong'),
 ('dev-four','development',4,2,1,3072,107,(7,193),'strong'),
 ('held-six','held-out',6,3,1,1792,211,(17,230),'strong'),
 ('held-ten','held-out',10,5,1,1280,223,(41,199),'strong'),
 ('weak-six','control',6,3,1,2048,227,(0,255),'weak'),
 ('absent','control',6,3,1,2048,229,(0,255),'absent'),
 ('empty','control',6,3,1,0,233,(0,255),'empty'),
]
def words(width,count,mask):
 return [x for x in range(1<<width) if x.bit_count()==count and all(not(mask>>j&1)or ((x>>(width-1-j))&1)==((x>>(width-2-j))&1)for j in range(width-1))]
def generate(case):
 name,split,b,h,mask,records,seed,alphabet,kind=case
 # Xorshift64* with rejection sampling for unbiased table indices.
 state=seed
 def draw():
  nonlocal state
  state^=state>>12;state^=(state<<25)&((1<<64)-1);state^=state>>27;state&=(1<<64)-1
  return (state*2685821657736338717)&((1<<64)-1)
 table=words(b,h,mask);out=bytearray()
 for i in range(records):
  while True:
   value=draw()
   if value>=((1<<64)%len(table)):break
  word=table[value%len(table)]
  row=bytearray(alphabet[(word>>(b-1-j))&1] for j in range(b))
  if kind=='weak' and i%17==0:row[0]=alphabet[1] if row[0]==alphabet[0] else alphabet[0]
  if kind=='absent':row=bytearray(draw()&255 for _ in range(b))
  out.extend(row)
 return bytes(out)
if __name__=='__main__':
 rows=[]
 for case in CASES:
  d=generate(case);p=WORK/'inputs'/f'{case[0]}.bin';p.write_bytes(d)
  rows.append(dict(name=case[0],split=case[1],parameters=case[2:],bytes=len(d),sha256=hashlib.sha256(d).hexdigest(),path=str(p)))
 (ROOT/'docs/research/2026-10-03-constraint-space/record-evidence/input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('froze8inputhashes before encoding')
