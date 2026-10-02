# Fixedmix stretch-table reuse

> **Timing evidence invalidated: mixed executable identity.** The candidate
> executable in the six-pair counterbalanced run was rebuilt while that run
> was active. The previously reported 3.0% encode and 1.7% decode gains cannot
> be attributed to this change and are withdrawn. Retained measurements below
> are historical, unqualified evidence. Archive equality and exact restoration
> remain valid observations. A fresh comparison using copied immutable
> executables with source, binary and runtime-library hashes is required.

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

An earlier mutable-artifact timing attempt was invalidated and is not used
below.  The qualified repetition rebuilt the two source revisions into unique
`CARGO_TARGET_DIR` locations, copied the `cix` and `uncix` outputs to read-only
artifact directories, and recorded SHA-256 manifests for both binaries and
every resolved dynamic library.  It then ran six counterbalanced AB/BA pairs,
with fresh encode and owning-decode processes, verifying that manifest before
and after each phase.  Odd pairs ran baseline then candidate; even pairs ran
candidate then baseline.  The run used CPU 10, `ulimit -v 1 GiB`, and a
predeclared 600-second wall budget.  Reported confidence intervals are
two-sided 95% Student-t intervals over six paired processes.

The frozen source and artifact identities were:

| role | source revision | `cix` SHA-256 | `uncix` SHA-256 | binary/DSO manifest SHA-256 |
| --- | --- | --- | --- | --- |
| baseline | `15426f310f40b9a3d753313741c28e718f7aceb6` | `e6ede6735f4b59bf75540353f4efcb26e3b05877c8af647cf77ed3f35e6729ab` | `acd854b39b19ae918ef7bac20ca638f6f017f07c1b63addae8f88c10a288fc78` | `4129bce4b7f251cd4bd1c574285f4d9b762aaf8ac8ebed77a67e45edf7883938` |
| candidate | `e72e331039f18c60e1c4dcd1dbfc4fe342e7442c` | `53d912b78c003df7b0a6561a2cc0e1e93d770f6a057bb5ac54ec1991fff97496` | `05df2478053525fa76d4e9078cdeb1627cb75deade0a9e8db5507ac6486b83e8` | `761fa4e0afb896b57e02c2f647ab689d0714b6abffc0e679c5c37ef3537a2282` |

## Results

Complete archive SHA-256 was identical for every baseline/candidate repetition:
`fd0554b163c1d61478d3df3a15fce0870c7a4117d186be40b3864c3138245166`
(53,302 bytes).

| metric | baseline (n=6) | shared table (n=6) | paired change |
| --- | ---: | ---: | ---: |
| encode wall time | 14.658 s, SD 0.194 s | 14.295 s, SD 0.125 s | -0.363 s, 95% CI -0.456 to -0.271 s; -2.5% |
| encode CPU time | 14.603 s | 14.240 s | -2.5% |
| decode wall time | 14.612 s, SD 0.156 s | 14.280 s, SD 0.165 s | -0.332 s, 95% CI -0.483 to -0.180 s; -2.3% |
| decode CPU time | 14.553 s | 14.218 s | -2.3% |
| peak RSS | 5,376–5,888 KiB | 5,632–5,888 KiB | no reliable process-RSS change at this resolution |

`perf record` on the baseline attributes dominant work to
`fixedmix::State::probabilities` and `State::update`, so table initialization
is not assumed to be the dominant fixedmix bottleneck.

The removed allocation is exactly the old 16 KiB `Vec<i32>` backing store per
fixedmix table construction.  Its effect is below process RSS granularity;
the retained table occupies 16 KiB once per process and needs no unsafe code
or dependency.

FAST automatic selection on the 4 KiB fixture selected DEFLATE (its
`--explain` output listed no fixedmix candidate).  It is a functional negative
control: table sharing changes no selector work when fixedmix is not selected.

## Validation

* Archive byte equality was checked across all twelve repeated stream encodes.
* Both owning `uncix` binaries restored their six fresh archives byte-for-byte;
  each output SHA-256 was the source SHA-256 above.
* Fresh cross-decoding also passed: baseline `uncix` decoded a candidate
  archive and candidate `uncix` decoded a baseline archive.
* All 36 pre/post-phase binary/DSO manifest checks and the final checks passed.
* A byte-flipped archive was rejected by fresh candidate `uncix -t` with
  `block checksum mismatch`.
* `cargo test --locked --lib fixedmix::tests -- --test-threads=1` passed six
  tests: all 4,096 table entries equal the legacy calculation; V1, legacy V2,
  and corrected V3 round trips with primed history; truncation rejection; and
  cross-thread one-time table initialization.  The command compiles both the
  library fixedmix module and the CLI's format-compatible module.

Reproduce a qualified measurement only after copying immutable binaries and
recording their SHA-256 and runtime DSO hashes before each pair:

```sh
taskset -c 10 ./rust/cix-native/target/release-lto/cix \
  --stream --route mixture --format cixg1 --threads 1 --memory 160MiB \
  --block-size 4KiB -c /tmp/cix-fixedmix-4m-zero.bin > result.cix
```

This is an implementation-only change: no route, backend, effort policy,
history limit, block boundary, archive format, or selector decision changed.
