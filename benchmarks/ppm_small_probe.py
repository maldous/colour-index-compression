#!/usr/bin/env python3
import urllib.request
from pathlib import Path
from cix.ppm import encode_ppm,decode_ppm
FILES={
"cp.html":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
"fields.c":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
"grammar.lsp":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
"xargs.1":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}
def main():
 root=Path("benchmark-work/ppm-small");root.mkdir(parents=True,exist_ok=True)
 for name,url in FILES.items():
  p=root/name
  if not p.exists():urllib.request.urlretrieve(url,p)
  data=p.read_bytes();row={}
  for order in range(0,9):
   blob=encode_ppm(data,max_order=order)
   assert decode_ppm(blob,source_length=len(data))==data
   row[order]=len(blob)
  print(name,len(data),row,"winner",min((v,k) for k,v in row.items()),flush=True)
if __name__=="__main__":main()
