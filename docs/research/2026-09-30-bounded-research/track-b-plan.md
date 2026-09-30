# Track B — bounded representation screening plan

This is Hutter-specific research.  It does not modify, claim to improve, or
replace the generic CIX policy.  Historical markup/dictionary work was negative
on 64 KiB Webster probes, so this plan tests two different fully charged
mechanisms using a fast matched zstandard control before any combination.

## Frozen first screen

All tests use `benchmarks/hutter_track_b.py` immutable build identity, zstandard
0.25.0 level 19, CPU allocation capped at four cores by the scheduler, 3 GiB
RSS, 1 GiB temporary disk and 300 seconds wall time per trial.  Each command
writes a physical `HTB1` archive, launches a fresh decoder process which receives
only that archive, and writes a SHA-256 verified receipt.  The control has the
same HTB1 framing and backend but directly compresses the source; no backend
gain is attributed to CIX.

Development input is canonical enwik9, fixed independent 262,144-byte regions
at offsets 0, 100,000,000 and 400,000,000; their source-range SHA-256 values are
recorded in receipts.  The held-out offsets 700,000,000 and 850,000,000 are not
read in this screen.  A deterministic repeated-record synthetic case first
checks that the expected mechanism is observable.

### B1: fixed ASCII-space structure separation

Hypothesis: a decoder-known one-bit space-position plane plus non-space literal
stream makes structural whitespace and lexical bytes more stationary than direct
byte coding.  The full bitmask, both compressed payloads, mode byte, original
length and both payload sizes are all in the physical archive.  Promotion needs
a complete archive, fresh-process exact restoration, and a lower physical size
than the matched control on at least two of three development regions with an
aggregate saving of at least 0.25%; then it may run once on untouched held-out
regions.  A failure is retained; no intermediate size stops a run.

### B2: newline-record prefix/edit transform

Hypothesis: adjacent Wikipedia records may share long prefixes, so storing each
record as a prefix length and changed suffix before matched compression lowers
the remaining representation cost.  Prefix and suffix lengths are explicit
varints; ordering and every suffix byte are included in the transformed stream.
Promotion uses the same two-of-three and 0.25% development rule.  It is run
only after B1 and is never combined with B1 in this screen.

The two candidates are representations, not PAQ/CIX claims.  Any later CIX or
predictor integration requires a new matched ablation experiment.

## Ranked next backlog

1. **Content-defined repeated-region edit references** — search a bounded prior
   window for a decoder-reproducible near match, then charge every reference,
   literal and edit operation.  This differs from B2's immediately preceding
   newline record and has a plausible path on repeated page templates.  Screen
   only if a simple bounded matcher can remain below the five-minute budget.
2. **Token-class partition with explicit escape stream** — static XML/text
   lexical classes followed by matched backend compression.  This is lower
   priority because the previous markup/prose work was negative; it must use a
   materially different, fully charged representation and first demonstrate a
   mechanism on development regions.
3. **Field-aware page grammar** — infer only decoder-reconstructible page
   delimiters and separate field values.  It has potentially high impact, but
   parsing ambiguity and framing cost make it more expensive; do not start it
   until a compact grammar/control design is predeclared.

No candidate is combined with B1 or B2 unless each component first clears its
own held-out promotion gate.
