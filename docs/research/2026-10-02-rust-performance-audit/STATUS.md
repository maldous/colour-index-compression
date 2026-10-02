# Performance audit status

Checkpoint source: `40d3520db63a7d54526cb22430b769e77cf601c9` on
`research/silesia-competitive`. This is an interim checkpoint, not completed
Sonar remediation or a final corpus qualification. The previous private push was verified at `c27406598`; subsequent completed
changes are queued for push. Repository privacy and disabled Actions were
read back again on 2026-10-02 before the next push.

## Retained implementation changes

| Change | Measured evidence | Compatibility |
|---|---|---|
| Count-range avoids computing a discarded permutation rank | 7.11× forced-route Canterbury CPU improvement; a distinct 4 KiB kernel improved 1.48× | Identical complete archive; necessary ranks remain BigUint |
| Exact colex recurrence with bounded cancellation checks | Strong/weak/absent cases; old large strong case exceeded its budget | Identical deterministic outputs; no fixed-width rank truncation |
| Shared immutable fixedmix stretch table | Corrected six-pair screen: encode 2.48%, decode 2.27% faster on the declared forced-mixture input | Identical complete archives and fresh native restores |
| Borrowed PPM context lookup | Controlled kernels: approximately 3–34% encode and 3–33% decode mean improvement depending on input; allocation events reduced | Identical payloads and fresh cross-decoding; not a general CLI speed claim |
| Fixed PPM eligible scan without temporary vectors | Controlled fixed order-3 kernels: approximately 16–30% lower encode means; lower allocated bytes and events | 32 byte-identical payload cases and fresh cross-decoding; decoder path unchanged |
| Checked payload arithmetic and varints; PPM rescale spelling | Boundary, overflow, malformed-input and captured payload tests | Valid payload bytes unchanged |
| Streaming setup/worker/output helpers | Independent review, G1/G2 byte identity, idle and slow-consumer pipe checks | Framing, ordering, model behavior and resource values preserved |

Evidence is in `count-range/`, `colex-rank-0e8685/`, `fixedmix-table/`,
`ppm-borrow/`, `ppm-eligible/`, `ppm-rescale-ceil/`, and `gstream-refactor/`.
Reviewed helper refactors also cover numeric coding and CLI encode options.
The numeric fixture now exercises real decoder modules rather than rejecting
stubs; all 18 affected optimized example tests passed.

## Qualification and open work

| Requirement | Current evidence / next work |
|---|---|
| Pre-refactor versus current matched CLI | Three paired automatic BEST grammar runs: 14.2% lower mean wall time for combined `8865bfbcc`; wall-time paired confidence interval includes zero. One small input does not establish general improvement. |
| Regression tests | Combined `8865bfbcc` passed 359 test executions; newer boundary and PPM targeted tests passed. Combined `9214e2f8b` exposed a rejecting numeric example stub, now repaired. The direct optimized `40d3520db` all-feature library/binary/integration/example suite exited zero; the separate Criterion smoke also exited zero. Reviewed raw logs, exit receipts and artifact metadata are retained in `combined-40d-validation/` (598 repeated test executions, not unique tests). |
| Profiling | DEFAULT Kennedy and BEST grammar perf recordings identify BigUint division, PPM, BWT and mixing work. Full cache/bandwidth, scheduling, lock and I/O attribution remains open. |
| Allocations | Encoder-only count-range DHAT and controlled PPM kernel DHAT completed. Fixed PPM eligible-vector removal is retained with 80 cgroup-read-back ABBA processes and raw allocation receipts; no whole-CLI improvement is inferred from kernels. |
| Streaming latency | Actual idle producer and slow-consumer pipes produced compressed and reconstructed bytes before EOF, including a root no-swap 128 MiB repetition. A 256 MiB raw-route pipe restored exactly inside a read-back 64 MiB aggregate cgroup with swap disabled, bounded relay and slow-consumer backpressure. This is a correctness/resource control, not a selector or persistent-history performance result. |
| Scaling | A 120-cell DEFAULT G1 screen completed. One-thread restores passed; explicit two/four-thread decoding is rejected. All timing rows are unqualified because the executed harness source identity was not retained. Native receipts preserve the failures; a direct-child status supervisor fixes future experiments under a new identity. No qualified decoder scaling curve is claimed. |
| Persistent history versus independent blocks | G1 is already independent; its reset flag cannot establish this tradeoff. Genuine persistent-format comparisons remain open. |
| Compiler / PGO | Portable/native, LTO/codegen and held-out PGO screens exist. PGO improves some encode screens but regresses decode; no build-profile change retained. Some historical resource readbacks were not retained, so those results remain screens. |
| Sonar | Corrected compact Clippy import exposed remaining findings. The corrected `40d3520db` scan has 26 native complexity findings, down from 30; its reviewed raw evidence packet is retained in `sonar-40d-corrected/`. Unsupported imported rules and raw/imported visibility differences remain recorded. No zero-warning claim; disjoint cleanup continues. |
| Full CCA gate then Silesia | Paused until reviewed cleanup and a new immutable release are complete. Corpus execution policy remains four datasets concurrently, four threads each. |
| Default thread/block recommendation | Pending qualified scaling, memory and history comparisons. Existing defaults remain. |

No dataset acquisition, Hutter restart, GitHub Actions, new ranking or public
Site result is authorized by these kernel and implementation measurements.
Recorded losses, failed attempts and limitations remain part of the evidence.
