"""Immutable-snapshot adapter for the generic pipeline and unchanged controls."""
from __future__ import annotations

import argparse
import bz2
import gzip
import json
import lzma
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=("encode","decode"))
    p.add_argument("source", type=Path); p.add_argument("destination", type=Path)
    p.add_argument("--mode", choices=("pipeline","baseline","gzip","bzip2","xz","brotli"),default="pipeline")
    p.add_argument("--effort",default="balanced"); p.add_argument("--backend",default="hybrid")
    p.add_argument("--force"); p.add_argument("--disable",action="append",default=[])
    p.add_argument("--history",type=int,default=0); p.add_argument("--block",type=int)
    p.add_argument("--offline",action="store_true")
    a=p.parse_args()
    if a.mode == "pipeline":
        from cix.pipeline import encode_file, decode_file
        report = (encode_file(a.source,a.destination,effort=a.effort,backend=a.backend,
                  force=a.force,disable=a.disable,history_bytes=a.history,block_bytes=a.block,
                  offline=a.offline,trace_path=a.destination.parent/"blocks.jsonl")
                  if a.operation == "encode" else decode_file(a.source,a.destination))
        (a.destination.parent/(a.operation+".codec.json")).write_text(json.dumps(report,indent=2)+"\n")
        return
    data=a.source.read_bytes()
    if a.mode == "baseline":
        from cix.cli import config_for_level
        from cix.multinomial import compress,decompress
        result=compress(data,config_for_level(1)) if a.operation == "encode" else decompress(data)
    elif a.mode == "gzip": result=gzip.compress(data,compresslevel=9,mtime=0) if a.operation == "encode" else gzip.decompress(data)
    elif a.mode == "bzip2": result=bz2.compress(data,compresslevel=9) if a.operation == "encode" else bz2.decompress(data)
    elif a.mode == "xz": result=lzma.compress(data,preset=6) if a.operation == "encode" else lzma.decompress(data)
    else:
        import brotli
        result=brotli.compress(data,quality=6) if a.operation == "encode" else brotli.decompress(data)
    a.destination.write_bytes(result)


if __name__ == "__main__": main()
