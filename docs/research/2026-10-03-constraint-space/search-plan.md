# Exhaustive 8-bit constraint search

Prepared only; root runs it under a 60-second lease. The fixed universe is all
256 byte values, represented as four `u64` truth-set words. The catalog has 337
serialized predicates: 16 `bit(position)=value`, 56 pair-XOR conditions, nine
popcounts, and 256 `x<=threshold` predicates.

Every pair intersects its exact truth sets. Every member of every nonempty
intersection is rank/unrank verified by set index. The report includes
contradictions, redundant pairs, independent pairs (`NA*NB=256*NI`), overlaps,
all joint wins, and the top ten positive-volume-interaction cases, including paid losses.

Paid grammar: mode 0 raw is `7 + 1 + 8 = 16` bits (common stored gamma(8) plus byte).
Mode 1 is common `7`, mode bit `1`, gamma(number of predicates), then each predicate:
type 2 bits; bit `position:3,value:1`; XOR `position:3,position:3,value:1`;
popcount 4; threshold 8. Type cost is additional. The suffix uses
`ceil(log2 NI)` rank bits (zero for NI=1); NI is derived from the constraints,
not serialized. No physical archive is emitted by this search; it verifies a
declared prefix-language bit cost only. There is no input identity, dictionary, external
codec, automatic selection, or novelty claim. The direct raw comparison is
reported to eliminate artificial rank-only examples.
