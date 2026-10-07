from pathlib import Path
import json,hashlib
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/evidence';WORK=ROOT/'benchmark-work/segmentation-reference'
def draw(seed,n,alpha=256):
 state=seed;out=[]
 for _ in range(n):
  state^=state>>12;state^=(state<<25)&((1<<64)-1);state^=state>>27;state&=(1<<64)-1;out.append((state*2685821657736338717&((1<<64)-1))%alpha)
 return bytes(out)
if __name__=='__main__':
 (WORK/'inputs').mkdir(parents=True,exist_ok=True);rows=[]
 def add(name,data,split,params):
  p=WORK/'inputs'/(name+'.bin');p.write_bytes(data);rows.append(dict(name=name,split=split,input=str(p),input_bytes=len(data),input_sha256=hashlib.sha256(data).hexdigest(),parameters=params))
 for name,data in [('empty',b''),('tiny-one',b'X'),('tiny-run',b'X'*12),('tiny-changing',bytes([0,0,0,1,1,1,2,2,2,3,3,3])),('tiny-random',draw(801,12))]:add(name,data,'oracle',dict(kind='tiny'))
 for name,data in [('small-homogeneous',b'X'*64),('small-change',draw(803,21,2)+draw(805,43)),('small-alternating',bytes([0,1])*32),('small-random',draw(807,64))]:add(name,data,'oracle',dict(kind='allcuts64'))
 for split,seed,offset in [('development',811,0),('held-out',911,13)]:
  a=draw(seed,379+offset,2);b=draw(seed+1,641-offset);c=draw(seed+2,431,2)
  cases={'homogeneous':b'k'*(1536+offset),'abrupt':a+b+c,'gradual':bytes(draw(seed+i,1,2+((i//16)%64))[0]for i in range(1536+offset)),'short-alternation':b''.join(draw(seed+i,7,2 if i%2==0 else 256)for i in range(200)),'A-B-A':a+b+a,'long-dependency':draw(seed,512)+draw(seed+1,513+offset)+draw(seed,512),'interleaved-noise':bytes(v for i,x in enumerate(draw(seed,512))for v in [x,(x+1)&255,0 if i%17 else x]),'high-entropy':draw(seed,1536+offset)}
  for name,data in cases.items():add(split+'-'+name,data,split,dict(seed=seed,offset=offset,kind=name,diagnostic_boundaries=[len(a),len(a)+len(b)]if name in['abrupt','A-B-A']else None))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('froze',len(rows),'inputs',flush=True)
