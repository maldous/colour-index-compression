# Performance audit status

Frozen combined source: `a628bda23` on `research/silesia-competitive`; the private remote
was last verified at `e03b7af8b`. Subsequent reviewed checkpoints await the next private push. Reviewed streaming, portfolio and decoder admission
helpers are merged. This is an interim checkpoint, not completed Sonar remediation
or final corpus qualification. Repository privacy and disabled Actions were
read back before the latest push.

## Retained implementation changes

| Change | Measured evidence | Compatibility |
|---|---|---|
| Count-range avoids computing a discarded permutation rank | 7.11× forced-route Canterbury CPU improvement; a distinct 4 KiB kernel improved 1.48× | Identical complete archive; necessary ranks remain BigUint |
| Exact colex recurrence with bounded cancellation checks | Strong/weak/absent cases; old large strong case exceeded its budget | Identical deterministic outputs; no fixed-width rank truncation |
| Shared immutable fixedmix stretch table | Corrected six-pair screen: encode 2.48%, decode 2.27% faster on the declared forced-mixture input | Identical complete archives and fresh native restores |
| Borrowed PPM context lookup | Controlled kernels: approximately 3–34% encode and 3–33% decode mean improvement depending on input; allocation events reduced | Identical payloads and fresh cross-decoding; not a general CLI speed claim |
| Fixed PPM eligible scan without temporary vectors | Controlled fixed order-3 kernels: approximately 16–30% lower encode means; lower allocated bytes and events | 32 byte-identical payload cases and fresh cross-decoding; decoder path unchanged |
| Integer decoder high-bit guards | 18 repeated boundary executions, 20 existing module executions and 16 integration tests passed; correctness evidence only | Valid maximum-width values preserved; oversized varints and Rice/PFOR components rejected |
| Checked payload arithmetic and varints; PPM rescale spelling | Boundary, overflow, malformed-input and captured payload tests | Valid payload bytes unchanged |
| Streaming setup/worker/output helpers | Independent review, G1/G2 byte identity, idle and slow-consumer pipe checks | Framing, ordering, model behavior and resource values preserved |

Evidence is in `count-range/`, `colex-rank-0e8685/`, `fixedmix-table/`,
`ppm-borrow/`, `ppm-eligible/`, `ppm-rescale-ceil/`, and `gstream-refactor/`.
Reviewed helper refactors also cover numeric coding and CLI encode options.
PPM model-control helpers and its varint guard are also reviewed and merged;
all-method v3/v4 and SEE/prefix receipts are correctness evidence, with
per-process resource coverage limitations disclosed. The numeric fixture now
exercises real decoder modules rather than rejecting
stubs; all 18 affected optimized example tests passed.

## Qualification and open work

| Requirement | Current evidence / next work |
|---|---|
| Pre-refactor versus current matched CLI | Three paired automatic BEST grammar runs: 14.2% lower mean wall time for combined `8865bfbcc`; wall-time paired confidence interval includes zero. One small input does not establish general improvement. |
| Regression tests | Combined `8865bfbcc` passed 359 test executions; newer boundary and PPM targeted tests passed. Combined `9214e2f8b` exposed a rejecting numeric example stub, now repaired. The direct optimized `40d3520db` all-feature library/binary/integration/example suite exited zero; the separate Criterion smoke also exited zero. Reviewed raw logs, exit receipts and artifact metadata are retained in `combined-40d-validation/` (598 repeated test executions, not unique tests). Later `55aac92a1` passed 652 repeated executions and Criterion smoke; `d52fa7f72` passed 664 executions across 40 executables and Criterion smoke. Their immutable packets are retained in `combined-55-validation/` and `combined-d52-validation/`. The immutable `45e7c68e7` release passed 698 repeated test executions across 40 result groups (five contained zero tests), plus Criterion smoke. Later streaming, portfolio and decoder changes have scoped checks and archive parity; the final combined release validation remains pending. |
| Profiling | DEFAULT Kennedy and BEST grammar perf recordings identify BigUint division, PPM, BWT and mixing work. Full cache/bandwidth, scheduling, lock and I/O attribution remains open. |
| Allocations | Encoder-only count-range DHAT and controlled PPM kernel DHAT completed. Fixed PPM eligible-vector removal is retained with 80 cgroup-read-back ABBA processes and raw allocation receipts; no whole-CLI improvement is inferred from kernels. |
| Streaming latency | Actual idle producer and slow-consumer pipes produced compressed and reconstructed bytes before EOF, including a root no-swap 128 MiB repetition. A 256 MiB raw-route pipe restored exactly inside a read-back 64 MiB aggregate cgroup with swap disabled, bounded relay and slow-consumer backpressure. This is a correctness/resource control, not a selector or persistent-history performance result. |
| Scaling | A 120-cell DEFAULT G1 screen completed. One-thread restores passed; explicit two/four-thread decoding is rejected. All timing rows are unqualified because the executed harness source identity was not retained. Native receipts preserve the failures; a direct-child status supervisor fixes future experiments under a new identity. No qualified decoder scaling curve is claimed. The new bounded scaling executor is implemented, independently reviewed, and passed nine local unit/mock tests after adding GNU-time CPU/RSS/throughput receipts and explicit physical-versus-logical topology through 24 threads. It uses the existing scheduler and native status receipts; no scaling corpus run has been dispatched. |
| Persistent history versus independent blocks | G1 is already independent; its reset flag cannot establish this tradeoff. Genuine persistent-format comparisons remain open. |
| Compiler / PGO | Portable/native, LTO/codegen and held-out PGO screens exist. PGO improves some encode screens but regresses decode; no build-profile change retained. Some historical resource readbacks were not retained, so those results remain screens. |
| Sonar | The corrected `d52fa7f72` scan records 17 native complexity findings and 50 imported Clippy findings (67 open), with raw/imported discrepancies retained in `sonar-d52-corrected/`. The corrected `45e7c68e7` scan and a fresh project control each record 42 open findings: 9 native complexity and 33 imported Clippy findings. Historical closed findings and all 15 importer drops are retained separately. Subsequent helper changes await a final combined rescan; remaining encoder and codec cleanup continues. No zero-warning claim. |
| Full CCA gate then Silesia | Paused until reviewed cleanup and a new immutable release are complete. Corpus execution policy remains four datasets concurrently, four threads each. |
| Default thread/block recommendation | Pending qualified scaling, memory and history comparisons. Existing defaults remain. |

