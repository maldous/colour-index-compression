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
