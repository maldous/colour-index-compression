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
