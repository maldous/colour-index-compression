# Track A — first bounded matched-information experiment

Predeclared before execution on 30 September 2026.

The candidate representation partitions next-byte repeat successes by the preceding byte.  Each partition transmits its event count and success count, then encodes its ordering by an exact binary type-class rank.  The matched arithmetic control receives the same predictor, same partitions, same counts, same remaining-count constraint, same exception bytes, source length, checksum and framing.  It differs only in using arithmetic coding for the conditional ordering.

The screening set is one deterministic synthetic repeat/edit stream and three 64 KiB fixed enwik9 development regions at offsets 0, 100,000,000 and 400,000,000.  Holdouts at 700,000,000 and 850,000,000 are not opened.  There is no warm-up.  The total trial budget is at most 300 seconds, pinned to logical CPU 2, with 2 GiB RAM, no swap and 1 GiB temporary disk.

Promotion requires exact child-process decoder SHA-256 verification for all physical streams and rank at least 0.5% smaller than range across two disjoint development regions.  A failure or negative result is retained; no heldout input is consulted unless promotion succeeds.

## Second predeclared ablation

The first result retained a separate arithmetic termination and bit-length field
for every context, while ranks still had a byte-aligned field per context.  The
second trial changes only the control's ordering representation: it has one
shared arithmetic stream across all contexts, preserving the same paid count
vector and resetting each context's decreasing-count state at its boundary.
The rank representation remains unchanged.  This directly tests whether the
first result was caused by per-context arithmetic framing.  It uses the same
four development inputs, resource limits and untouched holdouts.  Promotion is
not reconsidered unless the rank result survives this stronger control.
