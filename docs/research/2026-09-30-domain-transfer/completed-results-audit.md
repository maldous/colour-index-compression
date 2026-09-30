# Independent audit — completed five-domain results

**All 22 dispatched cells completed and restored exactly.** This audit independently rehashed every archive and restored output; it did not rerun encoding or decoding.

The 18-cell initial pilot and four separately predeclared replication cells all have `VERIFIED_SCREENING` receipts. There were **0 failures, 0 size-rejected outcomes and 0 cancellations**. For all 22 archives, CIXDOM01 physical accounting holds: complete size equals the paid 30-byte outer header, canonical metadata and backend payload. The framed original length matches the immutable input. Each decoded output SHA-256 equals both the receipt source hash and immutable input hash.

The frozen implementation was `39404002c566f75f9b4bc0bcd8be5af4a24ba7dd`; every receipt pins the same runtime-manifest SHA-256 `0823809a8d8a413ff6f2430ad81eef5dcabce5ce94c3847e3e64abf4e34eead1`. Runtime-reported adapter/CIX module hashes all match the corresponding immutable build map. The closure preflight passed before dispatch.

The timing evidence separates encoding from independent decoding: encoder reports state that it did not verify round trips, then a distinct archive-only decoder runs with the source inaccessible. GNU-time logs show zero swaps in both phases for every cell, and all Max RSS values are below the 3 GB cap. Cgroup memory remains a sampled lower bound rather than a claimed peak RSS.

The two positive mechanisms repeated on predeclared distinct inputs:

| Mechanism | First result | Predeclared repeat |
| --- | ---: | ---: |
| Molecular hydrogen slots | 2,056 vs 2,219 B, −163 B (7.35%) | 1,462 vs 1,536 B, −74 B (4.82%) |
| Numerical delta columns | 11,493 vs 11,709 B, −216 B (1.84%) | 8,988 vs 9,936 B, −948 B (9.54%) |

These are complete verified archive measurements on the named inputs. They do not establish a domain-wide gain. The numerical packed-metadata candidate and ELF packed-ID candidate both demonstrate the opposite lesson: a smaller raw intermediate representation can become larger after the fixed PAQ backend. The native NIfTI JXL result is a complete representation-plus-JXL backend trade-off, 226,074 B versus 223,738 B for the PAQ control (+1.04%); it is not a CIX rank-coding result.

The generated table and raw rows retain every candidate before selection: [CANDIDATE-TABLE.md](CANDIDATE-TABLE.md), [results.json](results.json), and [results.csv](results.csv). Full machine-readable audit detail is in [completed-results-audit.json](completed-results-audit.json).
