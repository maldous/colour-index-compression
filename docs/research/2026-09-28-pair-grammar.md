# Generic pair-substitution tournament: not promoted

The experimental codec replaces the most frequent token pair, breaking ties by
numeric token order, with up to 256 reversible rules. It materializes complete
frames after power-of-two rule counts and at termination. Rules, token counts,
original length, CRC32 and dictionary lengths are included. Input is bounded to
64 KiB for this diagnostic. It never uses source labels to choose a model.

Version 1 encodes rule/token integers with the existing integer-stream portfolio.
The second trial also offers version 2, coding serialized tokens with PPM orders
3 and 5, while retaining version 1. Seven cases passed exact round trips in each
trial: four generated distributions and three Canterbury prefixes (at most 8 KiB).
The same bounded-PPM policy was used as comparator for every case.

| Diagnostic input | Grammar integers | Grammar + PPM | Bounded PPM |
| --- | ---: | ---: | ---: |
| Uniform | 8,204 | 8,204 | 8,209 |
| Small alphabet | 3,656 | 3,330 | 3,275 |
| Periodic | 175 | 106 | 101 |
| Repeated phrases | 180 | 141 | 138 |
| Alice prefix | 4,253 | 3,230 | 3,191 |
| Fields prefix | 3,308 | 2,198 | 2,158 |
| Kennedy prefix | 2,699 | 2,361 | 2,361 |

The uniform case's five-byte advantage is raw-frame overhead, not a grammar
compression gain. No compressible probe improved on the comparator; token PPM
mostly closed the gap but added search cost. Do not expand this implementation
into a full corpus trial or add it to the production portfolio on this evidence.
These are small diagnostic results, not complete-member or leaderboard scores.

The two JSON companions preserve sizes, timings, exact restoration and all
materialized search checkpoints. `benchmarks/pair_grammar.py` preserves both
experimental frame versions for reproducibility.
