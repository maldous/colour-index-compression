# First forward-transfer checkpoint: 22 verified physical archives

Wikipedia projections and Hutter research remain paused. Historical work and
the previous implementation are preserved at
`research-before-domain-transfer-20260930` (`a501273c5c0dcb5025d8f777cbfe2f3b4c4f2bf0`).
The five new adapters and measurement path were frozen at
`39404002c566f75f9b4bc0bcd8be5af4a24ba7dd`. All 22 comparisons finished,
independently restored the exact source SHA-256, and stayed within their
predeclared resource budgets. No selector hid a losing candidate.

## Repeatable positive configurations

All PAQ measurements below use **v216 -4 -simd AVX2**, with the same settings,
single-file basename, empty state and paid wrapper on control and candidate.
These are complete archive sizes, including all transform information. They
are not measurements against historical PAQ v215 -12L or v216 -8 settings.

| New input | Original PAQ, B | Candidate, B | Saving | Control encode/decode s | Candidate encode/decode s |
|---|---:|---:|---:|---:|---:|
| PubChem 2D panel, first eight CIDs | 2,219 | 2,056 | 163 B / 7.3457% | 3.08 / 2.99 | 2.66 / 2.64 |
| PubChem 2D, disjoint eight-CID replication | 1,536 | 1,462 | 74 B / 4.8177% | 2.31 / 2.25 | 2.06 / 2.05 |
| NOAA San Francisco, January 2024 | 11,709 | 11,493 | 216 B / 1.8447% | 23.33 / 20.67 | 9.96 / 9.70 |
| NOAA Seattle, January 2024 replication | 9,936 | 8,988 | 948 B / 9.5411% | 19.57 / 18.01 | 8.88 / 8.14 |

The replication inputs were selected and acquired before compression, and
the source closure was required to be identical to the first trial. No
settings were adjusted for either replication. These are small convenience
panels and two geographic water-level assets, not population-level evidence.

The molecular gain is the inherited structural hydrogen representation plus
unchanged PAQ. The numerical gain is reversible causal delta columns plus
unchanged PAQ. Neither proves a new CIX entropy coder beats PAQ. The numerical
path also trades higher peak memory for lower observed wall time: about
761–762 MiB versus 460–462 MiB for the controls. All timings are one measured
run per cell on the recorded shared workstation; no speed leaderboard or
statistical precision is claimed.

## Negative and mixed results

| Configuration | Original PAQ, B | Candidate, B | Complete-size result |
|---|---:|---:|---|
| Same first molecular panel, 3D coordinates | 3,993 | 3,997 | 4 B larger; weak transfer, not a molecular-domain rejection |
| UCI Adult dictionary/remaining-count representation | 12,098 | 13,709 | 1,611 B larger (13.3163%); observed 6.09 / 6.06 s versus 23.42 / 20.95 s |
| ELF section-relative addresses | 41,016 | 41,072 | 56 B larger; only 155 addends / 1,240 byte positions are changed |
| ELF addresses plus packed section identifiers | 41,016 | 41,168 | 152 B larger |
| NIfTI framed original planes + PAQ | 223,738 | 223,767 | 29 B larger |
| NIfTI neighbouring-slice residuals + PAQ | 223,738 | 233,045 | 9,307 B larger |
| NIfTI inherited native lossless JXL path | 223,738 | 226,074 | 2,336 B larger (1.0441%), but substantial time/memory tradeoff |

Native JXL took 4.95 / 0.14 seconds versus PAQ's 132.66 / 121.74 seconds.
Its peak RSS was about 84.5 / 45.7 MiB versus 651.8 / 651.5 MiB. This is a
backend comparison with a size/speed/memory tradeoff, not a structural-only
win or a CIX rank-coding result. The literal database frame (12,108 B) and
raw ELF frame (41,015 B) remain in the complete candidate table. The latter's
one-byte reduction is a framing perturbation, not an address-model win.

## Packing result: recovered raw capacity did not survive the backend

| Isolated packing comparison | Before PAQ | Complete archive before/after | Net result |
|---|---|---:|---|
| NOAA six bounded metadata digits, one mixed-radix stream | 44,640 metadata bytes → 16,078 | 11,493 → 25,761 B | **14,268 B worse** than unpacked columns |
| ELF section identifiers, same address transform | 155 identifier bytes → 95 | 41,072 → 41,168 B | **96 B worse** than unpacked identifiers |

All metadata, lengths and variant choices are charged in those totals.
Recoverable index capacity is not automatically useful after an adaptive
backend: dense mixed-radix bytes can obscure predictable runs and symbols.
PAQ already exploited much of that structure. Preserve these exact packing
losses; do not mandate the tested rank layer in other pipelines.

The database order streams already use remaining-count arithmetic. JXL
already entropy-codes shared image structure. Molecular choice-byte slack
was inspected but not blindly wrapped in another rank coder. There is no
unmeasured claim that removing those bits would improve the final archive.

## Next research, ranked from this evidence

1. **Numerical representation:** retain unchanged delta columns and test
   longer contiguous records and another numeric source/schema, with exact
   exceptions and a matched PAQ control. First establish scaling and the
   value of grouping; do not reinstate the failed metadata rank packing.
2. **Molecular constraints:** retain the unchanged successful model and test
   a larger independently selected 2D record batch, then separate coordinate
   regimes. Small panel savings need scaling evidence before general claims.
3. **Volume tradeoff:** keep native JXL as an explicit practical backend
   alternative. Additional volumes are needed to establish repeatability of
   its time/memory tradeoff; the tested delta-z representation is not promoted.
4. **Database:** retain the complete negative result and useful speed result.
   A future retry needs a specific changed hypothesis about field dependencies
   or ordering information that this per-field representation discarded.
5. **Executable/object:** the current transfer only reaches RELA addends.
   Broader section/function relationships require a new documented coverage
   argument; do not extrapolate this tiny address-normalization trial to the
   historical ECOFF result or all executable data.

All five domains stay in the forward backlog. None of these decisions resumes
Wikipedia, Hutter or the historical Silesia tournament. No full-enwik9 run,
GitHub Action or publication occurred. The inherited production portfolio is
unchanged; these are separate research candidates, not a silently changed
automatic selection policy.

## Evidence and recovery

* [All candidates](CANDIDATE-TABLE.md), including complete sizes, decode status,
  timing and peak memory before selection.
* [CSV](results.csv) and [JSON](results.json): source hashes, physical payload
  and metadata sizes, commands/configuration references and every receipt.
* `pilot-v1.json` and `replication-v1.json`: immutable declared trials.
* `runs/`: physical archives, restored files, immutable source snapshots, GNU
  time logs, progress/resource logs and independent verification receipts.
* `environment.json`, `runtime-manifest.json` and `preflight.json`: machine,
  dependency identities and 37 passing focused tests / import-isolation gate.
* `completed-results-audit.json` / `.md`: independent readback and arithmetic.

Regenerate tables with `.venv/bin/python -m benchmarks.domain_summary`.
Already claimed cells are rehashed/reused, never automatically restarted.
Archive-only replay needs the identified software/runtime, not the original
input. Runtime/program inventory is reported separately and is not a minimal
distribution package. There is no prize or global-ranking claim.
