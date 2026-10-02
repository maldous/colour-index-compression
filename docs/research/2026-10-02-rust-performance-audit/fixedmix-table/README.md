# Fixedmix stretch-table reuse

## Scope and hypothesis

Commit `15426f310f40b9a3d753313741c28e718f7aceb6` rebuilt a 4,096-entry
`Vec<i32>` stretch table whenever fixedmix encoded or decoded a block.  The
table is a pure function of the fixed-point constants, so it has no model,
history, input, or archive-version state.  The hypothesis was that one
process-wide immutable table would remove an allocation and repeated integer
work for bounded streaming blocks without changing payload bytes.

The retained change uses `std::sync::OnceLock<[i32; 4096]>`.  It initializes
on the first fixedmix use and subsequently returns a shared immutable slice.
Fixedmix `State`, its history, contexts, recurrence predictor, arithmetic
coder, and all update ordering remain per call.

## Method

Host: Intel Core i9-13900K, Linux x86_64; CPU 10 was pinned with `taskset`.
Toolchain: rustc 1.98.1, `release-lto` (`opt-level=3`, LTO, one codegen unit).
The baseline and candidate were separate clean worktrees at the same source
revision; the only source difference was the table change.  No input name,
type, or corpus information participates in route selection.

The repeated-block measurement used a 4 MiB all-zero local synthetic input
(`sha256 bb9f8df61474d25e71fa00722318cd387396ca1736605e1248821cc0de3d3af8`),
forced `--stream --route mixture --format cixg1 --block-size 4KiB --threads 1
--memory 160MiB`, and `/usr/bin/time`.  This deliberately exercises 1,024
small bounded blocks, where table construction is paid repeatedly before the
change.  It is a kernel experiment, not a corpus compression claim.

## Results

Complete archive SHA-256 was identical for every baseline/candidate repetition:
`fd0554b163c1d61478d3df3a15fce0870c7a4117d186be40b3864c3138245166`
(53,302 bytes).

| metric | baseline (n=3) | shared table (n=3) | change |
| --- | ---: | ---: | ---: |
| encode wall time | 15.56, 14.95, 15.11 s (mean 15.21 s) | 15.13, 14.68, 14.62 s (mean 14.81 s) | -2.6% |
| encode CPU time | 15.51, 14.89, 15.07 s (mean 15.16 s) | 15.09, 14.63, 14.56 s (mean 14.76 s) | -2.6% |
| peak RSS | 5,888 KiB | 5,632–5,888 KiB | no reliable process-RSS change at this resolution |

One 4 KiB cold process run was also recorded with Linux `perf stat`.  Candidate
task-clock/cycles/instructions were 28.52 ms / 133.66 M / 335.13 M, versus
29.35 ms / 138.69 M / 338.13 M for the baseline.  The small sample is
consistent with the repeated-block result; it is not used to claim a precise
latency percentage.  `perf record` on the baseline attributes the dominant
work to `fixedmix::State::probabilities` and `State::update`, so this change
does not conceal that larger future optimization target.

The removed allocation is exactly the old 16 KiB `Vec<i32>` backing store per
fixedmix table construction.  Its effect is below process RSS granularity;
the retained table occupies 16 KiB once per process and needs no unsafe code
or dependency.

## Validation

* Archive byte equality was checked across all six repeated stream encodes.
* Both baseline and candidate `uncix` binaries, in fresh processes, restored
  the 4 MiB candidate archive byte-for-byte.
* A byte-flipped archive was rejected by fresh candidate `uncix -t` with
  `block checksum mismatch`.
* `cargo test --locked --lib fixedmix::tests -- --test-threads=1` passed four
  tests: V1, legacy V2, corrected V3 round trips; truncation rejection; and
  cross-thread one-time table initialization.  The command compiles both the
  library fixedmix module and the CLI's format-compatible module.

Reproduce the primary measurement after building each worktree:

```sh
taskset -c 10 ./rust/cix-native/target/release-lto/cix \
  --stream --route mixture --format cixg1 --threads 1 --memory 160MiB \
  --block-size 4KiB -c /tmp/cix-fixedmix-4m-zero.bin > result.cix
```

This is an implementation-only change: no route, backend, effort policy,
history limit, block boundary, archive format, or selector decision changed.
