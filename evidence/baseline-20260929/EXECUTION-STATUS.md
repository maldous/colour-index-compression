# Execution checkpoint — 29 September 2026, 10:14 UTC

The evidence baseline remains incomplete and unpublished. The frozen CIX version
is portfolio 25, commit `f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6`.
Research continues independently at portfolio 26 and later research commits; its
results are not substituted for this baseline.

The official 2026-09-01 English Wikipedia pages/articles multistream download
has completed and passed its published SHA-1 check. The compressed source is
26,797,495,184 bytes; full XML decompression is 117,231,826,047 bytes with SHA-256
`a58e239df7dfb1589bbd96cb810a025bf7f6a63653f01ce1b62cbd935dc14842`.
See `manifests/wikipedia-input.json` for the exact source, scope and preparation.
These are input-acquisition facts, not compression results.

The controlled schedule is frozen: 69 inputs and 1,872 prescribed invocations,
including warm-ups. It comprises 16 currently exact NNLCB inputs, Wikipedia and
52 synthetic class/size combinations. The other 12 NNLCB definitions remain
explicit qualification gaps. Completion of this schedule alone cannot establish
the required complete 28-dataset NNLCB comparison.

Six D1/xml comparator warm-ups completed. The first CIX warm-up had no final
record and its process no longer existed when inspected. Its cause is unknown.
The entire attempt, including its partial payload, remains under
`CIX-r0-interrupted-20260929T100605Z`; its original STARTED record is retained.
It is recorded as INTERRUPTED and excluded from completed measurements. Only
that interrupted warm-up was repeated, with the unchanged configuration. No
completed timing, compressed size or verification was inferred from it.

The scheduler now runs as the transient user service
`cix-evidence-baseline-20260929.service`, with durable logs in the raw run tree.
This avoids reliance on an interactive tool handle. It has no automatic restart
policy and is not enabled at boot. Inspect both the live service and the current
process tree when checking progress; a stale state file is insufficient.
`manifests/controlled-execution-recovery.json` preserves its exact definition.

No measured three-repetition group had completed at this checkpoint. Warm-up
results are not headline evidence. The preparation-only repository tag is not a
final evidence release. The separate evidence Site is still pending.
