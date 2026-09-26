#!/usr/bin/env python3
import argparse, bz2, gzip, json, lzma, tarfile, time, urllib.request
from pathlib import Path
from cix.multinomial import ContextModel, StreamConfig, StreamEncoder, decompress

URL="https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED={
"alice29.txt":152089,"asyoulik.txt":125179,"cp.html":24603,"fields.c":11150,
"grammar.lsp":3721,"kennedy.xls":1029744,"lcet10.txt":426754,
"plrabn12.txt":481861,"ptt5":513216,"sum":38240,"xargs.1":4227,
}

def config():
    return StreamConfig(
        min_block=4096,
        max_block=16384,
        probe_stride=1024,
        split_gain_bits=96.0,
        history_bytes=1<<20,
        lz_window_bytes=1<<20,
        lz_chain=32,
        context_beam=3,
        transform_beam=4,
        adaptive_beam=2,
        enable_chains=False,
        context_models=(
            ContextModel(1,8),ContextModel(2,8),ContextModel(2,10),
            ContextModel(4,10),ContextModel(6,12),
        ),
    )

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("member", choices=EXPECTED)
    args=ap.parse_args()
    work=Path("benchmark-work"); work.mkdir(exist_ok=True)
    arc=work/"cantrbry.tar.gz"; urllib.request.urlretrieve(URL,arc)
    dest=work/"member"
    with tarfile.open(arc,"r:gz") as tf: tf.extractall(dest,filter="data")
    matches=[p for p in dest.rglob(args.member) if p.is_file()]
    if not matches: raise RuntimeError(f"missing {args.member}")
    data=matches[0].read_bytes()
    if len(data)!=EXPECTED[args.member]: raise RuntimeError("size mismatch")

    started=time.perf_counter()
    enc=StreamEncoder(config())
    blob=enc.feed(data)+enc.finish()
    seconds=time.perf_counter()-started
    if decompress(blob)!=data: raise RuntimeError("round-trip mismatch")

    result={
        "member":args.member,"original":len(data),"cix":len(blob),
        "gzip":len(gzip.compress(data,9)),
        "bzip2":len(bz2.compress(data,9)),
        "xz":len(lzma.compress(data,preset=9)),
        "seconds":seconds,
        "models":list(enc.block_descriptions),
    }
    safe=args.member.replace(".","_")
    Path(f"member-{safe}.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
