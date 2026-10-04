# Native RC foundation checkpoint — 2026-10-04

**Release candidate not ready; benchmark remains stopped.** This checkpoint
preserves implementation progress and failed as well as passing checks. It is
not full-engine qualification, a public release or a compression record.

## Current source

The baseline remains `97fea6189`, reconciled from the qualified native snapshot.
No third-party source was modified. The following CIX-owned additions are under
qualification; the maintained Python code remains a reference outside the
standalone runtime and future distribution allowlist.

| Area | Present at this checkpoint | Still required |
| --- | --- | --- |
| Library context | Rust Read/Write and buffer entry points; caller limits, cooperative cancellation/deadline scopes and worker context inheritance; CLI signal state excluded from native-library scopes | Full extraction from the CLI implementation, stable C/context/incremental ABI, complete error/resource contracts and installed SDK consumers |
| Exact arithmetic | Checked varints, big integer rank/composition, Fenwick frequencies and arithmetic interval coding with reference/small exhaustive checks | Complete route/frame parity and final resource qualification |
| Record ordering | Count-conditioned streams, permutation rank blocks and framing primitives | Complete retained column/fixed-record models and native dispatch |
| Address relations | Validated object discovery, constraints, fields, GOT transforms and historical envelope helpers; golden choice-code bytes; corrected historical mode-0 inverse | Remaining pointer/section specialists, complete object/frame reference fixtures, model allocation budgets and end-to-end backend integration |
| Graph residuals | Fixed-width coordinate extraction/restoration, graph/sequential residuals, canonical-field checks and mixed line-ending preservation | Complete palettes, hydrogen constraints, historical framing and dispatch |
| Strided values | Strict extent recognition and signed scalar mapping | Complete retained grid representations and frame qualification |
| Volume lifting | Volume modes, finite-width residuals, axis layouts and bounded multiscale shape operations; explicit codec callbacks | Actual JXL bridge/dependency build, CIXI1 migration constraints and cross-decoding all retained physical frames |
| PAQ boundary | Four variant bridge sources and explicit same-executable-worker contract; SDK rejection; bounded error text and exact Unix argument bytes | Build/link/load qualification, unchanged dependency closure, worker supervisor/environment/resource enforcement and platform paths |
| Analysis gating | CIX-owned CXX runner accepts the authenticated stopped-benchmark state while retaining idle/source/lease guards | Actual CXX scan, final integrated-source Sonar/Clippy and dead-code disposition |

The current `core::codec` still includes the existing CLI implementation below a
library module. This is a reusable-entry foundation, not proof that RC02's full
library-first extraction is complete. The full-engine modules are not admitted
to ordinary CLI selection. Successful primitive tests cannot substitute for
archive-only restoration through the real integrated codec backends.

## Naming and distribution

All five newly ported domain-labelled modules use mathematical/process names:
`structured_frames`, `record_ordering`, `address_relations`, `strided_values`
and `volume_lifting`. The new coordinate helper is `graph_residuals`.
[Source naming](source-naming.json) records the mapping and exact preserved
research moves; [the audit](NAMING-AUDIT.md) checks the broader source layout.
No old module declarations/imports remain in current production candidates.

Names do not establish corpus independence. Recognition still requires
validated input-derived structure. Standard-format identities, external codec
names, wire bytes and provenance remain precise. Frozen historical snapshots
retain their original filenames. The old unexported oracle and its test were
moved byte-for-byte to `experiments/research_oracle`, outside automatic production
test discovery. Their hashes are in the naming receipt. A final explicit public
source/install allowlist is still required; no public repository was created.

## Evidence and failures

Every job has immutable input hashes, its actual command and resource receipt.
The original snapshots remain unchanged, verified in
[snapshot-verification.json](snapshot-verification.json). No failed run was
rewritten as a success.

| Job | Result and disposition |
| --- | --- |
| check-v1 | Launcher failed because PATH selected snap Cargo, which could not run in the constrained service. No codec check completed. |
| check-v2 | Same source as check-v1, direct toolchain path; exposed missing imports/constants in volume code. |
| check-v3 | Corrected source; exposed an old integration test importing parallel implementation without its limits module. |
| focused-v1 | Exposed the unexported research oracle left under automatic test discovery. Both old files preserved outside shipping/test discovery. |
| focused-v2 | All-target compilation, 11 full-engine primitive tests, 4 native-context tests, 3 PAQ descriptor tests, 7 pipeline tests and 6 CXX guard tests passed. |
| focused-v3 | New GOT/graph source failed compilation on two explicit type/error-conversion issues; no tests ran. |
| focused-v4 | All-target compilation passed; 19 primitive tests passed and 2 test assumptions failed. One expected the legacy zero-bit arithmetic padding to be rejected; the other accidentally joined CR and LF across an empty header line. Both test inputs corrected; decoder behavior was not tightened to hide the mismatch. |
| focused-v5 | All-target compilation and all 140 library tests passed, with zero failures/ignored tests. Current 133-file source matches the tested immutable snapshot. |

The two GOT golden cases include repeated shared contexts, so adaptive and static
arithmetic outputs differ. The [reference receipt](got-reference-vectors.json)
binds the frozen Python source hashes. These are generated tiny fixtures,
not evaluation corpus data or a new benchmark.

The CXX guard's six passing tests do not establish C++ analyzer coverage. Vendor
compiler warnings remain visible. The C++ bridges have not been compiled by
Cargo; all-target Rust compilation does not qualify their ABI or native linkage.
The separate [JXL build plan](JXL-BUILD.md) records actual dependency and API
requirements rather than treating a Python-wheel library as an installed SDK.

## GPU opportunity disposition

[The GPU review](../2026-10-04-gpu-cuda/OPPORTUNITIES.md) records current source,
primary references, local device metadata and additional lossless methodologies.
No GPU kernels, installations or benchmark ran. A pinned isolated BWT parity
specification is prepared. GPU speed, a smaller CIX archive and exhaustive limits
of possible compression are not established. Conditional GPU requirements do
not silently become required RC implementations or justify a benchmark restart.

## Continuing gate

The coordinator's 55-row requirements register remains authoritative and open.
The immediate implementation direction remains completing the native full-engine
ports and actual codec-library integration, followed by SDK/adapters, installation,
final quality and independent readiness review. No source feature is waived by
this foundation checkpoint. New benchmarking follows that review, not this log.

The final [check summary](check-summary.json) binds the actual result and log
hashes. The job used 252.429 seconds wall time and 280.590 CPU seconds under
four physical cores, no swap and a 6 GB host limit. Sampled cgroup memory reached
1,664,053,248 bytes (a lower bound, not a true process peak); temporary files
peaked at 1,157,203,097 bytes. These are correctness-check resource observations,
not compression-throughput benchmark results.