No dataset acquisition, Hutter restart, GitHub Actions, new ranking or public
Site result is authorized by these kernel and implementation measurements.
Recorded losses, failed attempts and limitations remain part of the evidence.

## Current resource and allocation work

The phase harness now parses unified cgroup paths correctly; an actual constrained
process and sixteen local tests passed. Future plans must bind the new helper
hash; historical missing readbacks are not retroactively qualified.

The explicit CIXB1 input path now uses a capped, fallible reader instead of an
unconditional 128 MiB reservation. Six boundary tests and six gzip/bzip2 CLI
cases passed, including complete archive parity and fresh native restores.
The conservative source allowance charges overlapping growth and leaves codec
admission separate. It can reject a large source earlier under a small budget;
it does not make this named-file path streaming.

The isolated DHAT reader experiment used eight actual child-bound processes.
Empty and 2 KiB input allocations fell from 128 MiB to 64 KiB; the 1 MiB case
used 1 MiB final capacity and 2,031,616 cumulative allocation bytes. This is
reader allocation evidence, not whole-CLI peak RSS or throughput evidence.
See `external-reader-integration/` and `bounded-reader-allocation/`.

## Final cleanup checkpoint (2026-10-03)

Portfolio, TrialState, candidate selection, M6 trial families, BWT/sparse coding,
and wavelet/bitplane helpers are merged with scoped restoration and byte-parity
evidence. The word-reconstruction helper is merged after independent source review,
boundary tests and 15 fresh archive restores with both current and pre-helper
Rust decoders. Historical incomplete full-library
runs remain labelled incomplete; scoped tests do not replace final validation.

The combined source is frozen at `a628bda23`. A fresh matched pre-refactor
`99f4f7319` build is running; final all-feature optimized validation, Criterion
smoke and a fresh Sonar scan are in progress or queued behind that build. The
hotspot runner is prepared with source/hash and actual descendant-resource
checks; preparation is not profiling. Full repeated CCA comparisons, qualified
scaling curves and build-profile replication remain open. No new corpus
performance or ranking claim is made.

## Verified interim release and follow-up cleanup

`a628bda23` completed its optimized all-feature suite: 44 successful result
groups, 748 repeated passed executions, and a separate Criterion smoke pass.
The fresh matched pre-refactor `99f4f7319` artifact and both metadata/manifests
were independently checked. Packets are under `2026-10-03-rust-performance-audit/`.

The fresh scan of that exact source records 33 open findings: 7 native
complexity and 26 imported Clippy. Fourteen importer drops remain in the warning
inventory. This is an interim release, not zero-warning completion.

Follow-up reader/chain and five encoder helpers are merged. Shared library codec
modules now use one instance with the included CLI; focused compile/boundary
checks pass. Legacy LZ reconstruction metadata and branch cleanup is also merged.
Remaining CLI warning fixes and streaming request grouping are being qualified
in separate worktrees. Adversarial review rejected false CIXZ1 and OOM-test pass
claims from one packet; its corrected independent rerun is pending. No unqualified
claim is used to rank or publish results.

The next combined source must pass optimized validation and a fresh scan before
corpus measurements resume. The intended corpus execution remains four datasets
concurrently with four encoder workers per dataset, with the CCA gate first.

## Final qualified source and matched measurement restart

Exact source `bd2a0d97bb4bc5847b55113341ad8de94c269c7f` passed the
locked optimized all-feature build, 44 suite groups / 713 passed executions,
and Criterion smoke. The reduction from 748 executions removes duplicate
library codec modules; it does not remove their CLI tests. Root independently
verified all 26 final validation manifest entries and artifact hashes.
Build/suite/Criterion cgroup peaks were 1,008,672,768 / 1,489,833,984 /
371,957,760 bytes, each with a fresh 2 GiB limit and zero swap.

The exact final source has zero current Sonar issues and zero imported Clippy
warnings across 82 indexed Rust-scope files. Compiler and vendored C++ notices
remain separately retained. Root verified the final Sonar packet checksums.
These findings do not establish whole-project C/C++ warning cleanliness.

Matched plan `2026-10-03-matched-bd2-v1` binds pre-refactor `99f4f7319`
and final BD2 native releases, 33 frozen CCA and 12 cached Silesia inputs,
FAST/default/BEST, four encoder threads, five repetitions. Initial execution
uses four datasets concurrently, each capped at 2.9 GB RAM / 900 MB temporary
space, zero swap. Silesia remains gated on all CCA results. Scaling/profile/PGO
experiments remain separate; no new throughput or ranking claim is made yet.

Initial v1 restart stopped on four wrapper launch failures before encoding.
The command transport is corrected and validated with actual constrained
children; new v2 plan retains the same releases/inputs/settings. The RAM ceiling
is explicitly page-aligned at 2,899,996,672 bytes per job. Failed probes remain
separate evidence, never performance observations.
