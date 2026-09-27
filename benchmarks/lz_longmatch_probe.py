#!/usr/bin/env python3
"""Explore sparse-long-match LZ over strong literal models."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from cix.lz import _encode_parse, _suffix_lpf_state, parse_lz_suffix
from cix.multinomial import ContextModel

MATCHES = (16, 24, 32, 48, 64, 96, 128)
URLS = {
    "alice32k": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
}


def sources():
    out = {
        "structured": b"".join(
            f"{i:06d}|item-{i%137:03d}|group-{i%17:02d}|{(i*31)%10007:05d}|{i%2}\n".encode()
            for i in range(2000)
        )[:32768],
    }
    work = Path("benchmark-work/lz-longmatch")
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
        ContextModel(1, 8), ContextModel(2, 8),
        ContextModel(2, 10), ContextModel(4, 10),
    )
    for name, data in sources().items():
        state = _suffix_lpf_state(data, b"", 1 << 17)
        if state is None:
            continue
        parsed = {}
        baseline = {}
        for min_match in MATCHES:
            parse = parse_lz_suffix(
                data, state=state, min_match=min_match,
                max_match=65535, window=1 << 17, lazy=True,
            )
            parsed[min_match] = parse
            blob, desc = _encode_parse(
                parse, data, b"", models, min_match, f"m{min_match}",
                allow_fixed_mix=False,
            )
            baseline[min_match] = (len(blob), desc)

        top = sorted(MATCHES, key=lambda m: baseline[m][0])[:3]
        rows = {}
        for m in MATCHES:
            size, desc = baseline[m]
            if m in top:
                blob, mixed_desc = _encode_parse(
                    parsed[m], data, b"", models, m, f"m{m}",
                    allow_fixed_mix=True,
                )
                if len(blob) < size:
                    size, desc = len(blob), mixed_desc
            rows[m] = {
                "bytes": size,
                "literals": len(parsed[m].literals),
                "matches": len(parsed[m].lengths),
                "description": desc,
            }
        print(
            name, rows,
            "winner", min((row["bytes"], m) for m, row in rows.items()),
            flush=True,
        )


if __name__ == "__main__":
    main()
