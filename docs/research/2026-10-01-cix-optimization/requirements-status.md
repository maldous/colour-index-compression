# CIX optimisation programme: current requirements status

Date: 2026-10-01. This is a status record for the Rust implementation and its local qualification evidence. It does not claim a complete codec survey, global BEST search, Silesia ranking, or universal performance.

## Current implementation and verification

The qualified source revision is `ee6b4396df760d19005c4e0800783fef58d52334`. The latest release evidence ran 178 tests with zero failures in 22 groups; four tests were filtered, including an expensive cross-decode fixture whose unchanged-chain evidence is separately identified in [`latest-release-tests.summary.json`](adversarial-parallel-evidence/latest-release-tests.summary.json).

The CIXG streaming path has a bounded ordered block pipeline. Independent blocks encode concurrently, retained work is charged against one global memory-permit budget, completions emit in input order, and a slow writer backpressures reader admission. Worker cancellation, deadline checks in expensive codecs, format gates, decoder frame checks, and footer integrity checks are reviewed in [`adversarial-parallel-review.md`](adversarial-parallel-review.md). The previous statement that CIX has no frame/block parallelism is incorrect: CIXG has bounded parallel independent-block work. Ordered output and stateful paths still constrain where parallelism is legal.

The recurrence correction is **experimental fixed-mix v3**. It preserves legacy v2 decoding and has malformed-input and causal-state fixtures, but it is not a general automatic-selection result or a promoted DEFAULT/BEST model.

The local native ABI smoke is complete. The Unix shared library accepted irregular partial reads/writes, round-tripped a synthetic 131,071-byte input in separate encoder/decoder processes, and rejected exercised error paths. The host lacked the Squash development package, so this is neither a Squash-plugin qualification nor a throughput/ratio claim. See [`native-ffi-final-smoke.md`](native-ffi-final-smoke.md).

## Measured profile and implementation results

The ordinary profile proof uses the CLI without strategy overrides. In the two-repetition CIXG profile qualification on its frozen 1 MiB development input, FAST produced 476,034 bytes, DEFAULT 407,643 bytes, and BEST 354,023 bytes; each pair fresh-decoded exactly. Those results quantify that input and revision only. Selector logs show bounded parallel block work and no reported memory or budget skips. See [profile evidence](adversarial-parallel-evidence/cix-profile-qualification/profile-summary.json).

The later ABBA DEFAULT confidence-v2 comparison used the input-derived PPM admission policy at revision `ee6…`. The candidate produced 381,955 versus 407,643 bytes on the frozen development range and 397,078 versus 423,660 bytes on the frozen replication range, with two candidate and two control runs per range and fresh exact decode. Candidate encode/decode wall times were also lower on those cells; the evidence records wall, CPU, and RSS rather than claiming universal dominance. See [`cix-default-confidence-v2/default-model-summary.json`](cix-default-confidence-v2/default-model-summary.json).

The parallel qualification confirms deterministic 354,023-byte archives for candidate-parallel and block-parallel plans. On its frozen 1 MiB input, the two thread-4 block runs took 2.57 and 2.56 s encode wall time versus 8.16 and 8.11 s for the thread-1 block runs. This is a local controlled result. The fixed-mix fixed-scratch comparison preserved its 52,400-byte archive across all four cells; resource differences were small on that 128 KiB forced-route control. The prior run's control identity remains with errata; future mixer qualifications bind every control binary to its own immutable receipt.

## Requirement matrix

| Requirement family | Current state | Evidence and remaining work |
|---|---|---|
| Exact lossless native encode/decode, framing, checksums, streaming | Implemented and locally tested | CIXG/CIXG2 frame/footer validation and bounded pipe fixtures exist. Broader latency, RSS, long-stream and persistent-history measurements remain. |
| Bounded multi-CPU use | Implemented for independent CIXG blocks | Ordered pipeline, one memory ledger, capped workers, cancellation and backpressure are controlled. Stateful/model-dependent routes need reset boundaries or measured sequential policy. |
| FAST, DEFAULT, BEST automatic effort | Implemented as bounded policies | Normal CLI leaves strategy dimensions automatic. BEST is finite and resource-bounded, not the whole legal encoding space. |
| Dynamic representation/backend/package/segmentation choice | Partial | Route/backend candidates and exact materialisation exist in declared universes. Automatic CIXM6/package competition, arbitrary transform stacks, segmentation, all parameter products and external-codec comparison remain incomplete. |
| Adaptive prediction and recurrence | Partial / experimental | Adaptive, PPM, fixed/expert mixing and recurrence-v3 components exist. Sparse variable-order mixing, calibrated context mixing, recurrence selector integration and ablations remain queued. |
| Structural representations and exact rank coding | Partial | LZ, runs, composition BigUint ranks, BWT/MTF, stride, phrases, predictor and native routes exist. Conditional composition/table coding and transform-composition search remain open. |
| Substream coding | Partial | Range/count-range and Huffman are available. Matched ANS/FSE/universal-integer comparisons and native implementations remain open. |
| Squash and other-inventory methodology coverage | Mapped, not fully implemented | [`coverage-matrix.md`](coverage-matrix.md) distinguishes implementation, partial principle coverage, backend-only and absent methods. Codec-specific parsing/model choices need measured qualification. |
| ZPAQ lead | Reproduced, not solved | Matched ZPAQ result and wrapper negative are in [`results.md`](results.md). Native context-mixing, recurrence and periodic-model ablations remain work, not inferred wins. |
| Native FFI | Host smoke completed | Exported ABI round trip and error paths are verified. Squash loading/plugin integration remain unqualified. |
| Full generic qualification and Silesia | Not complete | Canterbury/Calgary/Artificial gates precede renewed Silesia claims. Existing Silesia records remain historical/frozen. |

## Benchmark rule

Every new experiment must freeze input hash/range, binary and source identity, exact CLI, complete archive accounting, fresh decoder process, threads and resource caps before dispatch. It must report failures and omissions. Immutable receipts remain historical evidence; they are not rewritten when adapters or current defaults change.
