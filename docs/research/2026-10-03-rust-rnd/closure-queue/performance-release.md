# Performance release closure queue

Status: `NONEXECUTING_CLOSURE_REGISTER`
Snapshot: 2026-10-03

This register defines the finite performance and release work that may remain
before packaging the current Rust implementation. It authorizes no execution,
source edit, acquisition, publication, Actions change, Silesia run, full Hutter
run, or restart of the cancelled matched pre-refactor corpus wave.

The current native reference is source `6ac05f8e9fd78ff01e2f8d71e6557c5dc66bb8bb`,
tree `9b3cd2a8abec9fcdbd64e2f48b5bc9bb49f46133`. Dispatch must replace this
reference if production source changes, create a new experiment identity, and
invalidate every pending cell whose binary or source binding changed. A docs-only
commit may retain the native source hashes, but the release manifest must say so.

## Closure rule

Each numbered cell receives exactly one observation per declared arm. There are
no repetitions for averages, medians, confidence intervals, or a second attempt
at a surprising timing. A failed, negative, budget-limited, unsupported, or
unavailable result is a terminal result when its raw receipt is preserved. It is
never silently replaced by an easier configuration.

Every executed cell must freeze, before launch: source commit/tree and relevant
file hashes; binary, DSO, lockfile and toolchain hashes; input path/range/bytes and
SHA-256; complete argv and environment; route, effort, format, block/history,
thread/parallelism and memory settings; cgroup path, physical CPU identity,
`cpu.max`, `memory.max`, `memory.swap.max`; wall limit and temporary limit.
Record native child status, wall/user/system time, process RSS, sampled cgroup
high water as a lower bound, complete archive bytes/SHA-256, and a fresh
archive-only Rust restoration byte count/SHA-256. Build-only changes, PGO,
allocator substitution and ISA builds must produce the same complete archive as
their matched baseline. Scaling cells with a deliberately different block size
may change framing and size, which must be reported rather than called a speed-only
change.

All cells run through the existing root WaveScheduler. The aggregate ceiling is
four physical cores, decimal 12 GB memory, 4 GB temporary storage and zero swap.
Profiler, build and timing cells run sequentially in a quiet lease. Concurrent
work makes a timing descriptive and closes no performance cell.

## Evidence already terminal

| Area | Retained evidence | Closure value and limit |
|---|---|---|
| Exact arithmetic | [`perf-f579/REPORT.md`](../perf-f579/REPORT.md) records one matched instrumented Kennedy DEFAULT observation: 2.26 to 2.13 seconds, identical 82,984-byte archive and exact fresh restore. | The rank implementation opportunity is tested and integrated. The 5.75% observation is not a replicated or general throughput claim. |
| Current build and CLI | [`release-6ac0/REPORT.md`](../release-6ac0/REPORT.md) binds the current portable fat-LTO/CGU-1 binaries, a successful locked all-feature build, Clippy, and eight focused CLI checks. | Valid current baseline artifact. It is not a full-suite, warning-clean, pre-bound-toolchain or current Sonar result. |
| Large pipes | [`qualification-6ac0/REPORT.md`](../qualification-6ac0/REPORT.md) records exact G1 and restricted-budget M6 32 MiB live/fresh/old-Rust restoration, interruption, empty, midpoint-corrupt and one-byte-truncated controls. | Streaming correctness/resource evidence. It is not encoder-only throughput, one-core M6 qualification, all-route coverage, or internal native-queue measurement. |
| Allocation mechanisms | [`bounded-reader-allocation/README.md`](../../2026-10-02-rust-performance-audit/bounded-reader-allocation/README.md) and [`ppm-eligible/README.md`](../../2026-10-02-rust-performance-audit/ppm-eligible/README.md) contain qualified reader and PPM-kernel DHAT evidence. | These close the scoped allocation changes. They do not establish final-source whole-CLI allocation or an allocator replacement. |
| Compiler and PGO screening | [`build-matrix/RESULTS.md`](../../2026-10-02-rust-performance-audit/build-matrix/RESULTS.md) and [`build-matrix-886/RESULTS.md`](../../2026-10-02-rust-performance-audit/build-matrix-886/RESULTS.md) tested portable/native, LTO/CGU and disjoint PGO arms. | Historical screens only. They disagree on the practical CGU-16 gain, include nonfinal source, and one packet lacks durable live-cgroup readback. No build policy was retained. |
| Scaling | [`scaling-qualified/README.md`](../../2026-10-02-rust-performance-audit/scaling-qualified/README.md) preserves 120 native receipts. | Timing is unqualified because the executed harness was not retained; 80 two/four-thread decode cells were actual native failures. It supplies no release recommendation. |
| Final-source large source regression | The corrected PTT5 BEST run produced 27,614 bytes and restored through the existing BD2 decoder. | It qualifies the numeric-overflow repair at its tested source. A packaging artifact with a different native source or binary still needs cell Q5 below. |

## Remaining cells

### P. Final-source profiling — four cells

