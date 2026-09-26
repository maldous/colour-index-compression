#!/usr/bin/env python3
"""Probe previous-distance delta coding for generic LZ match distances."""

from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.lz import _suffix_lpf_state, parse_lz_suffix
from cix.multinomial import vencode
from cix.substreams import encode_distances_best, encode_uints


URLS = {
    "alice32k": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
}


def zigzag(value: int) -> int:
    return value * 2 if value >= 0 else -value * 2 - 1


def delta_blob(distances: list[int]) -> bytes:
    if not distances:
        return b""
    deltas = [
        zigzag(current - previous)
        for previous, current in zip(distances, distances[1:])
    ]
    return vencode(distances[0]) + encode_uints(deltas)


def delta2_blob(distances: list[int]) -> bytes:
    if not distances:
        return b""
    if len(distances) == 1:
        return vencode(distances[0])
    first_delta = distances[1] - distances[0]
    previous_delta = first_delta
    residuals = []
    for previous, current in zip(distances[1:], distances[2:]):
        delta = current - previous
        residuals.append(zigzag(delta - previous_delta))
        previous_delta = delta
    return (
        vencode(distances[0])
        + vencode(zigzag(first_delta))
        + encode_uints(residuals)
    )


def sources() -> dict[str, bytes]:
    rng = random.Random(20260927)
    n = 32768
    out = {
        "random": bytes(rng.randrange(256) for _ in range(n)),
        "periodic": bytes((i % 97) for i in range(n)),
        "repeat": (b"universal-colour-index|" * 2000)[:n],
        "structured": b"".join(
            f"{i:06d}|item-{i%137:03d}|group-{i%17:02d}|{(i*31)%10007:05d}|{i%2}\n".encode()
            for i in range(2000)
        )[:n],
    }
    work = Path("benchmark-work/lz-distance")
    work.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        p = work / name
        if not p.exists():
            urllib.request.urlretrieve(url, p)
        data = p.read_bytes()
        out[name] = data[:32768] if name == "alice32k" else data
    return out


def main() -> None:
    for name, data in sources().items():
        state = _suffix_lpf_state(data, b"", 1 << 17)
        if state is None:
            continue
        parse = parse_lz_suffix(
            data,
            state=state,
            min_match=4,
            max_match=65535,
            window=1 << 17,
            lazy=True,
        )
        distances = parse.distances
        current = encode_distances_best(distances)
        candidates = {
            "current": len(current),
            "delta1": len(delta_blob(distances)),
            "delta2": len(delta2_blob(distances)),
        }
        print(
            name,
            "matches", len(distances),
            "range", (
                (min(distances), max(distances)) if distances else None
            ),
            candidates,
            "winner", min((v, k) for k, v in candidates.items()),
            flush=True,
        )


if __name__ == "__main__":
    main()
