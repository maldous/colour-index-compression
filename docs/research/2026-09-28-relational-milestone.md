# Verified relations milestone — 28 September 2026

The best completed Silesia result is **52,036,355 physical bytes**, equivalent to
**172nd among the 322 published rows**, improving the completed bounded-PPM result
by 2,499,558 bytes (4.58%). All 12 full files restored exactly. The live leaderboard
HTML was fetched again and its SHA-256 matched the preserved snapshot. This is a
numerical insertion, not an official listing. First place is still 27,825,511 bytes;
CIX remains 24,210,844 bytes above it.

This Silesia result belongs to the existing **CIXT1 joint PPM/rounded-mixer policy**.
The new relation models below are a separate experiment and have **no completed
Silesia total**. Do not attribute the 172nd-place result to them.

## New complete prerequisite result

| Complete corpus | Previous R6 | Larger window only | R7 with relations | Saving against R6 |
|---|---:|---:|---:|---:|
| Canterbury, 11 members | 461,308 | 446,127 | **439,678** | **4.69%** |
| Calgary, canonical 14 | 796,468 | 762,939 | **759,386** | **4.66%** |

All 29 Canterbury/Calgary/Artificial inputs restored exactly, and no member grew.
Artificial is reported individually: a.txt 13→13; aaa.txt 71→71;
alphabet.txt 88→77; random.txt 76,424→76,424 bytes.
These are experimental standalone mixer portfolios, not the production decoder.

The ablation keeps framing and incumbent selection identical. It establishes
**6,449 bytes of additional Canterbury savings and 3,553 Calgary bytes specifically
from the relation models**, beyond the larger learning window. Most of the total
improvement comes from increasing the learning window; the new relations add a
smaller independently measured gain. Their combined model was not universally
better, so exact physical selection retains the old stream when needed.

## What was implemented

CIXQ6 mixes ordinary byte/bit contexts and the PPM expert with two causal views:

1. **Successor histories:** each byte value acts as a colour. Track the last two
   symbols that followed that colour, and predict using both the successor history
   alone and the colour plus that history. The shared view can learn relationships
   across different byte values.
2. **Modular differences:** learn an order-0/order-1 distribution of successive
   byte differences modulo 256, map that distribution back onto possible next
   bytes, and mix its bit probabilities with the other experts.

Every predictor uses only previously decoded bytes. No filenames, types, corpus
IDs, pre-trained source dictionary, language model or ISA information enters the
codec. CIXR7 uses fixed 1 MiB blocks, raw fallback, modes 0/1/2 and bank widths 0/2.
It selects complete physical frames and then retains the complete R6 incumbent
unless the new stream is strictly smaller. Both representations have real decoders.

## Why this direction is useful, and what is not established

The histogram plus a rank among its arrangements is classical enumerative coding,
not a newly established information-theoretic invention. A colour renaming alone
cannot reduce information. Histogram metadata savings cannot eliminate the cost of
encoding the arrangement. The opportunity is to discover useful conditional
relationships between occurrence positions, transitions and residuals, so that the
arrangement becomes more predictable without external knowledge.

The current experiment realizes that idea as multiple online, decoder-reproducible
views with exact selection. It is a useful measured CIX improvement. It does **not**
establish a new compression principle, global novelty, or eventual first place.
Context mixing, indirect models and predictive transforms have substantial prior
art. Further novelty claims require a narrower comparison against that literature.

Primary references:
- [Cover, Enumerative Source Encoding (1973)](https://isl.stanford.edu/~cover/papers/transIT/0073cove.pdf)
- [Mahoney, Data Compression Explained](https://mattmahoney.net/dc/dce.html), especially indirect models, context mixing, match models and predictive transforms.

## How experiments became faster

- Measured 16 available CPUs and about 62 GiB total RAM. Used bounded process pools;
  all computation ran locally, with no GitHub Actions or workflow changes.
- A fixed 72-trial, nine-input diagnostic tournament completed in **48.36 seconds**
  using six processes; every emitted candidate was decoded and compared exactly.
  Prefix probes remain diagnostics, never corpus scores.
- The complete 29-member R7 gate finished in **387.39 seconds** using six processes,
  including candidate verification and fresh decoding of cached incumbents.
- Native Q2/Q3/Q5 and Q6 decoding removes the slow Python verification bottleneck.
  Q6 passed 75 paired Python/native encoder and decoder cases, including real
  64 KiB data, a >64 KiB boundary and counter rescaling. Legacy decoding passed
  54 paired small cases plus six existing real Q3/Q5 frames (152–262 KiB).
- On the 64 KiB obj2 qualification probe, native decoding took **2.52 s** versus
  **59.62 s** in PyPy, about **23.7×** faster. This is a local paired timing probe,
  not a standardized speed-leaderboard result.
- Added standalone dependency-aware parallel decoding: independent mixer blocks
  run in parallel; PPM blocks start only after the necessary previous decoded
  bytes exist. It never reads the original input to supply decoder history.
- An extra count-pointer/squash-table/reservation optimization was byte-identical
  but about **5% slower** in its paired tournament; it is **not adopted**.

For Silesia, 11 completed joint records already had independent Python round trips.
The remaining Mozilla artifact was independently restored by the qualified native
mixer plus Python PPM/framing decoder using four processes. Its original encoding
time was unavailable in the pending worker record and is explicitly null in the
alternate verification record. The original slow verification was not overwritten.

## Verification and reproducibility

**99 repository tests passed** (`OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
--timeout=45`). The focused gates check encoder agreement, exact decoder restoration,
framing rejection and incumbent retention. Full reports preserve input/output
hashes, source/binary hashes, physical byte counts and measured timings.

Native builds (run from the repository):

```sh
g++ -O3 -std=c++17 -shared -fPIC benchmarks/native_relational_mixer.cpp -o results/leaderboard/native_relational_mixer.so
g++ -O3 -std=c++17 -shared -fPIC benchmarks/native_legacy_mixer.cpp -o results/leaderboard/native_legacy_mixer.so
OMP_NUM_THREADS=1 .venv-pypy/bin/python -m benchmarks.relational_qualify
OMP_NUM_THREADS=1 .venv/bin/python -m benchmarks.legacy_qualify
OMP_NUM_THREADS=1 .venv/bin/python -m benchmarks.relational_probe
OMP_NUM_THREADS=1 .venv/bin/python -m benchmarks.relational_tier1
OMP_NUM_THREADS=1 .venv/bin/python -m benchmarks.relational_ablation
OMP_NUM_THREADS=1 .venv-pypy/bin/python -m benchmarks.joint_parallel_verify
```

Tier1 and joint verification reuse already qualified physical artifacts in
`results/leaderboard/mixer-ppm-large-tier1` and `joint-silesia` respectively.
`relational_portfolio.encode(data)` can also compute its incumbent without that
cache. Artifacts remain local; no GitHub compute or source push was used.

The next experiment should use the qualified fast verification path and small
held-out block tournaments to test whether these relations improve *joint* PPM/mixer
streams. Do not launch another expensive whole-corpus portfolio merely because a
synthetic probe improves. Preserve the full evidence stack and require an actual
complete Silesia run before assigning a rank to R7 or a successor.
