#!/usr/bin/env python3
"""Coarse physical sweep of larger generic LZ minimum-match lengths."""

from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.lz import _encode_parse, _suffix_lpf_state, parse_lz_suffix
from cix.multinomial import ContextModel


MATCHES = (6, 8, 10, 12, 16, 24)
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
    work = Path("benchmark-work/lz-minmatch-coarse")
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

        parsed = {}
        baseline = {}
        for min_match in MATCHES:
            parse = parse_lz_suffix(
                data,
                state=state,
                min_match=min_match,
                max_match=65535,
                window=1 << 17,
                lazy=True,
            )
            parsed[min_match] = parse
            blob, description = _encode_parse(
                parse, data, b"", models, min_match, f"m{min_match}",
                allow_fixed_mix=False,
            )
            baseline[min_match] = (len(blob), description)

        top = sorted(MATCHES, key=lambda m: baseline[m][0])[:3]
        rows = {}
        for min_match in MATCHES:
            size, description = baseline[min_match]
            if min_match in top:
                blob, mixed_description = _encode_parse(
                    parsed[min_match], data, b"", models, min_match,
                    f"m{min_match}", allow_fixed_mix=True,
                )
                if len(blob) < size:
                    size, description = len(blob), mixed_description
            rows[min_match] = {
                "bytes": size,
                "literals": len(parsed[min_match].literals),
                "matches": len(parsed[min_match].lengths),
                "description": description,
            }

        winner = min((row["bytes"], m) for m, row in rows.items())
        print(name, rows, "winner", winner, flush=True)


if __name__ == "__main__":
    main()
