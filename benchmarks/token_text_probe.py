#!/usr/bin/env python3
import argparse,bz2,json,lzma,tarfile,time,urllib.request
from pathlib import Path
from cix.multinomial import ContextModel,StreamConfig,StreamEncoder,decompress

URL="https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED={"alice29.txt":152089,"asyoulik.txt":125179,"cp.html":24603,"fields.c":11150,
"lcet10.txt":426754,"plrabn12.txt":481861,"xargs.1":4227}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("member",choices=EXPECTED);a=ap.parse_args()
    w=Path("benchmark-work");w.mkdir(exist_ok=True);arc=w/"cantrbry.tar.gz";urllib.request.urlretrieve(URL,arc)
    d=w/"tokenprobe"
    with tarfile.open(arc,"r:gz") as tf:tf.extractall(d,filter="data")
    data=next(p for p in d.rglob(a.member) if p.is_file()).read_bytes()
    cfg=StreamConfig(
      min_block=16384,max_block=65536,probe_stride=4096,chunk_mode="fixed",
      history_bytes=1<<20,lz_window_bytes=1<<20,lz_chain=32,
      context_beam=2,enable_bwt=True,enable_lz=True,enable_tokens=True,
      enable_transforms=False,enable_numeric=False,enable_bitplanes=False,enable_chains=False,
      enable_sparse=False,enable_runs=False,enable_adaptive=False,enable_persistent_adaptive=False,
      enable_dedup=False,context_models=(ContextModel(1,8),ContextModel(2,10),ContextModel(4,10)))
    t=time.perf_counter();e=StreamEncoder(cfg);blob=e.feed(data)+e.finish();seconds=time.perf_counter()-t
    assert decompress(blob)==data
    result={"member":a.member,"original":len(data),"cix":len(blob),
      "xz":len(lzma.compress(data,preset=9)),"bzip2":len(bz2.compress(data,9)),
      "seconds":seconds,"models":list(e.block_descriptions)}
    Path("tokenprobe-"+a.member.replace(".","_")+".json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
