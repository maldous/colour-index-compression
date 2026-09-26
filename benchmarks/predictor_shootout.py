#!/usr/bin/env python3
from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.adaptive import decode_adaptive, encode_adaptive
from cix.expertmix import decode_expert_mix, encode_expert_mix
from cix.mixer import decode_mixer, encode_mixer
from cix.ppm import decode_ppm, encode_ppm


def sources():
    rng = random.Random(27092026)
    n = 8192
    random_data = bytes(rng.randrange(256) for _ in range(n))
    biased = bytes(0 if rng.random() < .9 else rng.randrange(1,16) for _ in range(n))
    periodic = bytes((i % 37) ^ (1 if rng.random() < .01 else 0) for i in range(n))
    repeat = (b"generic-context-mixing-sequence|" * 400)[:n]
    structured = b"".join(
        f"{i:06d}|{i%137:03d}|{i%17:02d}|{(i*31)%10007:05d}\n".encode()
        for i in range(500)
    )[:n]

    path=Path("benchmark-work/predictor/alice29.txt")
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
            path,
        )
    alice=path.read_bytes()[:32768]

    return {
        "random":random_data,
        "biased":biased,
        "periodic":periodic,
        "repeat":repeat,
        "structured":structured,
        "alice32k":alice,
    }


def main():
    orders=(0,1,2,4)
    for name,data in sources().items():
        results={}

        p=encode_adaptive(data,order=2,bucket_bits=10)
        assert decode_adaptive(p,source_length=len(data))==data
        results["adaptive-o2"]=len(p)

        p=encode_ppm(data,max_order=4)
        assert decode_ppm(p,source_length=len(data))==data
        results["ppm-o4"]=len(p)

        p=encode_expert_mix(data,orders=orders)
        assert decode_expert_mix(p,source_length=len(data))==data
        results["byte-expert"]=len(p)

        p=encode_mixer(data,orders=orders)
        assert decode_mixer(p,source_length=len(data))==data
        results["bit-mixer"]=len(p)

        ranked=sorted((size,model) for model,size in results.items())
        print(name,len(data),results,"winner",ranked[0],flush=True)


if __name__=="__main__":
    main()
