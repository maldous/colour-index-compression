#!/usr/bin/env python3
"""Generic PPM history-window tournament.

Tests whether exact per-block selection among shorter causal history suffixes can
beat the incumbent deterministic warm-history horizon. The candidate decision
is based only on physical encoded bytes and is fully reversible because the
decoder is given the same causal suffix.
"""
from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.ppm import encode_ppm, decode_ppm

BLOCK = 8192
WINDOWS = (0, 4096, 8192, 16384, -1)


def _synthetic_sources() -> dict[str, bytes]:
    n = 32768
    rng = random.Random(20260928)

    stationary = bytearray((b"causal-stationary-pattern|" * 2000)[:n])
    for i in range(n):
        if rng.random() < 0.025:
            stationary[i] ^= 1 << rng.randrange(8)

    regime = bytearray()
    left = (b"alpha-beta-gamma-delta|" * 800)[: n // 2]
    right = (b"one-two-three-four-five|" * 800)[: n - len(left)]
    regime.extend(left)
    regime.extend(right)
    for i in range(n):
        if rng.random() < 0.02:
            regime[i] ^= 1 << rng.randrange(8)

    drift = bytearray()
    x = 0
    for i in range(n):
        if i and i % BLOCK == 0:
            x = (x + 61) & 255
        if rng.random() < 0.08:
            x = (x + rng.choice((-3, -1, 1, 3))) & 255
        drift.append(x)

    return {
        "stationary": bytes(stationary),
        "regime-switch": bytes(regime),
        "drift": bytes(drift),
    }


def _real_sources() -> dict[str, bytes]:
    root = Path("benchmark-work/ppm-history-window")
    root.mkdir(parents=True, exist_ok=True)
    urls = {
        "alice64k": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
        "cp.html": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
    }
    out = {}
    for name, url in urls.items():
        path = root / name.replace("/", "_")
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        data = path.read_bytes()
        out[name] = data[:65536] if name == "alice64k" else data
    return out


def _suffix(prefix: bytes, window: int) -> bytes:
    if window < 0:
        return prefix
    if window == 0:
        return b""
    return prefix[-window:]


def probe(name: str, data: bytes) -> tuple[int, int]:
    incumbent_total = 0
    portfolio_total = 0
    wins = 0
    prefix = b""

    for index, start in enumerate(range(0, len(data), BLOCK)):
        block = data[start : start + BLOCK]
        blobs = {}
        for window in WINDOWS:
            hist = _suffix(prefix, window)
            blob = encode_ppm(block, max_order=4, prefix_history=hist)
            assert decode_ppm(
                blob,
                source_length=len(block),
                prefix_history=hist,
            ) == block
            blobs[window] = len(blob)

        incumbent = blobs[-1]
        winner = min(blobs, key=lambda w: (blobs[w], WINDOWS.index(w)))
        best = blobs[winner]
        incumbent_total += incumbent
        portfolio_total += best
        wins += best < incumbent
        print(
            name,
            "block", index,
            "incumbent", incumbent,
            "winner", winner,
            "best", best,
            "delta", best - incumbent,
            "all", blobs,
            flush=True,
        )
        prefix += block
        if len(prefix) > 65536:
            prefix = prefix[-65536:]

    saved = incumbent_total - portfolio_total
    pct = 100.0 * saved / incumbent_total if incumbent_total else 0.0
    print(
        "source-summary", name,
        f"incumbent={incumbent_total}",
        f"portfolio={portfolio_total}",
        f"saved={saved}",
        f"saved_pct={pct:.4f}",
        f"winning_blocks={wins}",
        flush=True,
    )
    return incumbent_total, portfolio_total


def main() -> None:
    old = new = 0
    for name, data in {**_synthetic_sources(), **_real_sources()}.items():
        a, b = probe(name, data)
        old += a
        new += b
    saved = old - new
    print(
        "TOTAL",
        f"incumbent={old}",
        f"portfolio={new}",
        f"saved={saved}",
        f"saved_pct={100.0 * saved / old:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
