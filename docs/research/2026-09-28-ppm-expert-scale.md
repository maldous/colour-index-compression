# Larger PPM byte-expert comparison

All nine physical frames passed independent Python decoding and their stored
input/artifact SHA-256 hashes were checked. The native encoder supplied only
bytes and the fixed bank width 2; no filename or source identity was provided.

| Input scope | Q3 | Q5 byte expert | Bounded PPM P2 |
|---|---:|---:|---:|
| Alice, complete 152,089 bytes | 41,738 | 40,812 | 41,209 |
| Kennedy, first 262,144 bytes only | 16,695 | 16,060 | 39,415 |
| obj2, complete 246,814 bytes | 63,280 | 61,346 | 72,066 |

The new expert improves all three comparisons. The full-member obj2 reduction
against Q3 is 1,934 bytes (3.06%). These are complete framed representations
of the stated scopes, not complete-corpus scores and not a leaderboard rank.
Unlike the earlier 64 KiB qualification, this run did not also compute the
Python encoder's output; it independently decoded every native frame instead.

The fixed 64 KiB portfolio gate remains running across all 29 prerequisite
members. Larger blocks may improve learning further, but these separate
single-frame measurements do not establish a zero-regret larger-block codec.
The next decision depends on the complete gate and full Silesia evidence.
