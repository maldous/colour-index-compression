# Current local implementation gaps v1

This is a read-only release checkpoint after the recorded CXX analysis gate.
It separates a scoped implementation or qualification result from coordinator
acceptance. It does not change the requirements ledger, schedule work, run a
build, scan, test, or benchmark, or authorize a Silesia run. Benchmark status
remains **HOLD** and third-party code remains untouched.

## What the current receipts already establish

The local picture is materially narrower than “all 55 rows are open.”
`native-regression-v3` passed its frozen format, warnings-denied all-target
Clippy, binary build, installed PAQ/JXL dispatch, scheduler and PAQ supervisor,
and named C ABI/dictionary/CLI/resource/stream/window integration checks. Its
scope is recorded in
[`receipt.json`](../jobs/native-regression-v3/receipt.json), not a new whole
release acceptance. `selection-override-contract-v1` records the scoped RC07
correction and 22 focused checks; the coordinator review marks that source
finding closed at its scoped level. `codec-hosts-v8` passed the pinned
Squash0.8 buffer, stream and custom-splice contract, while the filesystem
checkpoint records the private-ID SquashFS profile, VM and userspace reader
scope. None of those receipts should be repeated merely because final
acceptance is pending.

The completed CXX scan is also useful rather than clean: it indexed every
declared project and recorded findings. Its qualification review says
`ANALYSIS_GAPS_REMAIN_NOT_CLEAN`; this is the active analyzer gate, not proof
that every CIX source file is defective.

## Top five local next steps after the analyzer gate

1. **Correct the CXX analysis contexts before treating CXX findings as source
   defects.** Extend compiler-preprocessor projection only from the recorded
   compiler argv for the GStreamer, Blosc2, SquashFS-overlay and kernel
   translation units. Evaluate the documented per-file/`__global__` CXX route
   for bridge headers against the pinned analyzer. Do not inject generic macro
   definitions, hide headers, suppress findings, or edit vendor sources. The
   exact boundary and required receipts are in
   [`cxx-remaining-analysis-gaps-v1.md`](cxx-remaining-analysis-gaps-v1.md)
   and [`scan-v3/qualification-review.json`](../sonar-preparation/scan-v3/qualification-review.json).

2. **Close the remaining CIX-owned cross-platform full-engine source gaps.**
   `packaging/runtime/CMakeLists.txt` still rejects Windows staging and rejects
   full-engine companions on macOS and Windows. `src/paq_worker.rs` still
   intentionally limits native PAQ workers to Linux x86-64. Implement a
   target-specific runtime installer and only a platform worker/isolation
   contract that can be bounded and qualified; retain refusal until then. The
   existing dynamic-library and Windows SDK-layout corrections are already
   source-level progress, so this is not a request to redo them. See
   [`portable-source-gaps-v1.md`](portable-source-gaps-v1.md) and
   [`sdk-runtime-contract-v1/receipt.json`](../jobs/sdk-runtime-contract-v1/receipt.json).

3. **Make CIX-owned provider build and package inputs target-neutral where the
   current source still is Linux-specific.** The spatial bridge accepts selected
   libraries but its runtime packaging is ELF/Linux-only; PAQ bridge outputs
   need target-native provider artifacts before any non-Linux full-engine claim
   can be enabled. Preserve the already qualified Linux selected-provider
   manifest and do not edit PAQ/JXL/vendor code. The current provider inputs
   and their explicit limits are in
   [`distribution-engineering-v4/selected-provider-closure.json`](../jobs/distribution-engineering-v4/selected-provider-closure.json)
   and [`provider-binary-binding-v1.json`](provider-binary-binding-v1.json).

4. **Repair the current source-to-route evidence map before a final freeze.**
   The coordinator corrected the historical LSTM statement: the historical
   route uses PAQ v215 `-9L`, rather than a missing standalone transform. The
   existing `native-coverage` files still carry the obsolete missing-transform
   wording. Refresh that map and complete the required 41-production-module
   ownership/encoder/decoder/parity mapping against the final source. This is
   an evidence and release-manifest task, not a request for a new predictive or
   corpus experiment. Evidence: the coordinator
   [`EXECUTION-REVIEW-2026-10-05.txt`](../../2026-10-04-rc-reconciliation/EXECUTION-REVIEW-2026-10-05.txt),
   [`native-quality-semantics-v1.md`](native-quality-semantics-v1.md), and
   [`native-coverage.json`](../native-coverage.json).

5. **Prepare one final-source export and language-quality configuration only
   after the preceding source edits stop.** The Linux provider closure is an
   engineering input, not a final dependency/provenance closure; PAQ rebuilds
   have source identity but were not byte-identical to the selected binaries.
   Create the final allowlisted export, bind providers/notices/package inputs,
   then run the distinct final CXX and Rust/selected-Python analysis scopes.
   This step should not rerun predecessor checks on a mutable checkout. See
   [`final-sonar-language-scope-v1.md`](final-sonar-language-scope-v1.md),
   [`package-manager-qualification-v1/PLAN.md`](../jobs/package-manager-qualification-v1/PLAN.md),
   and [`provider-binary-binding-v1.json`](provider-binary-binding-v1.json).

## Actual external blockers, retained separately

No local source edit turns these into completed work:

| Blocker | What is needed | Evidence boundary |
|---|---|---|
| Linux ARM64, macOS ARM64/x86-64, Windows x64 | Actual target runners, builds, installed consumers and selected runtime/provider execution. Cross compilation, Wine and a synthetic SDK layout do not qualify them. | [`platform-runners-v1.md`](platform-runners-v1.md) |
| Host SDKs and registries | Pinned real SDKs/toolchains/runners and honest development identities for the promised adapters; stock/upstream acceptance only if claimed. | `RC54-sdk-runners` and `RC54-identities` in [`requirements.json`](../../2026-10-04-rc-reconciliation/requirements.json) |
| Stock SquashFS / external format adoption | The private ID 65001 filesystem result and Squash0.8 v8 contract do not qualify stock tools, arbitrary kernels, registry allocation or upstream adoption. | [`FILESYSTEM-CHECKPOINT.md`](../jobs/filesystem-evidence-v1/FILESYSTEM-CHECKPOINT.md) and `RC42-owned` / conditional upstream rules |

The next native-regression, package-manager, platform, or final-analysis run
must be scheduled by root against a new immutable source identity. The current
receipts remain evidence for their named source and scope; they are not erased
or silently broadened.
