# Performance audit status

Checkpoint source: `9214e2f8b80a16009986af56dd3de242fd26651e` on
`research/silesia-competitive`. This is an interim checkpoint, not completed
Sonar remediation or a final corpus qualification. The private remote SHA was
verified after pushing; repository Actions remained disabled.

## Retained implementation changes

| Change | Measured evidence | Compatibility |
|---|---|---|
| Count-range avoids computing a discarded permutation rank | 7.11× forced-route Canterbury CPU improvement; a distinct 4 KiB kernel improved 1.48× | Identical complete archive; necessary ranks remain BigUint |
| Exact colex recurrence with bounded cancellation checks | Strong/weak/absent cases; old large strong case exceeded its budget | Identical deterministic outputs; no fixed-width rank truncation |
| Shared immutable fixedmix stretch table | Corrected six-pair screen: encode 2.48%, decode 2.27% faster on the declared forced-mixture input | Identical complete archives and fresh native restores |
| Borrowed PPM context lookup | Controlled kernels: approximately 3–34% encode and 3–33% decode mean improvement depending on input; allocation events reduced | Identical payloads and fresh cross-decoding; not a general CLI speed claim |
| Checked payload arithmetic and varints; PPM rescale spelling | Boundary, overflow, malformed-input and captured payload tests | Valid payload bytes unchanged |
| Streaming setup/worker/output helpers | Independent review, G1/G2 byte identity, idle and slow-consumer pipe checks | Framing, ordering, model behavior and resource values preserved |

Evidence is in `count-range/`, `colex-rank-0e8685/`, `fixedmix-table/`,
`ppm-borrow/`, `ppm-rescale-ceil/`, and `gstream-refactor/`.

## Qualification and open work

| Requirement | Current evidence / next work |
|---|---|
| Pre-refactor versus current matched CLI | Three paired automatic BEST grammar runs: 14.2% lower mean wall time for combined `8865bfbcc`; wall-time paired confidence interval includes zero. One small input does not establish general improvement. |
| Regression tests | Combined `8865bfbcc` passed 359 test executions; newer boundary and PPM targeted tests passed. Full combined `9214e2f8b` validation and release packaging are running separately. |
| Profiling | DEFAULT Kennedy and BEST grammar perf recordings identify BigUint division, PPM, BWT and mixing work. Full cache/bandwidth, scheduling, lock and I/O attribution remains open. |
| Allocations | Encoder-only count-range DHAT and controlled PPM kernel DHAT completed. PPM eligible-vector removal is a separate measured candidate under investigation. |
| Streaming latency | Actual idle producer and slow-consumer pipes produced compressed and reconstructed bytes before EOF, including a root no-swap 128 MiB repetition. Substantially-larger-than-budget input qualification remains open. |
| Scaling | A 120-cell DEFAULT G1 screen completed. One-thread restores passed; explicit two/four-thread decoding is rejected. Raw native exit codes and wrapper/control provenance are being reviewed before integration. No qualified decoder scaling curve is claimed. |
| Persistent history versus independent blocks | G1 is already independent; its reset flag cannot establish this tradeoff. Genuine persistent-format comparisons remain open. |
| Compiler / PGO | Portable/native, LTO/codegen and held-out PGO screens exist. PGO improves some encode screens but regresses decode; no build-profile change retained. Some historical resource readbacks were not retained, so those results remain screens. |
| Sonar | Corrected compact Clippy import exposed remaining findings. Current scan also reconciles relative paths and unsupported imported rules. No zero-warning claim; disjoint cleanup continues. |
| Full CCA gate then Silesia | Paused until reviewed cleanup and a new immutable release are complete. Corpus execution policy remains four datasets concurrently, four threads each. |
| Default thread/block recommendation | Pending qualified scaling, memory and history comparisons. Existing defaults remain. |

No dataset acquisition, Hutter restart, GitHub Actions, new ranking or public
Site result is authorized by these kernel and implementation measurements.
Recorded losses, failed attempts and limitations remain part of the evidence.
