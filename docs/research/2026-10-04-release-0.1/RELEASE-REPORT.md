# CIX 0.1 private release report

**Status:** The named research, source-quality, performance, final qualification, package-artifact, and notice-qualification screens are complete. The package-version benchmark is running; the private portal is locally complete and will receive its authorized owner-private deployment after terminal results. This is private evidence, not a public release claim.

## Decision

No measured compression opportunity justifies a new production codec route for v0.1. The omitted native predictive leads are resolved: corrected FixedMix recurrence-v3 loses to v1, and native PPM does not expose a normalized original-byte distribution for predictive mixing. The numeric structural-composition closure at `20e18503b` remains in force.

This is a finite evidence audit. It does not prove an entropy, Kolmogorov, or universal-compression limit. It establishes only that the audited mechanisms, with their fixed source, inputs, and complete-cost rules, do not supply a v0.1 promotion candidate.

## Predictive-information closure

The original CPI1 audit found a small causal gain in its frozen 28-expert set, but it missed the material gate. Its hindsight oracle must remain labelled **HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY**: it selects after seeing the actual byte and cannot be decoded without additional information. CPI1 null controls show that oracle gaps can arise from selection advantage and calibration variation rather than exploitable causal information.

`RELEASE-PREDICTIVE-1` tested the omitted native signals on 49,152 held-out bytes. FixedMix v1 is the best native expert at 139,280.337288 ideal bits. Recurrence-v3 N1 and N2 are worse by 0.006298 and 0.006361 bits per byte. The selected Bayesian combination improves the best single expert by only 0.000256 bits per byte, below both gates (>0.05 bits/byte and >1% strongest-pool improvement). It fails.

Native PPM's raw and normalized held-out coding-path diagnostics are both 155,099.386741 bits: the held-out reachable-byte mass is one within rounding, so the paid valid-mass correction is approximately zero bits. CPI1 nevertheless demonstrated subprobability on other reachable states. The frozen follow-up therefore keeps PPM separate from the oracle and causal pool pending a global compatibility normalization contract. There is no held-out normalization gain. This classifies the interface; it does not say PPM cannot compress an archive.

Evidence: [CPI1](../2026-10-04-predictive-information/REPORT.md) and [RELEASE-PREDICTIVE-1](PREDICTION-RESULTS.md).

## Physical cost check

The native cost screen isolates existing substreams, not complete archives. Ideal-loss or payload values must not be advertised as archive savings.

| Native substream | Total bytes | Metadata bytes | Arithmetic bytes | Result |
| --- | ---: | ---: | ---: | --- |
| FixedMix v1 eta 6 | 17,466 | 49 | 17,417 | Best existing signal. |
| FixedMix v3 N1 eta 6 | 17,590 | 133 | 17,457 | 124 bytes larger than v1. |
| FixedMix v3 N2 eta 6 | 17,588 | 133 | 17,455 | 122 bytes larger than v1. |
| PPM order 3, escape 1 | 19,456 | 62 | 19,394 | Coding-path diagnostic only. |

V3 adds payload and metadata cost. Its N1 finite-precision, termination, and padding diagnostic is 66.089 bits versus 55.663 bits for v1. These are physical native-substream losses, not complete CIX archive comparisons. [Cost evidence](cost-results.json) binds the source and inputs.

## Other compression opportunities

[OPPORTUNITIES.md](OPPORTUNITIES.md) and [opportunities.json](opportunities.json) retain the complete mechanism ledger and second-pass v0.1 decisions. Transform composition, paid structural descriptions, lane/segmentation extensions, numeric layout/composition, new parser/coder frames, and neural or external-model proposals are either negative on their declared evidence, already covered by current routes, or future research requiring a new format without a measured release signal.

The physical numeric-composition result remains negative: it reduced internal payload by 4 bytes but added 29 description bytes, leaving the incumbent 25 bytes smaller on the decisive fresh slice. Do not reopen it through R4, R6, or Q1-Q4.

## Performance and source quality

