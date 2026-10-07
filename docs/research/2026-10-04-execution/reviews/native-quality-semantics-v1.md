# Native quality semantics review v1

Date: 2026-10-05
Scope: read-only review of uncommitted Rust lint and portability edits against `HEAD`. No build or test was run.

## Result

No actionable correctness regression was found in the reviewed edits. The changes group existing values, replace equivalent integer/container idioms, or extend explicitly bounded platform behavior. This is source review only; it does not qualify any platform or replace focused checks.

| Area | Review finding | Required focused qualification |
|---|---|---|
| Fixed-width `.as_chunks()` conversions | The affected paths retain an exact byte-length guard before using the fixed-width branch: conditional values checks divisibility, grid context checks `n * width`, and spatial/JXL paths check sample alignment. Their `as_chunks::<N>().0` therefore has no discarded tail on an accepted input. The fallback width branch remains an error. | Existing malformed/truncated and fixed-width round trips, including 4- and 8-byte conditional/grid values and 2-byte image samples. |
| PAQ request grouping | `PaqOptions` carries exactly the former `variant`, operation, level, LSTM layer, and joint-discount fields. Encode still selects `Encode`; bounded decode still selects `Decode`; construction of `PaqWorkerRequest` preserves all assignments. | PAQ encode/decode worker contract plus cancellation, deadline, and joint-discount route tests. |
| Hydrogen topology grouping | `HydrogenTopology` only packages the same atom count, parents, adjacency, and type vectors returned by `hydrogen_topology`. Candidate selection still borrows the same vectors and uses the same coordinate prefix/slot mutation ordering. | Historical SDFH representations 0–3 byte-vector assertions and exact decode tests. |
| Dictionary C ABI buffers | `OperationBuffers` groups the five former input/output pointers and lengths. Region overlap validation, `written = 0` initialization, memory reservation, input copy, and output write use the same fields and order. The added safety documentation does not change the ABI. | Existing C dictionary create/train/encode/decode/overlap/short-output contract tests. |
| Shared dynamic provider loader | Providers still validate absolute regular paths, resolve the same pinned symbols, verify versions, and hold a handle for provider lifetime. Unix retains `RTLD_NOW | RTLD_LOCAL`; Windows now requires an absolute path and limits dependency lookup to the selected DLL directory plus System32. | Target-native staged bridge load, missing-symbol/version rejection, sibling dependency resolution, and unload checks on Linux, macOS, and Windows. |
| Standard-input wrapper and defaults | Unix stdin remains a duplicated file descriptor and uses poll-aware paths. Non-Unix now reads `Stdin` directly for blocking streams; timed flush remains rejected before a blocking read. The BEST default-memory change is an explicit profile policy, while explicit `--memory` continues to override it. | Windows redirected stdin named/pipe behavior, rejection of timed flush on that path, and CLI profile/default-memory boundary tests. |

## Remaining constraints

- The current source still does not package or qualify full-engine runtime providers on macOS or Windows.
- PAQ worker execution remains Linux x86-64/AVX2 and Unix-private-root dependent.
- Source review cannot prove Windows loader flags, platform toolchain behavior, or stdin-handle behavior. These require actual target execution.

## Review notes

The `.as_chunks()` edits are safe only because their surrounding validation remains part of the acceptance condition. Future callers must not copy the pattern into a path that accepts trailing partial elements. No source change was made by this review.
