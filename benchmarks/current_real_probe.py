#!/usr/bin/env python3
from __future__ import annotations
import bz2,gzip,lzma,time,urllib.request
from pathlib import Path
try:
 import brotli
except ImportError: brotli=None
try:
 import zstandard as zstd
except ImportError: zstd=None
from cix.cli import config_for_level
from cix.multinomial import StreamEncoder,decompress

FILES={
"alice29.txt":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
"cp.html":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
"fields.c":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
"grammar.lsp":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
"xargs.1":"https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}
def pct(n,d):return 100*n/d
def main():
 root=Path("benchmark-work/current-real");root.mkdir(parents=True,exist_ok=True)
 for name,url in FILES.items():
  p=root/name
  if not p.exists():urllib.request.urlretrieve(url,p)
  data=p.read_bytes();cfg=config_for_level(6)
  start=time.perf_counter();enc=StreamEncoder(cfg);blob=enc.feed(data)+enc.finish();secs=time.perf_counter()-start
  assert decompress(blob)==data
  refs={
   "gzip":len(gzip.compress(data,9)),
   "bzip2":len(bz2.compress(data,9)),
   "xz":len(lzma.compress(data,preset=9)),
   "brotli":len(brotli.compress(data,quality=11)) if brotli else None,
   "zstd":len(zstd.ZstdCompressor(level=19).compress(data)) if zstd else None,
  }
  print(name,len(data),"CIX",len(blob),f"{pct(len(blob),len(data)):.3f}%","refs",refs,f"{secs:.2f}s","models",enc.block_descriptions,flush=True)
if __name__=="__main__":main()
