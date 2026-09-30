# Track A first result — repeat-candidate conditional compositions

Completed 30 September 2026 with the predeclared plan in `track-a-plan.md`.
The retained receipt is `track-a-first-enforced-receipt.json`; it was executed in
a cgroup pinned to logical CPU 2 with `MemoryMax=2 GiB`, `MemorySwapMax=0`, and
a 300-second tree timeout.  The four input frames all completed in about one
second.  A preliminary unconstrained scheduling attempt is preserved separately
as a log/artifact but is not used as the retained resource-bounded evidence.

| input | rank bytes | matched range bytes | rank − range |
| --- | ---: | ---: | ---: |
| synthetic repeat/edit, 65,536 bytes | 15,124 | 15,594 | −470 |
| enwik9 development offset 0 | 64,298 | 64,360 | −62 |
| enwik9 development offset 100,000,000 | 64,487 | 64,552 | −65 |
| enwik9 development offset 400,000,000 | 63,426 | 63,504 | −78 |
| total | 207,335 | 208,010 | −675 |

Every physical frame includes first literal, source length, checksum, complete
per-context event counts, ordering payload, and exception bytes.  The control
uses exactly the same counts and decoder-reproducible remaining-count state.
Every frame was restored by a fresh child interpreter and SHA-256 matched its
input.

This is a small but real representational result: exact ranks saved 675 bytes
(0.32% of this deliberately weak repeat-predictor representation), entirely in
the ordering field.  It does **not** meet the predeclared promotion criterion:
there is no 0.5% total-size win on two development regions.  The untouched
regions at offsets 700,000,000 and 850,000,000 remain unread.  The next useful
trial is to pack rank fields across context groups and compare against a range
control with equivalently amortised framing; this tests whether the observed
gain is intrinsic combinatorial coding rather than per-group byte/framing cost.
