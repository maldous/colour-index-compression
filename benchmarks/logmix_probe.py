#!/usr/bin/env python3
import random,urllib.request
from pathlib import Path
from cix.logmix import encode_logmix,decode_logmix,ETAS
from cix.ppm import encode_ppm

def srcs():
 r=random.Random(20260927);n=8192
 random_data=bytes(r.randrange(256) for _ in range(n))
 biased=bytes(0 if r.random()<.9 else r.randrange(1,16) for _ in range(n))
 periodic=bytes(((i%37)*7)&255 for i in range(n))
 repeat=(b"generic-logistic-context-sequence|"*500)[:n]
 structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(500))[:n]
 p=Path("benchmark-work/logmix/alice29.txt");p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",p)
 return {"random":random_data,"biased":biased,"periodic":periodic,"repeat":repeat,"structured":structured,"alice16k":p.read_bytes()[:16384]}

def main():
 for name,data in srcs().items():
  row={"ppm4":len(encode_ppm(data,max_order=4))}
  for i,eta in enumerate(ETAS):
   p=encode_logmix(data,eta_id=i);assert decode_logmix(p,len(data))==data
   row[f"logmix-{eta}"]=len(p)
  print(name,len(data),row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
