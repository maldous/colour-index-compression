# Bounded-model PPM candidate

The fixed generic candidate uses 262,144-byte blocks, at most 65,536 prior bytes,
PPM orders 3/5/7 with exact physical selection, and a raw fallback for each block.
Every block resets the model after bounded history training. Input/output buffers
are still held in memory; this is a bound on model growth, not a streaming-memory
claim. The experimental CIXP version 2 frame includes original length, block size,
CRC32, and explicit block lengths and selectors. Its decoder uses the original
Python PPM implementation. It is not yet wired into the production CIX decoder.

Three focused tests cover byte restoration across block boundaries, empty data,
truncation, trailing bytes, checksum corruption, and invalid block bounds.
All 29 complete prerequisite files also passed exact restoration with the native
encoder. Their physical frame hashes and one shared policy were checked before
launching Silesia. Largest observed prerequisite peak RSS was 314.6 MiB.

| Corpus | Frozen incumbent | Bounded PPM alone | Exact-size portfolio |
| --- | ---: | ---: | ---: |
| Canterbury | 500,926 | 557,027 | 478,842 |
| Calgary, canonical 14 | 872,234 | 804,005 | 798,488 |

The bounded candidate loses on some inputs; retain the incumbent. Portfolio
sizes use each representation's distinct magic, so no additional dispatch byte
is required. A combined production decoder remains integration work. Artificial
is reported per member in `2026-09-28-bounded-ppm-tier1.json`.

After this complete gate, a standalone bounded-candidate Silesia run was started:

```sh
OMP_NUM_THREADS=1 .venv-pypy/bin/python -m benchmarks.ppm_bounded_run \
  --manifest results/silesia-manifest.json \
  --output results/leaderboard/ppm-bounded-silesia --jobs 4
```

It uses exactly the prerequisite policy, records full physical artifacts and
compares decoded bytes before creating a result. The original CIX Silesia run
continues separately. A standalone candidate rank can be calculated only once
all 12 candidate files pass; the combined incumbent/candidate portfolio requires
both full cohorts. Neither result may be inferred from partial progress.
