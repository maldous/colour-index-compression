#!/usr/bin/env python3
"""Physical sweep of generic LZ minimum-match lengths."""

from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.lz import _encode_parse, _suffix_lpf_state, parse_lz_suffix
from cix.multinomial import ContextModel


URLS = {
    "alice32k": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
}


def sources():
    rng = random.Random(20260927)
    n = 32768
    out = {
        "biased": bytes(0 if rng.random() < 0.9 else rng.randrange(1, 16) for _ in range(n)),
        "structured": b"".join(
            f"{i:06d}|item-{i%137:03d}|group-{i%17:02d}|{(i*31)%10007:05d}|{i%2}\n".encode()
            for i in range(2000)
        )[:n],
    }
    work = Path("benchmark-work/lz-minmatch")
    work.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        p = work / name
        if not p.exists():
            urllib.request.urlretrieve(url, p)
        data = p.read_bytes()
        out[name] = data[:32768] if name == "alice32k" else data
    return out


def main():
    models = (
        ContextModel(1, 8),
        ContextModel(2, 8),
        ContextModel(2, 10),
        ContextModel(4, 10),
    )
    for name, data in sources().items():
        state = _suffix_lpf_state(data, b"", 1 << 17)
        if state is None:
            continue
        rows = {}
        for min_match in range(4, 9):
            parse = parse_lz_suffix(
                data,
                state=state,
                min_match=min_match,
                max_match=65535,
                window=1 << 17,
                lazy=True,
            )
            blob, description = _encode_parse(
                parse,
                data,
                b"",
                models,
                min_match,
                f"m{min_match}",
                allow_fixed_mix=True,
            )
            rows[min_match] = {
                "bytes": len(blob),
                "literals": len(parse.literals),
                "matches": len(parse.lengths),
                "description": description,
            }
        winner = min((row["bytes"], m) for m, row in rows.items())
        print(name, rows, "winner", winner, flush=True)


if __name__ == "__main__":
    main()
