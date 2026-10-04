# Analysis checkpoint closure review v1

Date: 2026-10-05
Scope: staged analysis evidence and the compiler-context/header-canary evidence only. This is not a release or product-quality acceptance.

## Review method

This was a read-only inspection of the staged path list, line counts, staged patch whitespace check, result/receipt JSON, size inventory, and a pattern-based secret-name/content screen. It did not run a build, scan, test, or change the index.

The index currently contains 985 paths and 4,084,664 added/deleted lines. Most of that volume is analysis evidence rather than product source. The two retained CXX full scans alone occupy about 59 MiB (`scan-v2`) and 63 MiB (`scan-v3`). The largest individual artifacts are the raw Sonar issue responses: each PAQ `issues.json` is about 9.6--10.1 MiB and `native-vendor/issues.json` is about 8.4 MiB.

## Result and resource evidence

`sonar-preparation/scan-v2/result.json` is explicitly `FAILED`, with the error `analysis configuration requires correction for: ['cix-native-adapters']`. Its accounting reserved 3,994,476,544 of the 4,000,000,000-byte temporary budget while reserving only 32 MiB for evidence. It is useful failed-attempt provenance, but must not be cited as a completed or budget-qualified scan.

`sonar-preparation/scan-v3/result.json` is `SCANNED_WITH_RECORDED_FINDINGS`; all seven named projects are `SCANNED` and its producer field has an empty `analysis_gaps` list. That producer field is incomplete. The later, authoritative `scan-v3/qualification-review.json` has status `ANALYSIS_GAPS_REMAIN_NOT_CLEAN`: it explains that the producer completion classification omitted the CXX parser-recovery rule and some Cppcheck configuration errors. The first-party CIX adapter and core projects have 1,378 issues total, 65 `cxx:ParsingErrorRecovery` findings, and six Cppcheck configuration errors. The wider seven-project evidence also records parser recoveries and configuration errors for the native-vendor and PAQ projects. Thus scan-v3 is a completed indexing record with unresolved analysis gaps, not valid clean analysis.

Its accounting records 3,935,105,024 reserved bytes, including 100,663,296 bytes of evidence and a 520,093,696-byte temporary-filesystem ceiling, leaving 64,894,976 bytes of planned headroom. The slice receipt records four allowed CPUs (`8 10 12 14`), a 5 GiB memory maximum, and swap disabled. This supports the stated planned allocation for v3; it does not turn the recorded findings into a clean quality gate.

The compiler context capture is traceable to one successful qualified JXL bridge compilation. `context.json` records `/usr/bin/c++`, the recorded `-std=c++17` invocation, source and compile-database hashes, 462 raw compiler macros including `__cplusplus 201703L`, and the system include paths. It explicitly says it does not infer header-guard macros and limits its scope to that C++ context. Its recorded command uses an empty standard input and a read-only, no-network bubblewrap call. That is adequate evidence for this one compiler context; it must not be applied to unrelated C, kernel, or platform toolchains. The corresponding `header-context-v1` result is negative: applying that actual context to the unchanged public JXL header leaves all 13 parser recoveries. It is preserved diagnostic evidence, not qualification.

The later `cppcheck-header-canary-v9` is a different, narrow result. Its script selects at least five GIO/SevenZip compilation entries, preprocesses them into analyzer copies, and reports a zero child exit. The job specification caps it at two CPUs, 3,000,000,000 bytes of memory, 4,000,000,000 bytes of temporary space, and 300 seconds. The receipt records 4.57 seconds elapsed, 4.54 CPU seconds, and a 3,561,862,059-byte temporary peak. It also expressly labels its 215,285,760-byte cgroup high-water value as a lower bound, with true process peak unavailable. Therefore this canary demonstrates that its selected headers/configuration were analyzable under the recorded constraints; it does not independently prove a true memory peak below the job cap or general CXX coverage.

## Checkpoint hygiene

No staged path matched common generated-tree names such as `target`, `node_modules`, `.scannerwork`, `__pycache__`, or `.pyc`. A targeted content screen did not find private-key blocks, AWS access-key forms, GitHub token forms, or Slack token forms. Broader word matches are confined to source/tool text and expected server logs, so they are not evidence of a credential disclosure. The evidence does contain absolute local paths, compiler command lines, package/include locations, and frozen tool/source copies. Those are necessary provenance for a **private** research checkpoint, but make this evidence unsuitable for publication or a public source export without a separate redaction review.

`git diff --cached --check` reports trailing whitespace or extra blank lines in raw compiler/log evidence and one review. Those bytes are part of the preserved tool output and are not a source-quality defect or a reason to normalize the raw evidence. A checkpoint policy that requires a whitespace-clean index needs an explicit raw-evidence exception, rather than modification of the receipts.

The failed v2 scan retains approximately 60 MiB of full raw output beside v3. Its PAQ and vendor issue bodies are near-identical in size but have different hashes, so blind file-level deduplication is not justified. Retain all v2 and v3 raw bodies: v2 is required failed-attempt evidence, and v3 is the completed scan record. They are intentional, necessary private evidence rather than disposable generated artifacts.

## Checkpoint disposition

The evidence is safe to checkpoint as private analysis material, with the labels kept explicit: v2 is failed; v3 completed indexing but has unresolved analysis gaps; and `header-context-v1` is a negative 13-recovery result. The context capture and v9 canary are bounded, narrow supporting evidence. The checkpoint is not safe to use as a claim of a clean scanner result, valid first-party analysis, a complete CXX analysis, a measured true process-memory peak, or a public artifact without redaction review.
