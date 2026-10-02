# Measured implementation checkpoint

Branch: `research/silesia-competitive`.
Source revision: `15426f310f40b9a3d753313741c28e718f7aceb6`.
The second adversarially reviewed Sonar refactor was committed first at
`1627d33f6`; the count-range implementation optimization followed it.
Actions were checked disabled and the private remote revision was verified.

## Retained count-range improvement

The old encoder generated an arbitrary-precision permutation rank whose bytes
were discarded before emitting the count-range sequence. The new encoder
serializes the identical count header directly. Required composition/colex
ranks remain arbitrary precision. Decoder, framing, selector, history and
block boundaries are unchanged; there is no unsafe code or new production
dependency.

Two distinct matched experiments are reported separately:

| experiment | baseline | candidate | complete output |
| --- | ---: | ---: | --- |
| Canterbury alice29, forced CIXG1 composition/count-range, 7 repetitions | 182.48 ms task-clock | 25.27 ms | identical 92,470-byte archive |
| 4 KiB synthetic count-range kernel, Criterion 30 samples | 16.410–16.670 ms | 11.093–11.180 ms | identical 4,171-byte payload |

The 7.11× and 1.48× speedups describe different inputs and measurement scopes.
They are not an overall automatic-compression speedup.
DHAT on the isolated 4 KiB encoder measured allocated volume falling from
2,571,062 to 206,235 bytes, allocation events from 7,653 to 2,967, and peak
live heap from 18,930 to 10,540 bytes. These are heap measurements, not RSS.
See [complete commands and checks](count-range/README.md).

Root's merged count-range tests passed 6/6. Fresh worker native decoder
round trips covered empty/tiny, repetitive, alphabet, random and Canterbury
inputs; corrupted framing was rejected. The complete old/new archive SHA
provides an independent check beyond the shared-header unit tests.

## Refactor and ordinary CLI probes

The first checkpoint FAST and DEFAULT probe used frozen Canterbury grammar,
three repetitions per release/profile, one thread and fresh native cross
decoders. FAST archives were identically 1,431 bytes; DEFAULT archives were
identically 1,321 bytes. Their 10–20 ms GNU Time measurements are too coarse
for a performance conclusion.

A counterbalanced AB/BA full automatic BEST probe compared pre-refactor
`99f4f7319` against integrated `15426f310` on the same frozen grammar bytes:

| metric | pre-refactor | integrated checkpoint |
| --- | ---: | ---: |
| complete archive, all 3 repetitions | 1,096 B | 1,096 B |
| encode wall mean ± sample SD | 45.687 ± 0.680 s | 46.187 ± 1.532 s |
| encode CPU mean | 45.667 s | 46.163 s |
| mean peak RSS | 102.471 MB | 102.422 MB |

All six archives had identical SHA-256; twelve fresh owning/opposite-release
native decodes restored the original bytes exactly. This small experiment
shows no reproducible overall BEST improvement. Decoder timing resolution
was insufficient for a throughput conclusion. Exact revision/binary hashes,
samples and limitations are in [the summary](matched-best-grammar-summary.json).

## Profiling and work still underway

An initial DEFAULT Kennedy CPU recording had 617 samples, no lost samples,
and attributed 29.40% to BigUint division, 9.31% to PPM observation,
7.37% to BigUint scalar multiplication and 6.48% to BWT sorting. LLVM can
merge identical helpers; symbol names alone do not identify a unique caller.
A separate full automatic BEST profile is being collected. This is not yet
an allocation, bandwidth, scheduling or lock-contention audit of all profiles.

Parallel work is evaluating exact colex recurrence, immutable fixedmix-table
reuse, compiler/LTO/codegen/portable/native variants and PGO. Criterion and
optional DHAT instrumentation are isolated from normal CIX builds.
The local benchmark harness is independently reviewed before dispatch.

The complete performance programme remains open: full gate repetitions,
scaling curves, allocation/lock/I/O attribution, build/PGO replication,
streaming latency and final default-thread/block recommendations are pending.
Sonar's second scan still had 38 complexity findings; remediation continues.
The earlier aggregate test process had no recoverable final status, so no
success is claimed. A new aggregate run has durable logs and exit capture.

## Working release probe artifacts

The integrated release-lto binaries are under:
`benchmark-work/rust-performance-audit/integrated-15426f310/final/`
(`cix`, `uncix`, `cixcat`, `libcix_native.so`, `native-release.json`).
These are functioning measured checkpoint artifacts, not a declaration of
completed final release qualification. Dataset/restoration/archive bytes stay
outside Git; only requested result evidence is committed.