Use the frozen Kennedy input, ordinary DEFAULT, one encoder thread, the portable
release baseline and unchanged codec settings. Profiling overhead is included;
these cells locate work and do not rank release throughput.

| ID | Single observation | Terminal result |
|---|---|---|
| P1 | CPU 8 `perf stat` plus call-graph `perf record`, including cycles, instructions, cache misses, branch misses, context switches and migrations. | Exact archive/restore plus retained samples and lost-sample count, or an explicit kernel-permission/unsupported receipt. |
| P2 | Same command on CPU 16 after topology confirms it is the intended second core class. | Same evidence as P1. This is a different hardware-class observation, not a repeat. If topology does not distinguish the class, record `NOT_APPLICABLE`. |
| P3 | One `strace -c` encode for syscall and I/O attribution. | Exact archive/restore and syscall summary, or `UNAVAILABLE`. Instrumented time is not release throughput. |
| P4 | One `perf lock` observation using the same workload. | Lock report and exact archive/restore, or a retained unsupported/permission receipt. Zero output without a successful profiler status is not evidence of zero contention. |

The existing f579 result already tests its predeclared rank change. New hotspot
ideas discovered here are recorded for a later release; they do not recursively
expand this closure queue or authorize production edits before packaging.

### B. Portable build, LTO and host ISA — at most ten runtime cells

All arms build the same frozen source and lockfile with the same C/C++ inputs.
Screen on one ordinary DEFAULT Kennedy encode. B0 is the sealed current
fat-LTO/CGU-1 release and is reused, not rerun, if its binding remains exact.

| ID | Build arm | Runtime cell |
|---|---|---|
| B0 | Portable opt3, fat LTO, CGU 1 | Existing sealed baseline; one uninstrumented DEFAULT measurement only if no qualified matching runtime receipt exists. |
| B1 | Portable opt2, no LTO, CGU 16 | One DEFAULT encode/decode. |
| B2 | Portable opt2, no LTO, CGU 1 | One DEFAULT encode/decode. |
| B3 | Portable opt3, no LTO, CGU 16 | One DEFAULT encode/decode. |
| B4 | Portable opt3, no LTO, CGU 1 | One DEFAULT encode/decode. |
| B5 | ThinLTO at the better portable opt/CGU point | One DEFAULT encode/decode. |
| B6 | Fat LTO at that same opt/CGU point | Reuse B0 only when its settings match; otherwise one DEFAULT encode/decode. |
| B7 | `target-cpu=native` at the retained LTO/opt/CGU point | One host-specific DEFAULT encode/decode. This can produce a host artifact, never the portable package. |
| B8 | Retained portable candidate, ordinary FAST on frozen Kennedy | One encode/decode against B0 FAST. |
| B9 | Retained portable candidate, CIXG1/LZ-constrained BEST on frozen grammar | One encode/decode against B0 constrained BEST; no unconstrained BEST or compression-ratio claim. |

Record compile wall/CPU/RSS, binary bytes/hashes and DSO hashes for every
artifact. The portable package stays at B0 unless one portable candidate has
identical outputs, a clear improvement in both wall and user CPU on DEFAULT,
and no regression in the single FAST or constrained-BEST checks. A small or
mixed single-observation difference is terminal inconclusive evidence and keeps
B0. B7 closes host-ISA/automatic-vectorisation screening but cannot alter the
portable default.

There is no source-level explicit-SIMD cell. Current profiles do not identify a
specific hot, vectorisable scalar loop with an exact portable fallback, and the
source contains no production SIMD implementation to qualify. Static inspection
of B0/B7 symbols and annotated hot instructions is recorded with B7. A future
intrinsics patch would be a new source experiment, not an unfinished cell here.

### G. PGO — two training cells and six held-out arms

PGO uses the retained portable B-series winner. Training inputs and evaluation
inputs are disjoint by file hash. Build one `profile-generate` artifact, execute
Alice29 FAST once and Calgary `book1` DEFAULT once, merge with the matching LLVM
`llvm-profdata`, then build one `profile-use` artifact. Raw profile count, merge
status and profile-data SHA-256 are mandatory.

Held-out evaluation has exactly six arms: baseline and PGO once each for
Kennedy FAST, Kennedy DEFAULT, and grammar CIXG1/LZ-constrained BEST. Each pair
must have identical archives and cross-decode in both fresh binaries. PGO is
retained only if all three candidate observations avoid a material wall/user
CPU or RSS regression and at least one useful workload has a clear improvement.
Mixed or small results retain the non-PGO portable build. No training retry,
profile tuning, or alternate split follows from these results.

### A. Allocation and allocator — two cells

