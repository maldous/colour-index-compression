# Count-range: remove discarded exact-rank work

## Scope

This is an implementation-only optimization of native CIXG1 count-range
substream coder 5.  It does not alter route selection, block boundaries,
history, framing, the arithmetic sequence coder, or any encoded format.

The old encoder called `encode_type_class(tile)`, then removed that function's
sequence mode byte and permutation-rank suffix before writing the count-range
arithmetic sequence.  That produced an exact arbitrary-precision permutation
rank which count-range never used.  The new path emits the same count header
directly, then emits the existing range sequence.

Base revision: `e0b96c0fc6e1b3d61c1f250e50911003a732d4a8`.

Candidate patch SHA-256: `9574dce7d94be68143ac6442081a9ca7680f95cd1f3188eb50f2e8a3b9aa6661`.

## Matched profile and method

- Host: Intel Core i9-13900K, 24 physical cores / 32 logical CPUs.
- CPU affinity: logical CPU 28 only (an Atom/E-core according to Linux perf).
- Maximum process build/measurement allocation: two CPUs; no more than 1 GiB
  was requested by this experiment.
- Toolchain: rustc 1.98.1, LLVM 22.1.8; Cargo release profile.
- Input: frozen Canterbury `alice29.txt`, 152,089 bytes, SHA-256
  `7467306ee0feed4971260f3c87421154a05be571d944e9cb021a5713700c38f0`.
- Invocation:

```sh
taskset -c 28 rust/cix-native/target/release/cix \
  --format cixg1 --route composition --backend count-range --threads 1 -c \
  /home/user/src/colour-index-compression/benchmark-work/canterbury/alice29.txt \
  > archive.cix
```

Each `perf stat` result below is seven repetitions.  CLI process startup and
complete CIXG1 archive framing are included.  Output was sent to `/dev/null`
for the timing trial; a separate archive comparison used the same invocation.

| build | mean elapsed | task-clock | cycles | instructions | IPC | branches | branch misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| e0b96c0fc baseline | 183.47 ms +/- 0.73% | 182.48 ms +/- 0.72% | 693,065,836 | 606,945,137 | 0.88 | 97,000,356 | 2,109,565 (2.17%) |
| direct-header candidate | 25.851 ms +/- 1.96% | 25.27 ms +/- 1.83% | 98,544,318 | 145,110,848 | 1.47 | 25,940,928 | 1,160,026 (4.47%) |

This is a 7.11x task-clock reduction (86.15%) for this forced count-range
control.  It does not imply a general `--fast`, default, or `--best` result:
those profiles can choose other coders and routes.

The baseline `perf record -g` showed 62.63% of sampled cycles under
`num_bigint::biguint::division::div_rem`, reached from
`rank::encode_type_class` inside `rank::encode_count_range`.  The candidate
profile instead spends its visible work in the required count header
(36.96%) and arithmetic sequence coding (33.87%); the discarded permutation
rank is absent.  There were no lost samples.  Cache-reference counts are low
and cache-miss variance is high, so no cache conclusion is drawn.

Reproduce the counter capture with:

```sh
sudo -n perf stat --repeat 7 \
  -e task-clock,cycles,instructions,branches,branch-misses,cache-references,cache-misses,context-switches,cpu-migrations \
  -- taskset -c 28 rust/cix-native/target/release/cix --format cixg1 \
  --route composition --backend count-range --threads 1 -c INPUT > /dev/null
sudo -n perf record -g --call-graph dwarf -- taskset -c 28 \
  rust/cix-native/target/release/cix --format cixg1 --route composition \
  --backend count-range --threads 1 -c INPUT > /dev/null
```

## Exactness and decoder checks

The pre-change and candidate complete archives for `alice29.txt` are exactly
equal, including CIXG1 framing:

```
6fa17595f44a7cc44f1d2f43575b7f45edce0242140475cfcc6b1213da05aff1
```

`rank::tests` adds six compiled instances because `main.rs` is also included
by the library test target; all six passed.  The tests compare the new
count-range bytes against an in-test transcription of the pre-change assembly
on empty, tiny, single-symbol, 256-symbol, random-like, and multi-tile inputs;
round-trip each case; verify a type class with cardinality over 128 bits; and
reject a truncated tile.

Fresh `uncix` process round trips also passed for the following frozen CCA
inputs using the forced CIXG1 composition/count-range configuration:

| input | input SHA-256 | input bytes | archive bytes |
| --- | --- | ---: | ---: |
| Artificial a.txt | `ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb` | 1 | 96 |
| Artificial aaa.txt | `6d1cf22d7cc09b085dfc25ee1a1f3ae0265804c607bc2074ad253bcc82fd81ee` | 100,000 | 273 |
| Artificial alphabet.txt | `bc634ceb27746878af610424e3afd5024f31e06f1f3479deda6cb33a21258bf7` | 100,000 | 61,986 |
| Artificial random.txt | `f939ba0ca704df5e4665fca1d934411c856cf4409898c276ed26a3e591729201` | 100,000 | 79,577 |
| Canterbury alice29.txt | `7467306ee0feed4971260f3c87421154a05be571d944e9cb021a5713700c38f0` | 152,089 | 92,470 |
| Canterbury fields.c | `85d73e354cc50cec76cb5a50537cf8dc035f8cbb8480f9e1cbe2f7d6c23393c7` | 11,150 | 7,264 |

Corrupting byte 100 of the candidate `alice29.txt` archive made fresh
`uncix -t` exit 2 with `block checksum mismatch`.

No unsafe code, allocator change, SIMD, or dependency was added.  The
optimization retains all arbitrary-precision count/header ranks; it removes
only an independently materialized arbitrary-precision sequence rank whose
bytes were discarded before output.

## Kernel-only Criterion and allocation audit

The end-to-end number above includes CIXG1 selection and framing.  A separate
pair of disposable instrumentation worktrees measured only
`rank::encode_count_range` on the same deterministic 4,096-byte synthetic
input.  Both used CPU 28, Criterion 0.5.1, 30 samples, one second warmup and
three seconds requested measurement time.  Criterion extended the candidate
collection to 5.12 seconds to obtain its requested 30 samples.

| revision | encoded bytes | SHA-256 | Criterion time | throughput |
| --- | ---: | --- | ---: | ---: |
| e0b96c0fc baseline | 4,171 | `0a5b75ff72f907c5818a01749c6e8a35717d86477e64e6d3db4dfc0a4aca6a6a` | 16.410–16.670 ms | 239.95–243.75 KiB/s |
| direct-header candidate | 4,171 | `0a5b75ff72f907c5818a01749c6e8a35717d86477e64e6d3db4dfc0a4aca6a6a` | 11.093–11.180 ms | 357.77–360.57 KiB/s |

That is a 1.48x kernel speedup at the midpoint. This synthetic input differs
from the English-text CLI control, so the two speedup ratios are not a matched
comparison of kernel versus CLI overhead. Three outliers were reported in
each 30-sample run; the intervals are retained rather than reduced to a
single point estimate.

An audit-only `dhat` global allocator binary encoded that exact same input
once in clean pre-change and candidate worktrees.  Fixture construction occurs
before profiling; the fresh decode and exact restoration assertion occur after
the profiler closes.  The count-range payload bytes and SHA-256 above were
identical in both runs.  The allocator results therefore describe the encoder
alone:

| revision | total allocated | allocation blocks | peak live | live at exit |
| --- | ---: | ---: | ---: | ---: |
| baseline | 2,571,062 B | 7,653 | 18,930 B | 4,172 B |
| candidate | 206,235 B | 2,967 | 10,540 B | 4,172 B |

The candidate reduces counted allocation volume by 91.98%, allocation events
by 61.23%, and peak live heap by 44.32% for this input.  DHAT is a profiling
allocator, not a production allocator or a peak-RSS measurement.
The audit-only dependency and binary remain outside this production change.

The audit commands were:

```sh
taskset -c 28 env CARGO_BUILD_JOBS=2 cargo bench \
  --manifest-path rust/cix-native/Cargo.toml --bench count_range_audit -- \
  --sample-size 30 --warm-up-time 1 --measurement-time 3
taskset -c 28 env CARGO_BUILD_JOBS=2 cargo run \
  --manifest-path rust/cix-native/Cargo.toml --release \
  --features audit-dhat --bin count-range-dhat
```

This narrow improvement may reduce automatic-search cost wherever an eligible
candidate uses count-range.  It does not change FAST, DEFAULT, or BEST
selection policy and therefore cannot by itself establish an overall profile
speedup or a compressed-size change.
