#!/usr/bin/env python3
"""Compare physical CIX sizes for generic LZ parsing strategies."""

from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.lz import (
    _encode_parse,
    _suffix_lpf_state,
    parse_lz_optimal_suffix,
    parse_lz_suffix,
)
from cix.multinomial import ContextModel


URLS = {
    "alice32k": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
}


def sources() -> dict[str, bytes]:
    rng = random.Random(20260927)
    n = 32768
    out = {
        "biased": bytes(0 if rng.random() < 0.9 else rng.randrange(1, 16) for _ in range(n)),
        "periodic": bytes((i % 97) for i in range(n)),
        "repeat": (b"universal-colour-index|" * 2000)[:n],
        "structured": b"".join(
            f"{i:06d}|item-{i%137:03d}|group-{i%17:02d}|{(i*31)%10007:05d}|{i%2}\n".encode()
            for i in range(2000)
        )[:n],
    }
    work = Path("benchmark-work/lz-parse")
    work.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        p = work / name
        if not p.exists():
            urllib.request.urlretrieve(url, p)
        data = p.read_bytes()
        out[name] = data[:32768] if name == "alice32k" else data
    return out


def encoded_size(parse, data, models, min_match, name):
    blob, description = _encode_parse(
        parse,
        data,
        b"",
        models,
        min_match,
        name,
        allow_fixed_mix=True,
    )
    return len(blob), description


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
            continue
        parses = {}
        for min_match, lazy, label in (
            (4, False, "greedy4"),
            (4, True, "lazy4"),
            (5, True, "lazy5"),
        ):
            parses[label] = (
                parse_lz_suffix(
                    data,
                    state=state,
                    min_match=min_match,
                    max_match=65535,
                    window=1 << 17,
                    lazy=lazy,
                ),
                min_match,
            )
        parses["optimal4"] = (
            parse_lz_optimal_suffix(
                data,
                state=state,
                min_match=4,
                max_match=65535,
                window=1 << 17,
            ),
            4,
        )

        results = {}
        for label, (parse, min_match) in parses.items():
            size, description = encoded_size(
                parse, data, models, min_match, label
            )
            results[label] = {
                "bytes": size,
                "literals": len(parse.literals),
                "matches": len(parse.lengths),
                "description": description,
            }
        winner = min(
            (row["bytes"], label)
            for label, row in results.items()
        )
        print(name, results, "winner", winner, flush=True)


if __name__ == "__main__":
    main()
