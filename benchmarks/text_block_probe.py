#!/usr/bin/env python3
import argparse,bz2,gzip,json,lzma,tarfile,time,urllib.request
from pathlib import Path
from cix.multinomial import ContextModel,StreamConfig,StreamEncoder,decompress

URL="https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED={"alice29.txt":152089,"asyoulik.txt":125179,"cp.html":24603,"fields.c":11150,
"lcet10.txt":426754,"plrabn12.txt":481861,"xargs.1":4227}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("member",choices=EXPECTED); ap.add_argument("max_block",type=int)
    a=ap.parse_args()
    work=Path("benchmark-work");work.mkdir(exist_ok=True);arc=work/"cantrbry.tar.gz";urllib.request.urlretrieve(URL,arc)
    dest=work/"textprobe"
    with tarfile.open(arc,"r:gz") as tf:tf.extractall(dest,filter="data")
    p=next(p for p in dest.rglob(a.member) if p.is_file()); data=p.read_bytes()
    cfg=StreamConfig(
      min_block=min(8192,a.max_block//4),max_block=a.max_block,probe_stride=2048,
      split_gain_bits=128.0,chunk_mode="fixed",history_bytes=1<<20,lz_window_bytes=1<<20,lz_chain=32,
      context_beam=2,transform_beam=2,adaptive_beam=1,
      enable_numeric=False,enable_bitplanes=False,enable_chains=False,enable_sparse=False,
      enable_runs=False,enable_adaptive=False,enable_persistent_adaptive=False,enable_tokens=False,
      context_models=(ContextModel(1,8),ContextModel(2,10),ContextModel(4,10)),
    )
    t=time.perf_counter();enc=StreamEncoder(cfg);blob=enc.feed(data)+enc.finish();seconds=time.perf_counter()-t
    assert decompress(blob)==data
    result={"member":a.member,"max_block":a.max_block,"original":len(data),"cix":len(blob),
      "xz":len(lzma.compress(data,preset=9)),"bzip2":len(bz2.compress(data,9)),
      "seconds":seconds,"models":list(enc.block_descriptions)}
    name=a.member.replace(".","_");Path(f"textprobe-{name}-{a.max_block}.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
