# Single-run native coder control results

All eight configuration measurements passed physical archive hashing and fresh-process exact restoration under CPU20, 1 GiB/no swap. Each input is 16,384 bytes, with identical counts (16 symbols x64) in every 1,024-byte tile. No baseline was rerun.

| Ordering | Exact rank bytes | Remaining-count range bytes | Difference |
|---|---:|---:|---:|
| alternating | 8,570 | 8,602 | +32 |
| clustered | 8,570 | 8,602 | +32 |
| periodic | 8,570 | 8,602 | +32 |
| random | 8,570 | 8,602 | +32 |

The entire 32-byte gap is the range stream bit-length varints: two bytes in each of 16 tiles. Sequence payload bytes are 8,080 for both coders; both pay416 bytes of count headers,32 tile-length bytes,16 mode bytes, and26 outer framing bytes. Termination changes bit lengths/padding but not byte widths on these inputs.

The ideal count-conditioned type-class cost is64,529.341449 bits. Both methods supply identical counts and capture no extra context or ordering relationship. This falsifies an ordering-only modelling benefit in this declared control; it does not test richer conditional models. Arithmetic stream bits are stored output, not summed quantised-CDF prediction cost.

Single-process elapsed nanoseconds, GNU Time CPU/wall and peak RSS, temp high water, command hashes and actual constraints remain in results.json/raw. Millisecond observations are screening measurements; no repeated averages, throughput rank or general performance superiority is claimed.

Neither this experimental wrapper nor any new method is deployed. Follow-up candidates: joint/reused histogram metadata, and context/lane-conditioned counts with full partition cost. Raw controls/negative evidence stay preserved.
