#!/usr/bin/env python3
"""Small generic PPM local-order-estimation tournament."""
from __future__ import annotations

import random

from cix.ppm import decode_ppm, encode_ppm


def sources():
    n = 8192
    rng = random.Random(20260928)

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

    structured = b"".join(
        f"{i:06d}|{i % 137:03d}|{i % 17:02d}|{(i * 31) % 10007:05d}|{i % 2}\n".encode()
        for i in range(600)
    )[:n]

    return {
        "structured": structured,
        "markov": bytes(markov),
        "periodic-noisy": bytes(periodic),
        "repeated-noisy": bytes(repeated),
        "random-walk": bytes(walk),
    }


def main():
    old_total = 0
    new_total = 0
    loe_wins = 0
    round_trips = 0

    for name, data in sources().items():
        incumbent = {}
        portfolio = {}
        for order in (2, 3, 4):
            old_blob = encode_ppm(data, max_order=order, local_order=False)
            new_blob = encode_ppm(data, max_order=order)
            assert decode_ppm(old_blob, source_length=len(data)) == data
            assert decode_ppm(new_blob, source_length=len(data)) == data
            round_trips += 2
            incumbent[order] = len(old_blob)
            portfolio[order] = len(new_blob)

        old_order = min(incumbent, key=lambda o: (incumbent[o], o))
        new_order = min(portfolio, key=lambda o: (portfolio[o], o))
        old_size = incumbent[old_order]
        new_size = portfolio[new_order]
        old_total += old_size
        new_total += new_size
        loe_wins += new_size < old_size

        print(
            name,
            "old", old_order, old_size,
            "new", new_order, new_size,
            "delta", new_size - old_size,
            "incumbent", incumbent,
            "portfolio", portfolio,
            flush=True,
        )

    saved = old_total - new_total
    print(
        "summary",
        f"old={old_total}",
        f"new={new_total}",
        f"saved={saved}",
        f"saved_pct={100.0 * saved / old_total:.4f}",
        f"wins={loe_wins}",
        f"round_trips={round_trips}",
        flush=True,
    )


if __name__ == "__main__":
    main()
