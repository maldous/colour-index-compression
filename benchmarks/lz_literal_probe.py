#!/usr/bin/env python3
"""Probe PPM/fixed-mix coding of generic LZ literal residuals."""

from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.fixedmix import encode_fixed_mix
from cix.lz import (
    _encode_literals,
    _suffix_lpf_state,
    parse_lz_suffix,
)
from cix.multinomial import ContextModel
from cix.ppm import encode_ppm


URLS = {
    "alice32k": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
}


def sources() -> dict[str, bytes]:
    rng = random.Random(20260927)
    n = 16384
    out = {
        "random": bytes(rng.randrange(256) for _ in range(n)),
        "biased": bytes(0 if rng.random() < 0.9 else rng.randrange(1, 16) for _ in range(n)),
        "repeat": (b"universal-colour-index|" * 1000)[:n],
        "structured": b"".join(
            f"{i:06d}|item-{i%137:03d}|group-{i%17:02d}|{(i*31)%10007:05d}|{i%2}\n".encode()
            for i in range(1000)
        )[:n],
    }
    work = Path("benchmark-work/lz-literal")
    work.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        p = work / name
        if not p.exists():
            urllib.request.urlretrieve(url, p)
        data = p.read_bytes()
        out[name] = data[:32768] if name == "alice32k" else data
    return out


def main() -> None:
    models = (
        ContextModel(1, 8),
        ContextModel(2, 8),
        ContextModel(2, 10),
        ContextModel(4, 10),
    )

    for name, data in sources().items():
        state = _suffix_lpf_state(data, b"", 1 << 17)
        if state is None:
            print(name, "NO_SUFFIX_STATE", flush=True)
            continue
        parse = parse_lz_suffix(
            data,
            state=state,
            min_match=4,
            max_match=65535,
            window=1 << 17,
            lazy=True,
        )
        current, current_name = _encode_literals(
            parse, data, b"", models
        )
        candidates = {
            "current": len(current),
            **{
                f"ppm{o}": 1 + len(encode_ppm(parse.literals, max_order=o))
                for o in (1, 2, 3, 4)
            },
        }
        if len(parse.literals) <= 16384:
            candidates["fixedmix"] = 1 + len(
                encode_fixed_mix(parse.literals)
            )
        print(
            name,
            "source", len(data),
            "literals", len(parse.literals),
            "current_model", current_name,
            candidates,
            "winner", min((v, k) for k, v in candidates.items()),
            flush=True,
        )


if __name__ == "__main__":
    main()
