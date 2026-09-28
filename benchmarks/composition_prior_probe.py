#!/usr/bin/env python3
"""Probe universal priors for the CIX histogram/count vector.

This does not change the codec.  It compares the current exact histogram metadata cost
(active alphabet + uniform positive composition) with full-alphabet symmetric
Dirichlet-multinomial count-vector priors.  The permutation/type-class rank cost is
identical for every candidate and therefore cancels in the comparison.

alpha=1 is uniform over all 256-way non-negative compositions. alpha<1 favours sparse
count vectors; alpha>1 favours balanced ones.  Results are theoretical ideal code lengths
plus a small selector allowance and are used only to decide whether a physical coder is
worth implementing.
"""
from __future__ import annotations

import math
import random
import urllib.request
from pathlib import Path

K = 256
ALPHAS = (0.25, 0.5, 1.0, 2.0)

URLS = {
    "alice29": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "cp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
    "fields": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "grammar": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
    "xargs": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}

def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n-k+1)) / math.log(2)

def counts(data: bytes) -> list[int]:
    out=[0]*K
    for b in data: out[b]+=1
    return out

def current_hist_bits(cs: list[int], n: int) -> float:
    m=sum(c>0 for c in cs)
    if n==0: return 1.0
    active=0.0 if m==K else log2_comb(K,m)
    composition=0.0 if m<=1 else log2_comb(n-1,m-1)
    # mode/varint/byte-rounding is deliberately omitted from both sides.
    return active+composition

def dm_hist_bits(cs: list[int], n: int, alpha: float) -> float:
    # -log2 Dirichlet-multinomial probability of this ordered 256-count vector.
    # log P = log n! - sum log n_i! + logGamma(K a)-logGamma(n+Ka)
    #         + sum[logGamma(n_i+a)-logGamma(a)]
    logp=math.lgamma(n+1)-sum(math.lgamma(c+1) for c in cs)
    logp+=math.lgamma(K*alpha)-math.lgamma(n+K*alpha)
    base=math.lgamma(alpha)
    logp+=sum(math.lgamma(c+alpha)-base for c in cs)
    return -logp/math.log(2)

def generated() -> dict[str,bytes]:
    rng=random.Random(20260928); n=32768
    random_bytes=bytes(rng.randrange(256) for _ in range(n))
    biased=bytes(0 if rng.random()<0.92 else rng.randrange(1,16) for _ in range(n))
    balanced=bytes(i&255 for i in range(n))
    markov=bytearray(); x=0
    for _ in range(n):
        if rng.random()<0.04: x=rng.randrange(64)
        markov.append(x)
    periodic=(bytes(range(37))*((n//37)+1))[:n]
    return {
        "gen-random":random_bytes,
        "gen-biased":biased,
        "gen-balanced":balanced,
        "gen-markov":bytes(markov),
        "gen-periodic":periodic,
    }

def sources() -> dict[str,bytes]:
    out=generated()
    work=Path("benchmark-work/composition-prior"); work.mkdir(parents=True,exist_ok=True)
    for name,url in URLS.items():
        p=work/name
        if not p.exists(): urllib.request.urlretrieve(url,p)
        out["canterbury-"+name]=p.read_bytes()
    return out

def main() -> None:
    block_size=8192
    total_current=0.0
    total_best=0.0
    wins={a:0 for a in ALPHAS}
    blocks=0
    for name,data in sources().items():
        source_current=source_best=0.0
        choice_counts={a:0 for a in ALPHAS}
        for start in range(0,len(data),block_size):
            block=data[start:start+block_size]
            if not block: continue
            cs=counts(block); n=len(block)
            cur=current_hist_bits(cs,n)
            candidates={a:dm_hist_bits(cs,n,a)+2.0 for a in ALPHAS} # 2-bit alpha selector
            a_best,best=min(candidates.items(),key=lambda kv:kv[1])
            actual=min(cur,best) # incumbent remains a zero-regret candidate
            source_current+=cur; source_best+=actual
            if best<cur:
                choice_counts[a_best]+=1; wins[a_best]+=1
            blocks+=1
        total_current+=source_current; total_best+=source_best
        print(name,
              f"current_bytes={source_current/8:.2f}",
              f"portfolio_bytes={source_best/8:.2f}",
              f"saved_bytes={(source_current-source_best)/8:.2f}",
              "alpha_wins",choice_counts,
              flush=True)
    print("SUMMARY",
          f"blocks={blocks}",
          f"current_bytes={total_current/8:.2f}",
          f"portfolio_bytes={total_best/8:.2f}",
          f"saved_bytes={(total_current-total_best)/8:.2f}",
          f"saved_pct={100*(total_current-total_best)/total_current:.4f}",
          "alpha_wins",wins,
          flush=True)

if __name__=="__main__":
    main()
