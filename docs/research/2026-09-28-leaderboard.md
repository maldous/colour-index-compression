# Local leaderboard measurement checkpoint

The objective remains a generic, verified Silesia total below the leading
published result. No Silesia rank has yet been established. All computation is
local; no GitHub Actions jobs were invoked.

The complete prerequisite gate passed exact restoration for all 29 members:
Canterbury (11) totals 500,926 stream bytes, Calgary (canonical 14) totals
872,234. Artificial results are 18, 32, 89 and 75,089 bytes, reported individually
in the companion JSON. These are not Silesia results.

All 12 Silesia inputs were materialized and matched the published MD5 values.
The frozen baseline uses level 3 and the core source digest recorded in the
companion evidence. Each member is independently compressed and decoded.
Both raw stream and CLI wrapper artifacts are preserved and hashed.

The run is resumable with:

```sh
OMP_NUM_THREADS=1 .venv/bin/python benchmarks/leaderboard_run.py \
  --python .venv-pypy/bin/python --fast-comb \
  --manifest results/silesia-manifest.json \
  --output results/leaderboard/silesia --jobs 12
```

Do not run a second writer while the existing manager is alive. Check process
state first. Checkpoints contain locally generated pickle state and must never
be replaced with untrusted external files.

PyPy with exact GMP binomial arithmetic passed 78 tests. Runtime qualification
on four complete members produced byte-identical outputs. Optional memoization
was slower on that qualification set and is disabled in the Silesia run.
The baseline is slow; partial progress must not be extrapolated into a rank.

After every member completes, run:

```sh
.venv/bin/python benchmarks/leaderboard_position.py
```

This refuses incomplete cohorts, checks source and artifact hashes and requires
one encoder policy. Rank is calculated from numeric totals, not visual table
order. The captured table contains 322 entries and its leader is
`paq8px_v215 -12L` at 27,825,511 bytes. A calculated position is an equivalent
numerical insertion, not an official listing. Refresh the published table before
claiming first place.

Full artifacts and runtime logs remain in the ignored `results/leaderboard/`
directory. The companion checkpoint JSON preserves the prerequisite results,
published corpus hashes and leaderboard snapshot data in version control.

## Experimental PPM key cache

`benchmarks/ppm_key_cache.py` caches sorted symbols for growing PPM context
dictionaries, with strong references and a bounded entry count. It does not
change probabilities or candidate selection. Run its generated tournament with
`.venv-pypy/bin/python -m benchmarks.ppm_key_cache`.

All 18 cases (uniform, small alphabet and periodic; orders 1/3/5; cold and
warmed) produced identical compressed bytes and decoded with the original
implementation. Summing each case's fastest of two timings gives 16.43 seconds
baseline versus 14.62 seconds cached, an 11% reduction. Some individual cases
regressed. These measurements ran alongside the local Silesia workers and are
diagnostic, not isolated speed-leaderboard evidence. Raw results are in
`2026-09-28-ppm-key-cache.json`.

The accelerated PyPy/GMP suite passed 78 tests in 70.31 seconds; a separate cache
growth/rescale/exclusion/eviction property test also passed. The cache remains
experimental and is not enabled in the frozen Silesia run. A whole-stream paired
qualification is needed before adoption; this is not a compression-size gain.

The subsequent four-member whole-stream qualification is now complete. Every
artifact matched the control SHA-256 and round-tripped. Aggregate encode time
was 172.38 seconds for the control and 173.24 seconds with the cache; the apparent
kernel improvement did not translate into a whole-stream benefit on this set.
Do not enable the cache for the current Silesia run. Individual measurements and
their concurrent-load limitation are in `2026-09-28-ppm-key-cache-streams.json`.
The runner's explicit `--ppm-key-cache` option exists for further experiments
only and defaults off.
