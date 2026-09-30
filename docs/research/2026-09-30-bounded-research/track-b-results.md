# Track B first bounded results

All results below are Hutter-specific representation screens, not generic CIX
results or Hutter scores.  Each row is a completed physical `HTB1` archive using
zstandard 0.25.0 level 19, with fresh-process archive-only decode and SHA-256
verification.  The direct control uses the same backend and framing.

| mechanism | region | control bytes | candidate bytes | difference | verification |
|---|---:|---:|---:|---:|---|
| fixed ASCII-space plane | synthetic repeated records | 1,266 | 1,342 | +6.00% | exact |
| fixed ASCII-space plane | enwik9 0..262,144 | 81,812 | 95,017 | +16.14% | exact |
| fixed ASCII-space plane | enwik9 100,000,000..100,262,144 | 90,736 | 105,133 | +15.87% | exact |
| fixed ASCII-space plane | enwik9 400,000,000..400,262,144 | 79,296 | 91,734 | +15.69% | exact |
| newline prefix/edit | synthetic repeated records | 1,266 | 233 | -81.60% | exact |
| newline prefix/edit | enwik9 0..262,144 | 81,812 | 84,969 | +3.86% | exact |
| newline prefix/edit | enwik9 100,000,000..100,262,144 | 90,736 | 93,513 | +3.06% | exact |
| newline prefix/edit | enwik9 400,000,000..400,262,144 | 79,296 | 83,266 | +5.01% | exact |

Both candidates fail their predeclared promotion gate: neither is lower than
the control on two development regions, so the held-out regions were not read.
The line-prefix transform does expose repeated synthetic records, but that
mechanism does not transfer to these initial Wikipedia regions.  Fixed
space/literal separation is a stronger negative: its separated streams lose
cross-symbol context which zstandard's direct model retains.

The raw archives, restored outputs and receipts are under `track-b-results/`.
Receipts record input range hashes, archive and restore hashes, exact physical
framing/payload costs, source build hashes, timings and decoder commands.

## B3 — causal bounded near-match XOR edits

This distinct near-duplicate representation used an immutable module snapshot,
a causal 64 KiB reference window, 1,024-byte records, fixed sparse anchors and
a threshold of 12.5% equal bytes.  Every record carries raw bytes or marker,
length, distance and one XOR byte per source byte; the complete transform is
then compressed by the same zstandard control backend.

| region | control bytes | candidate bytes | difference | copied records | equal bytes | verification |
|---|---:|---:|---:|---:|---:|---|
| synthetic repeated records | 1,266 | 2,495 | +97.08% | 292 | 290,995 | exact |
| enwik9 0..262,144 | 81,812 | 96,055 | +17.41% | 28 | 5,949 | exact |
| enwik9 100,000,000..100,262,144 | 90,736 | 91,542 | +0.89% | 0 | 0 | exact |
| enwik9 400,000,000..400,262,144 | 79,296 | 94,998 | +19.80% | 27 | 5,278 | exact |

The candidate is negative and fails promotion.  The exact copy/edit state is
recoverable, but explicit records plus a full XOR byte at every copied position
discard information already represented efficiently by direct zstandard LZ
matches.  It will not be combined with B1/B2 or tested on held-out regions.

## B4 — fixed XML grammar terminals

This is deliberately distinct from the earlier learnt tag dictionary and paid
word preprocessing: it transmits no input-derived dictionary and removes no
markup.  The immutable B4 snapshot greedily substitutes a fixed 20-terminal
Wikipedia XML/entity vocabulary with escape codes in one reversible stream.
It is Hutter-specific and does **not** establish a Hutter score or eligibility.

| region | control bytes | B4 archive bytes | difference | replacements | verification |
|---|---:|---:|---:|---:|---|
| synthetic XML records | 2,610 | 2,181 | -16.44% | 24,000 | exact |
| dev 0..262,144 | 81,812 | 81,547 | -0.32% | 2,297 | exact |
| dev 100,000,000..100,262,144 | 90,736 | 90,678 | -0.06% | 1,173 | exact |
| dev 400,000,000..400,262,144 | 79,296 | 78,877 | -0.53% | 2,950 | exact |
| held-out 700,000,000..700,262,144 | 82,731 | 82,404 | -0.40% | 1,861 | exact |
| held-out 850,000,000..850,262,144 | 81,479 | 80,984 | -0.61% | 2,911 | exact |
| contiguous dev 0..1,048,576 | 312,672 | 311,973 | -0.22% | 6,745 | exact |

The three development regions saved 742 bytes over 251,844 bytes (0.29%), so
they met the predeclared screen gate before the two untouched hold-out checks.
The longer run retained a smaller physical archive, but this archive-only B4
view has a compiled vocabulary and therefore omits program/model accounting.

The canonical serialized vocabulary has 20 entries, 194 terminal bytes and
**215 serialized bytes** (count plus every length and token).  The B4 immutable
module is 19,768 bytes versus 16,617 bytes for the preserved B3 snapshot, an
incremental **3,151 source bytes**.  These are separate known costs, not a
complete executable/package calculation.

### B4T — vocabulary table charged inside the archive

B4T uses precisely the same frozen vocabulary/order but places its canonical
215-byte table inside the candidate HTB1 archive and makes the independent
decoder parse it.  On the predeclared contiguous 1 MiB development range,
direct zstd was 312,672 bytes and the fully table-charged candidate was
**312,190 bytes**, a 482-byte (0.154%) archive reduction.  The raw receipt's
`framing_bytes=228` includes the 215-byte metadata table; the derived, non-
overlapping accounting is 311,962 compressed payload bytes, 215 metadata bytes
and **13 non-metadata framing bytes**.  Restoration was exact.  The two commands were explicitly pinned to CPU
sets 16–17 and 18–19 respectively and record those actual affinities.

Earlier B1–B4 receipts record a four-core *budget*, but not actual CPU affinity;
their size and verification evidence remains valid, while they must not be used
as controlled speed comparisons.  B4T adds affinity recording for future runs.
Even B4T is not a Hutter result: it does not include full compressor/decompressor
program accounting, a full enwik9 stream, or qualification resource evidence.

### B4T hard-cgroup confirmation

The raw B4T receipt and its erratum remain preserved.  An unchanged pair then
ran sequentially from the same immutable snapshot with `taskset -c 16-19` inside
separate transient user-systemd units configured with `AllowedCPUs=16-19`,
`MemoryMax=3,000,000,000`, `MemorySwapMax=0` and `RuntimeMaxSec=300`.  Both
encoder receipts recorded the actual four-CPU affinity and exact restoration.
The control was 312,672 bytes = 312,661 payload + 0 metadata + 11 framing.  The
candidate was 312,190 bytes = 311,962 payload + 215 table metadata + 13
non-metadata framing.  Thus every component sums to its physical archive and
the result remains −482 bytes (−0.154%).

Systemd reported the configured memory/swap/time limits.  Its completed
transient cgroups did not retain an independently readable peak-memory counter,
so this is evidence of configured hard limits, not a separately measured memory
peak; resource enforcement for the earlier B4/B4T runs remains unverified.
