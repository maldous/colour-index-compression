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

For B3 onward, the whole invocation runs from a supplied immutable snapshot
directory containing the exact module copy; the receipt hashes that copy, the
Python executable, zstandard module and native zstandard backend.  The fresh
decoder inherits that snapshot working directory, never the mutable repository
module path.

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

1. **Causal bounded near-match edit references (B3, active)** — search a bounded
   64 KiB prior window with fixed 1,024-byte records and 64-byte-spaced anchors;
   for a candidate with at least 12.5% equal bytes emit a complete causal
   distance plus one XOR edit byte per source byte, otherwise emit the raw
   record.  The transform itself is then compressed by the matched backend.
   This differs from B2's immediately preceding newline record and has a
   plausible path on repeated page templates.  The direct control, all record
   markers, lengths, distances, XOR bytes and container framing are charged.
   It uses the same synthetic plus three development regions and promotion gate
   as B1/B2; no held-out range is read unless it clears that gate.
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

### B4: fixed XML grammar vocabulary

Earlier negative evidence used an **input-derived** tag dictionary with a
separate identity stream, and a paid word-replacement preprocessor.  B4 differs
materially: it has no learned data, no dictionary transmission and no removed
markup.  It greedily replaces only a fixed ordered vocabulary of 20 canonical
XML and XML-entity constructs with two-byte escape codes; raw `0xff` is itself
escaped.  This produces one complete reversible byte stream, then the same
zstandard 0.25.0 level-19 backend and HTB1 frame as the direct matched control.

Hypothesis: fixed grammar terminals reduce the lexical representation cost of
the recurring Wikipedia XML envelope without input-dependent side information.
The codebook is compressor configuration, so this is explicitly Hutter-specific
and any eventual candidate must charge its program bytes separately.  First
screen: deterministic synthetic XML plus the same three 262,144-byte development
regions; an immutable snapshot executes both compressor and archive-only fresh
decoder.  CPU is capped at four, RAM at 3 GiB with no swap, temporary disk at
1 GiB and wall time at 300 seconds per trial.  Promotion requires complete exact
archives, a two-of-three development win, and aggregate saving of at least
0.25%; otherwise held-out data remains unread.

The immutable B4 development run met that gate.  Its only next measurement is
one unchanged-control comparison at the already reserved held-out offsets
700,000,000 and 850,000,000, both 262,144 bytes.  No vocabulary, ordering,
threshold or backend setting changes between development and holdout.

After that fixed holdout confirmation, one 1,048,576-byte contiguous development
run at offset zero is permitted with the same immutable snapshot.  This tests
whether the effect survives a longer backend context; it is not a new selection
trial and does not alter the representation or unlock full enwik9 execution.

### B4T: charged vocabulary table confirmation

The B4 fixed-codebook archive gain is explicitly **not** a Hutter package or
score: the 20 terminals serialize to 215 bytes, and the current module is 3,151
bytes larger than the preserved B3 module snapshot (a source-size indicator, not
a complete program package).  To separate archive framing from decoder-program
cost, B4T carries that exact canonical 215-byte vocabulary table inside every
candidate archive; its decoder reads and validates it before inversion.  The
control remains direct zstandard level 19.  One frozen B4T snapshot runs both
the candidate and control on offset-zero 1,048,576-byte development input only,
with `taskset -c 16-19`, 300-second wall, 3 GiB RAM/no swap and 1 GiB temporary
disk budgets.  This is a cost-accounting check, not a new vocabulary search or
a promotion to holdout/full-enwik9.

For subsequent receipts, `logical_cpu_cap` means the maximum CPU set assigned
to one experiment; the actual affinity is recorded separately.  Earlier raw
receipts retain their ambiguous `cpu_cores` budget field for auditability.
