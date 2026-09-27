"""Small deterministic, format-agnostic tournament for PPM secondary escape estimation."""
from __future__ import annotations

import random

from cix.ppm import decode_ppm, encode_ppm


def iid_skew(n, seed):
    r = random.Random(seed)
    alphabet = list(range(16))
    weights = [32,20,14,10,8,6,5,4,3,3,2,2,1,1,1,1]
    return bytes(r.choices(alphabet, weights=weights, k=n))


def iid_uniform(n, seed):
    r = random.Random(seed)
    return bytes(r.randrange(256) for _ in range(n))


def markov(n, seed):
    r = random.Random(seed)
    x = r.randrange(32)
    out = bytearray()
    for _ in range(n):
        if r.random() > 0.90:
            x = r.randrange(32)
        out.append(x)
    return bytes(out)


def periodic_noisy(n, seed):
    r = random.Random(seed)
    pattern = bytes((3,9,27,81,27,9,3,1))
    out = bytearray(pattern[i % len(pattern)] for i in range(n))
    for i in range(n):
        if r.random() < 0.035:
            out[i] = r.randrange(256)
    return bytes(out)


def repeated_noisy(n, seed):
    r = random.Random(seed)
    base = bytes((i * 37 + 11) & 255 for i in range(97))
    out = bytearray(base[i % len(base)] for i in range(n))
    for i in range(n):
        if r.random() < 0.02:
            out[i] ^= 1 << r.randrange(8)
    return bytes(out)


def sparse_binary(n, seed):
    r = random.Random(seed)
    return bytes(255 if r.random() < 0.035 else 0 for _ in range(n))


def random_walk(n, seed):
    r = random.Random(seed)
    x = 128
    out = bytearray()
    for _ in range(n):
        x = (x + r.choice((-2,-1,0,0,0,1,2))) & 255
        out.append(x)
    return bytes(out)


FAMILIES = (
    ("iid-skew", iid_skew),
    ("iid-uniform", iid_uniform),
    ("markov", markov),
    ("periodic-noisy", periodic_noisy),
    ("repeated-noisy", repeated_noisy),
    ("sparse-binary", sparse_binary),
    ("random-walk", random_walk),
)


def main():
    wins = 0
    incumbent_total = 0
    portfolio_total = 0
    print("n family incumbent see portfolio winner")
    for n in (4096, 16384):
        for idx, (name, make) in enumerate(FAMILIES):
            data = make(n, 1000 + 17 * idx + n)
            incumbent = encode_ppm(
                data,
                max_order=4,
                secondary_escape=False,
            )
            see = encode_ppm(
                data,
                max_order=4,
                secondary_escape=True,
            )
            portfolio = encode_ppm(
                data,
                max_order=4,
                secondary_escape=None,
            )
            assert decode_ppm(incumbent, source_length=len(data)) == data
            assert decode_ppm(see, source_length=len(data)) == data
            assert decode_ppm(portfolio, source_length=len(data)) == data
            best = min(len(incumbent), len(see))
            assert len(portfolio) == best
            wins += len(see) < len(incumbent)
            incumbent_total += len(incumbent)
            portfolio_total += len(portfolio)
            winner = "see" if len(see) < len(incumbent) else "incumbent"
            print(n, name, len(incumbent), len(see), len(portfolio), winner)

    saved = incumbent_total - portfolio_total
    pct = 100.0 * saved / incumbent_total
    cases = len(FAMILIES) * 2
    print(
        f"summary cases={cases} wins={wins} incumbent={incumbent_total} "
        f"portfolio={portfolio_total} saved={saved} pct={pct:.3f}"
    )
    if wins < 3 or saved * 200 <= incumbent_total:
        raise SystemExit(
            "secondary escape did not clear generic 0.5% / 3-case promotion gate"
        )


if __name__ == "__main__":
    main()
