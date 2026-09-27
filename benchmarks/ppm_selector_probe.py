#!/usr/bin/env python3
"""Discriminating tournament for PPM order selection.

Compares the legacy single-escape estimator with the active portfolio-aware estimator
against exact physical PPM payload sizes. Inputs are generic byte processes plus a
small standard Canterbury sample; no result is used as a codec-side specialization.
"""
from __future__ import annotations

import random
import urllib.request
from pathlib import Path

from cix.ppm import (
    decode_ppm,
    encode_ppm,
    estimate_ppm_bits,
    estimate_ppm_portfolio_bits,
)

ORDERS = (2, 3, 4)
BLOCK = 16384

FILES = {
    "alice29.txt": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "cp.html": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
    "fields.c": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "grammar.lsp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
    "xargs.1": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}


def synthetic_sources():
    n = 8192
    rng = random.Random(20260928)

    structured = b"".join(
        f"{i:06d}|{i % 137:03d}|{i % 17:02d}|{(i * 31) % 10007:05d}|{i % 2}\n".encode()
        for i in range(600)
    )[:n]

    markov = bytearray()
    x = 0
    for _ in range(n):
        if rng.random() < 0.04:
            x = rng.randrange(64)
        markov.append(x)

    periodic = bytearray((i * 29 + (i % 7) * 3) & 255 for i in range(n))
    for i in range(n):
        if rng.random() < 0.03:
            periodic[i] ^= 1 << rng.randrange(8)

    repeated = bytearray((b"generic-context-pattern|" * 500)[:n])
    for i in range(n):
        if rng.random() < 0.02:
            repeated[i] ^= 1 << rng.randrange(8)

    walk = bytearray()
    x = 128
    for _ in range(n):
        x = (x + rng.choice((-2, -1, 0, 0, 0, 1, 2))) & 255
        walk.append(x)

    return {
        "synthetic-structured": structured,
        "synthetic-markov": bytes(markov),
        "synthetic-periodic-noisy": bytes(periodic),
        "synthetic-repeated-noisy": bytes(repeated),
        "synthetic-random-walk": bytes(walk),
    }


def real_sources():
    root = Path("benchmark-work/ppm-selector")
    root.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, url in FILES.items():
        path = root / name
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        out["canterbury-" + name] = path.read_bytes()[:BLOCK]
    return out


def main():
    sources = {}
    sources.update(synthetic_sources())
    sources.update(real_sources())

    old_total = 0
    new_total = 0
    full_total = 0
    exact_total = 0
    improved = 0
    worsened = 0
    exact_hits_old = 0
    exact_hits_new = 0
    exact_hits_full = 0

    print("case bytes exact old new full old_size new_size full_size best_size")
    for name, data in sources.items():
        prefix = b""
        exact = {}
        for order in ORDERS:
            payload = encode_ppm(data, max_order=order, prefix_history=prefix)
            assert decode_ppm(
                payload,
                source_length=len(data),
                prefix_history=prefix,
            ) == data
            exact[order] = len(payload)

        old_est = {
            order: estimate_ppm_bits(
                data,
                max_order=order,
                prefix_history=prefix,
            )
            for order in ORDERS
        }
        new_est = {
            order: estimate_ppm_portfolio_bits(
                data,
                max_order=order,
                prefix_history=prefix,
            )
            for order in ORDERS
        }
        full_est = {
            order: estimate_ppm_portfolio_bits(
                data,
                max_order=order,
                prefix_history=prefix,
                sample_limit=len(data),
            )
            for order in ORDERS
        }

        exact_order = min(ORDERS, key=lambda order: (exact[order], order))
        old_order = min(ORDERS, key=lambda order: (old_est[order], order))
        new_order = min(ORDERS, key=lambda order: (new_est[order], order))
        full_order = min(ORDERS, key=lambda order: (full_est[order], order))
        old_size = exact[old_order]
        new_size = exact[new_order]
        full_size = exact[full_order]
        best_size = exact[exact_order]

        old_total += old_size
        new_total += new_size
        full_total += full_size
        exact_total += best_size
        exact_hits_old += old_order == exact_order
        exact_hits_new += new_order == exact_order
        exact_hits_full += full_order == exact_order
        improved += full_size < old_size
        worsened += full_size > old_size

        print(
            name,
            len(data),
            exact,
            old_order,
            new_order,
            full_order,
            old_size,
            new_size,
            full_size,
            best_size,
            flush=True,
        )

    saved = old_total - full_total
    regret_old = old_total - exact_total
    regret_new = new_total - exact_total
    regret_full = full_total - exact_total
    print(
        "summary",
        f"cases={len(sources)}",
        f"old={old_total}",
        f"new={new_total}",
        f"full={full_total}",
        f"best={exact_total}",
        f"saved={saved}",
        f"old_regret={regret_old}",
        f"new_regret={regret_new}",
        f"full_regret={regret_full}",
        f"hits_old={exact_hits_old}",
        f"hits_new={exact_hits_new}",
        f"hits_full={exact_hits_full}",
        f"improved={improved}",
        f"worsened={worsened}",
        flush=True,
    )
    if full_total > old_total:
        raise SystemExit("full-block portfolio selector regressed exact physical PPM bytes")


if __name__ == "__main__":
    main()
