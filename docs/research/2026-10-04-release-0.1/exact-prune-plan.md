# Exact native archive-prefix prune plan

## Change under qualification

For the native whole-archive CIXG and CIXM6 trials only, a candidate writer
has two independent bounds:

1. the existing complete-archive admission capacity; and
2. a snapshot of the current incumbent archive length.

The writer rejects an append only when the resulting serialized prefix would
be *longer* than that snapshot. Equal length remains writable and follows the
existing stable tie policy. External candidates, the raw fallback, streaming,
memory admission, container/route eligibility, and decoder validation are
unchanged.

This is an exact physical fact, not an estimate: no later output operation can
shorten bytes already written to a `Write` stream. A prefix longer than the
incumbent cannot yield a smaller complete archive.

## Independent review proof

Let `W` be the bytes already accepted by a candidate writer and let `A` be any
future complete archive emitted through that writer. The writer contract gives
`W` as a prefix of `A`, so `len(A) >= len(W)`. If appending the next bytes would
make `len(W)` greater than the snapshotted incumbent length `I`, then every
possible `A` has `len(A) > I` and cannot replace the incumbent under the
existing strict-smaller selection rule. If `len(W) == I`, the candidate remains
admissible because equality is not a loss under the stable tie rule. This proof
depends only on append-only output and the snapshot; it makes no timing,
compression-ratio, or model-quality assumption.

## Required qualification

Root runs the frozen-release scheduler. No measurement is to be repeated or
averaged.

- Run the focused unit set plus the existing release-LTO test set. The unit
  controls cover the boundary, exact equality, and a real CIXG encode that is
  omitted without changing the incumbent.
- On predeclared small and medium inputs, compare the complete winning archive
  and fresh decoder SHA-256 between a baseline build and the prune build where
  both runs complete the same candidate set. The expected result is byte
  identity.
- Retain the candidate omission list, completed-candidate count, exact archive
  sizes, elapsed time, CPU time, and peak memory. A prune must be labelled
  `exact archive prefix exceeded incumbent; cannot improve`.
- Separately retain deadline-limited observations. A prune can free time for a
  later candidate, so deadline-limited searches need not select the same final
  archive as the unpruned run. That is a scheduling consequence, not evidence
  against prefix monotonicity.

## Acceptance and stop rule

Accept only if all focused and release tests pass, every matched completed-set
comparison has identical winner bytes and exact restoration, and no route,
external, fallback, or decode path changes. Stop and revert the release-only
change if an equal-length candidate is rejected, a distinct prune is treated as
an error, or a matched completed-set output differs.
