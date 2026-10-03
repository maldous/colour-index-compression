import json,re,subprocess
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression')
AREA=ROOT/'docs/research/2026-10-03-constraint-space/search-evidence'
BIN=ROOT/'benchmark-work/constraint-space/build/search'
p=subprocess.run([str(BIN)],capture_output=True,text=True)
(AREA/'search.stdout').write_text(p.stdout);(AREA/'search.stderr').write_text(p.stderr)
assert p.returncode==0,p.stderr
reported={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',p.stdout.splitlines()[0])}
pred=[]
def add(fn,bits):pred.append((sum(1<<x for x in range(256) if fn(x)),bits))
for pos in range(8):
 for val in range(2):add(lambda x,p=pos,v=val:(x//(2**p))%2==v,6)
for i in range(8):
 for j in range(i+1,8):
  for val in range(2):add(lambda x,i=i,j=j,v=val:((x//2**i)%2+(x//2**j)%2)%2==v,9)
for k in range(9):add(lambda x,k=k:bin(x).count('1')==k,6)
for t in range(256):add(lambda x,t=t:x<=t,10)
assert len(pred)==337
got=dict(catalog=337,pairs=0,contradictions=0,redundant=0,independent=0,overlap=0,joint_winning=0,individually_losing_joint_winning=0,positive_volume_interactions=0,rank_unrank_checks=0)
width=lambda n:(n-1).bit_length() if n else 0
for i,(a,ba) in enumerate(pred):
 for b,bb in pred[i+1:]:
  got['pairs']+=1;na=a.bit_count();nb=b.bit_count();ni=(a&b).bit_count()
  if ni==0:got['contradictions']+=1;continue
  category='redundant' if ni==na or ni==nb else 'independent' if na*nb==256*ni else 'overlap'
  got[category]+=1;got['rank_unrank_checks']+=ni
  if na*nb>256*ni:got['positive_volume_interactions']+=1
  joint=7+1+3+ba+bb+width(ni);singlea=7+1+1+ba+width(na);singleb=7+1+1+bb+width(nb)
  if joint<16:
   got['joint_winning']+=1
   if singlea>=16 and singleb>=16:got['individually_losing_joint_winning']+=1
assert got==reported,(got,reported)
(AREA/'results.json').write_text(json.dumps({'rust_report':reported,'independent_python_oracle':got,'fresh_process_exit':p.returncode,'physical_archives_emitted':False,'scope':'exact finite pair search; logical prefix costs; not a corpus/compressor benchmark'},indent=2)+'\n')
print(json.dumps(got))
