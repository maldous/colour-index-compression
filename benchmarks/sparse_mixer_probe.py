#!/usr/bin/env python3
import random,urllib.request
from pathlib import Path
from cix.mixerv2 import encode,decode
from cix.ppm import encode_ppm
from cix.mixer import encode_mixer

def srcs():
 r=random.Random(20260927);n=8192
 structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(500))[:n]
 repeat=(b"universal-sparse-context-sequence|"*500)[:n]
 periodic=bytes(((i%37)*7)&255 for i in range(n))
 random_data=bytes(r.randrange(256) for _ in range(n))
 biased=bytes(0 if r.random()<.9 else r.randrange(1,16) for _ in range(n))
 p=Path("benchmark-work/mix2/alice29.txt");p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",p)
 return {"random":random_data,"biased":biased,"periodic":periodic,"repeat":repeat,"structured":structured,"alice32k":p.read_bytes()[:32768]}

def main():
 for name,data in srcs().items():
  p=encode(data);assert decode(p,len(data))==data
  row={"mix2":len(p),"ppm4":len(encode_ppm(data,max_order=4)),"mix1":len(encode_mixer(data,orders=(0,1,2,4)))}
  print(name,len(data),row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