The finite performance screen selects portable B0: `opt-level=3`, fat LTO, one code-generation unit, and `target-cpu=x86-64`. It does not select PGO, ThinLTO, host-native code, or jemalloc. PGO's one held-out 1.77-second observation overlaps later unchanged-B0 variation (1.83 seconds); jemalloc matches system-allocator CPU time and raises RSS from 7,244 KiB to 9,216 KiB.

On the frozen 1,029,744-byte Kennedy input, all completed CIXG1 scaling points restore and produce the same 70,536-byte archive. Block workers 1/2/4 observed 1.91/1.11/0.65 wall seconds; candidate workers observed 1.89/1.08/0.71 seconds. These are configuration-scoped observations, not a shipped-default, decoder-parallelism, or general-throughput claim. The M6 screen exhausted its 300-second budget before a complete archive and is unranked. [Performance results](PERFORMANCE-RESULTS.md) records the limits.

The accepted throughput changes are the exact-prefix prune and T1's discarded-histogram avoidance; no other optimization is selected. The prune preserved selected archive bytes in both matched controls: grammar BEST observed 10.14/10.17 user/wall seconds before and 10.22/10.24 after, while the Kennedy constrained predictor observed 1.18/1.19 before and 1.07/1.08 after. These one-off CPU rows establish equivalence and omission accounting, not a general speedup. Release-source cleanup removed research-only exports and Rust dead-code suppression while retaining decoder modules and optional Squash C ABI. The final tree is `bd28975a504abbeb011d2aaba36224af6b5c7f3fa844f491c224166750cab1e7`; its release build, 115 library tests, 4 CLI smoke tests, 7 streaming-pipe tests, warnings-denied Clippy, and Sonar v2 pass with zero Rust diagnostics/issues and an `OK` quality gate. The clean result excludes vendored C/C++ warning scope. Final qualification also passed package build/runtime, shared-library ABI, stream, and SquashFS checks. [Quality closure](QUALITY-CLOSURE.md) defines that boundary.

The shipping successor adds a complete 32-crate Rust notice bundle and only the documentation/install-rule changes needed to carry it. `dependency-notices/amendment.json` verifies that all 90 protected runtime/build files are byte-identical between the frozen export and successor. Notice qualification v2 checks the same notice hash in staged source/binary artifacts and package forms; it is a legal-distribution qualification, not a claim about third-party source quality beyond the documented scope.

## Initial corpus qualification

The complete Canterbury/Calgary/Artificial gate passed: 84 physical profile cells (87 logical memberships), all exact restores with successful resource-control receipts. [Gate results](CCA-GATE.md) contain the completed corpus totals and timing scope. The broader immutable local-data queue remains active. [Inventory arithmetic erratum](inventory-total-erratum.json) corrects three stale display totals without changing any frozen input or measurement.

## Root-owned evidence slots

| Deliverable | Required fill before accepting a candidate |
| --- | --- |
| Successor distribution and package artifacts | **Complete.** Shipping source is `/home/user/src/cix-0.1-distribution`; packages are under `/home/user/src/cix-0.1-artifacts/distribution-v2/packages`. Notice qualification v2 passed with exact binary hashes, staged source build/install/uninstall, DEB, RPM, DSC, and binary-tar notice-hash checks. The retained v1 RPM packager failure is superseded by this corrected v2 result, not erased. |
| Package-version benchmark | **Running.** The frozen plan contains 267 profile cells across 89 physical / 90 logical assets; 85 cells are verified at this checkpoint under four cores and 10 GiB. Two initial BEST timeouts are retained; the corrected native allowance is at least 900 seconds and the finite hourly continuation is configured. Fill FAST/DEFAULT/BEST complete archives, exact restores, resource receipts, dataset identities, and comparator scope when terminal. |
| Public-record table | Original source links plus matched/not-directly-comparable labels; no inferred rank. |
| Private portal review | Local portal is complete. Populate final charts only from the terminal benchmark, then the owner may choose private publication; it is currently not deployed. |

## Exactly one evidence-selected next action

**Conduct a private candidate review after, and only after, the immutable package artifact and its package-version benchmark report are complete.** The review should accept the frozen B0 candidate or identify a specific missing artifact, benchmark, or compatibility receipt. It must not reopen closed compression branches or add a new codec route.