| ID | Single observation | Decision |
|---|---|---|
| A1 | Run the existing final-source `cix-dhat-audit` target once with its frozen cases, outside production binaries. | Record allocated bytes/events, peak-live semantics, exact reconstruction and resource receipt. This closes selected-kernel allocation instrumentation, not whole-CLI RSS. |
| A2 | Run the same B-series DEFAULT Kennedy binary once normally and once with the already installed `/lib/x86_64-linux-gnu/libjemalloc.so.2` preloaded; hash the library and resolved mappings. | Require identical archive/fresh restore. Report wall/user/system, RSS and cgroup high water. The observation tests allocator sensitivity only; the release keeps its normal system allocator and does not acquire or add a dependency from this screen. |

A2 is not a licence to package an `LD_PRELOAD` requirement. Any linked allocator
proposal is a later source/dependency experiment and does not block this release.

### S. Encoder scaling and parallelism — twelve cells

Use one frozen cached Kennedy input, ordinary DEFAULT unless stated, 64 KiB
blocks, 512 MiB CLI memory and one-thread fresh decode. Every cell runs alone.
The current four-physical-core aggregate limit bounds the curve at four workers;
the superseded 8/12/16/20-worker Cartesian proposal is not revived.

| IDs | Format and parallelism | Workers | Purpose |
|---|---|---|---|
| S1–S3 | CIXG1, explicit block parallelism | 1, 2, 4 | Physical worker curve and deterministic ordered output. |
| S4–S6 | CIXG1, explicit candidate parallelism | 1, 2, 4 | Separate within-block candidate curve and exact winner-order check. |
| S7 | CIXG1, normal automatic parallelism | 4 | Measure the shipped automatic policy without substituting an explicit mode. |
| S8–S9 | CIXG2, explicit block parallelism | 1, 4 | Bound the second independent container without a full duplicate curve. |
| S10 | CIXG1 block parallelism at the best nonregressing worker count, 16 KiB blocks | selected | Block-size tradeoff; size may change and must be charged. |
| S11 | Same selected 64 KiB configuration with 256 MiB CLI memory | selected | Memory-admission interaction; report any candidate omissions or archive change. |
| S12 | CIXM6 FAST, one worker, 64 KiB blocks, 16 MiB CLI memory | 1 | Serial persistent-format anchor only. No parallel M6 claim or state reset. |

Within S1–S9, equal format/block/policy inputs must produce the expected
deterministic archive independent of worker count. Record actual task/thread
peaks, CPU time, wall time, ordered-queue peak and admitted memory. Decoder
parallelism is excluded: the CLI rejects decode `--threads >1`, and preserved
native failures already establish that boundary. A requested 1 MiB CIXG block
is excluded because retained native proof shows the format clamps it to 65,536
bytes; relabelling that as a new block-size result would be false.

These twelve cells may support a narrow recommendation for this input. They do
not support a universal default-thread recommendation or a corpus throughput
claim. Existing defaults remain when results are mixed, size-changing, or
resource-limited.

### Q. Packaging qualification — five gates

Run these after B/G/A/S decisions, against the exact artifact intended for the
private package. Earlier source-exact evidence may be reused only when binary,
source, configuration and acceptance scope match exactly.

| ID | Gate | Pass condition |
|---|---|---|
| Q1 | Pre-bound locked all-feature package build for `cix`, `uncix`, `cixcat` and library. | Exit zero; source/tree/lock/toolchain/C/C++/DSO hashes, build RSS, cgroup and binary manifest retained before and after. |
| Q2 | Full optimized `--lib --bins --tests --examples` suite, serial test execution. | Every result group records its actual test count and exit zero; zero-test filters are labelled and do not masquerade as coverage. |
| Q3 | Audit bench smoke using `-- --test`, once for each registered bench target. | Compile and smoke exits zero. Criterion sampling output is not used as a timing result or average. |
| Q4 | Fresh static scan of the exact source plus retained Clippy all-target/all-feature output. | Scanner/source identity and raw issue inventory retained. Packaging may disclose findings; no false zero-warning claim. |
| Q5 | One final-artifact PTT5 BEST encode plus fresh current and frozen-BD2 archive-only decode. | Exact source SHA, 27,614-byte compatibility expectation or explicitly explained format/policy difference, both restorations exact, bounded resources and nonzero child statuses treated as failure. |

The corrected G1/M6 large-stream packet already binds the 6ac binary. Reuse it
if Q1 produces that exact binary hash; otherwise repeat only those two stream
rows under a new identity. This conditional replay has a maximum of two rows
and is compatibility qualification, not a timing repeat.

## Queue size and stop point

The maximum new runtime observations are: P=4, B=10, G=8, A=3 arms, S=12,
Q5=1, plus at most two conditional stream rows. Build, suite, smoke and scan are
separate qualification phases. Reused exact artifacts reduce this count.

Packaging is ready when every numbered item is terminal, the selected portable
artifact passes Q1–Q5, all positive and negative receipts are sealed, and the
release notes keep single-observation limits. Performance screens do not reopen
the cancelled full pre-refactor baseline, five-repeat CCA matrix, Silesia gate,
full-enwik9 work, public dashboard, or publication. A newly discovered idea is
recorded for a later experiment identity rather than extending this queue.
