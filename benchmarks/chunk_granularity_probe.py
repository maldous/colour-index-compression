#!/usr/bin/env python3
from __future__ import annotations
import time
import urllib.request
from dataclasses import replace
from pathlib import Path
from cix.cli import config_for_level
from cix.multinomial import StreamEncoder, decompress

FILES = {
    "alice64k": ("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt", 65536),
    "cp": ("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html", None),
    "fields": ("https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c", None),
}

def encode(data: bytes, cfg):
    t=time.perf_counter()
    enc=StreamEncoder(cfg)
    blob=enc.feed(data)+enc.finish()
    assert decompress(blob)==data
    return len(blob), time.perf_counter()-t, enc.block_descriptions

def main():
    root=Path("benchmark-work/chunk-granularity")
    root.mkdir(parents=True, exist_ok=True)
    base=config_for_level(6)
    variants={
        "m2k-g96":base,
        "m4k-g96":replace(base,min_block=4096),
        "m2k-g64":replace(base,split_gain_bits=64.0),
        "m4k-g64":replace(base,min_block=4096,split_gain_bits=64.0),
    }
    for name,(url,limit) in FILES.items():
        p=root/name
        if not p.exists():
            urllib.request.urlretrieve(url,p)
        data=p.read_bytes()
        if limit is not None:
            data=data[:limit]
        out={}
        for label,cfg in variants.items():
            size,secs,models=encode(data,cfg)
            out[label]={"bytes":size,"seconds":round(secs,3),"blocks":len(models),"models":models}
        print(name,len(data),out,flush=True)

if __name__=="__main__":
    main()
