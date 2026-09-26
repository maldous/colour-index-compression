#!/usr/bin/env python3
import argparse,json,lzma,tarfile,time,urllib.request
from pathlib import Path
from cix.multinomial import StreamConfig,StreamEncoder,decompress

URL="https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED={"ptt5":513216,"sum":38240}

def cfg(member):
    if member=="ptt5":
        return StreamConfig(
          min_block=16384,max_block=65536,probe_stride=4096,chunk_mode="fixed",
          history_bytes=1<<20,lz_window_bytes=1<<20,context_models=(),
          enable_lz=False,enable_bwt=False,enable_transforms=False,enable_numeric=False,
          enable_bitplanes=False,enable_chains=False,enable_adaptive=False,
          enable_persistent_adaptive=False,enable_tokens=False,enable_raster=True,
          enable_dedup=False,enable_sparse=True,enable_runs=True)
    return StreamConfig(
      min_block=38240,max_block=38240,probe_stride=38240,chunk_mode="fixed",
      history_bytes=1<<20,lz_window_bytes=1<<20,context_models=(),lz_chain=32,
      enable_lz=True,enable_bwt=False,enable_transforms=True,transform_beam=35,
      enable_numeric=True,enable_bitplanes=False,enable_chains=True,chain_beam=14,
      enable_adaptive=False,enable_persistent_adaptive=False,enable_tokens=False,
      enable_raster=False,enable_dedup=False,enable_sparse=False,enable_runs=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("member",choices=EXPECTED);a=ap.parse_args()
    w=Path("benchmark-work");w.mkdir(exist_ok=True);arc=w/"cantrbry.tar.gz";urllib.request.urlretrieve(URL,arc)
    d=w/"specialized"
    with tarfile.open(arc,"r:gz") as tf:tf.extractall(d,filter="data")
    data=next(p for p in d.rglob(a.member) if p.is_file()).read_bytes()
    t=time.perf_counter();e=StreamEncoder(cfg(a.member));blob=e.feed(data)+e.finish();seconds=time.perf_counter()-t
    assert decompress(blob)==data
    xz=len(lzma.compress(data,preset=9))
    result={"member":a.member,"original":len(data),"cix":len(blob),"xz":xz,
      "seconds":seconds,"models":list(e.block_descriptions)}
    Path(f"specialized-{a.member}.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
