#!/usr/bin/env python3
import random,urllib.request
from pathlib import Path
from cix.wavelet import encode_wavelet,decode_wavelet
from cix.multinomial import encode_type_class_known_n
from cix.adaptive import encode_adaptive

def srcs():
 r=random.Random(20260927);n=8192
 random_data=bytes(r.randrange(256) for _ in range(n))
 biased=bytes(0 if r.random()<.9 else r.randrange(1,16) for _ in range(n))
 sparse_alpha=bytes(r.choice((0,1,2,3,250,251)) for _ in range(n))
 structured=b"".join(f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode() for i in range(500))[:n]
 p=Path("benchmark-work/wavelet/alice29.txt");p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():urllib.request.urlretrieve("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",p)
 return {"random":random_data,"biased":biased,"sparse-alpha":sparse_alpha,"structured":structured,"alice16k":p.read_bytes()[:16384]}

def main():
 for name,data in srcs().items():
  w=encode_wavelet(data);assert decode_wavelet(w,len(data))==data
  direct=encode_type_class_known_n(data)
  adaptive=encode_adaptive(data,order=0,bucket_bits=8)
  row={"wavelet":len(w),"direct-typeclass":len(direct),"adaptive-kt":len(adaptive)}
  print(name,len(data),row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
