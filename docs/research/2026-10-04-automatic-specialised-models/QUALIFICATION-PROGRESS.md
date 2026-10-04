# Integrated runtime qualification

The frozen 36-cell Silesia confirmation pass is **running** under
`qualification/silesia-confirmation-v1/plan.json`. Product source is `5d93d9f1b`;
freeze checkpoint `d026ee070` is pushed privately. The development checks below
are separate from the fresh corpus results. The live summary is derived from
individually verified cells and must remain labelled incomplete until all 36 pass.

* `integrated-dev-unit-5`: 31 focused Python tests passed. Earlier unit failures
  remain recorded: missing decoder helpers, malformed test expectations, a
  malformed ELF fixture and a subsequent indentation error were corrected.
* `runtime-quality-dev.json`: production package parses successfully; no
  unresolved local imports, research/corpus runtime coupling or silent exception
  handlers were detected by the bounded source checker. This is not a Sonar result.
* `integrated-dev-smoke-1`: caught renamed `uncix-native` being invoked without
  explicit `-d`. The adapter and native streaming delegation now specify decoding.
* `integrated-dev-smoke-2`: FAST, DEFAULT and BEST each produced an archive and
  restored the arbitrary-byte fixture through a fresh packaged CLI process.
  Every admitted trial completed. The later image comparison in this job failed
  because the test compared an archive with a `(archive, metadata)` tuple.
* `integrated-dev-image-1`: corrected tiny current-JXL comparison and fresh decode
  passed. The shared CIXV/CIXI2 candidate builds both envelopes from one current
  payload; no stored archive is used.
* `integrated-dev-specialists-1`: all 15 actual-backend fixture checks passed with
  fresh-process archive-only decoding: chemical geometry/hydrogen, database
  constraints/remaining-count/fixed columns, grouped scientific grid, executable
  GOT/pointer/section/joint discount, filtered modes 1/2, PAQ v215/v216 -8 and
  v215 -9L. These tiny generated fixtures prove integration, not corpus quality.
* `integrated-native-build-1`: fresh formatting check, Clippy with warnings denied,
  115 library + 4 CLI + 7 streaming optimized tests, and optimized release build
  passed. The four stripped native artifacts exactly reproduce the prior frozen
  native binary hashes. Vendor C++ compiler warnings remain explicitly separate
  from the clean first-party Rust Clippy result.

Final Sonar `hygiene/run-5` reports **zero Rust and zero Python issues** on the
actual native source and complete maintained runtime/tools/tests. Earlier scans
and all fixes remain preserved. CFamily/C++ is unavailable on the installed server,
so first-party C++ and vendor code are explicitly unscanned by Sonar. Native
compiler diagnostics remain separate. No Python formatter was installed/run.
No release-readiness or new Silesia size claim follows from these source checks.

Later checks found and corrected two further integration gaps before freezing:
Mozilla's TAR container was excluded by the inherited byte-zero ELF condition;
the joint-discount candidate now also accepts validated embedded section-pointer
structure. The read-only admission census covers the expected historical family
for all 12 members. Low-bit volume fixtures exposed a supplied-output dtype
mismatch in JPEG XL decoding. The decoder now supplies a fixed-capacity byte
buffer, allowing the binding to infer its sample dtype. The binding's
[output-buffer implementation](https://raw.githubusercontent.com/cgohlke/imagecodecs/master/imagecodecs/_shared.pyx)
constructs a bounded array view rather than allocating a new image for this case.
All 16 image/volume cases now pass, including direct low-bit CIXI2 restoration.
The tiny TAR-carried joint-discount route also completed a fresh encode and
archive-only exact decode.

Current mode policy: FAST considers native FAST plus raw; DEFAULT also considers
non-PAQ whole-input specialists and paid heterogeneous regions; BEST admits the
restored generic PAQ and specialist choices under explicit resource/time bounds.
Every complete candidate pays its framing and model description. Whole-input
competition and local mixed-region selection remain distinct from predictive mixing.

Final focused evidence:

* `integrated-dev-unit-10`: 37 focused runtime and real-command harness checks
  passed after the final product edit (unused local removal).
* `integrated-dev-specialists-2`: all 15 specialist archives have exactly the
  same SHA-256 as the earlier pre-cleanup results, with fresh independent decode.
* `integrated-helper-parity-1`: 55 old/current helper cases passed, including
  byte-identical encoding and both cross-decoding directions.
* `integrated-dev-images-3`: all 16 high/low-bit image and volume cases passed.
* `integrated-admission-1`: read-only current-input admission confirms the
  historical winning family for all twelve canonical members under BEST's budget.
* `runtime-quality-final.json`: 41 production modules parse; no unresolved local
  imports, research/corpus coupling or silent exception handlers detected.
* The harness now freezes its scheduler/import closure and both Python
  interpreters, validates canonical identities/order/budgets before dispatch,
  and counts all retained evidence plus active scratch toward the temporary cap.
  Kernel memory peaks are read from the aggregate phase cgroup; temporary limits
  use sampled directory accounting rather than a filesystem quota.

The final host stage `/home/user/src/cix-integrated-candidate` has passed fresh
ordinary FAST/DEFAULT/BEST CLI exact-restoration checks, shared-image verification,
and source/stage parity. The final four functional harness fixtures also pass.
The independent freeze review is closed; its temporary-accounting concern was
withdrawn after verifying total (not incremental) live-directory measurement.
The source/dependency freeze is complete and checked before each phase. The stage
is intentionally host-pinned Linux qualification material; integrated portable
source builds, platform packages and public distribution remain unqualified.

The root launched the full serial pass in exec session 85334, using absolute
paths throughout. FAST and DEFAULT Dickens have completed fresh exact decode;
BEST Dickens is active at this checkpoint. Do not mistake these two cells for
complete mode or corpus qualification. Read the live `summary.json` and cell
receipts for current progress.

The current-task heartbeat `finish-frozen-cix-silesia-confirmation` checks every
15 minutes to supervise this already-running pass and produce its final report.
The user has additionally requested repair of the C/C++ analyzer limitation.
After the Silesia report and all benchmark processes have finished, root must
execute and verify the separately prepared SonarOpenCommunity CXX repair under
the shared scheduler lease. The coordinating task owns `tools/sonar-cxx` and
`docs/research/2026-10-04-sonar-cxx-repair`; its ready command will be supplied
separately. Require actual analyzer execution and indexed-file/issue read-back
for first-party native/squash and native/PAQ vendor scope. CXX is distinct from
commercial CFamily; keep rule/coverage limitations explicit. No product change
is implied, and no setup/build/scan may compete with this frozen pass. Preparation
alone does not complete this new request. The heartbeat stays quiet on unchanged
healthy state and pauses only after both reports are delivered.

The coordinator has now delivered the ready command (run from the development
repository only after all 36 cells verify and every benchmark process ends):

```sh
python3 tools/sonar-cxx/repair.py run --prepared docs/research/2026-10-04-sonar-cxx-repair/prepared-v1 --out docs/research/2026-10-04-sonar-cxx-repair/scan-v1
```

Prepared runner SHA-256:
`6ba9316434fec91803c2e05be31f9e144dea8f651215e9767de7299c0659c6c0`.
Root read-back matches. The manifest inventories 1,346 C/C++ files, with two
disabled CUDA headers separately excluded. Three lightweight preparation tests
passed in the coordinating task; actual server/probe/six-project scans have not
run. Server/plugin compatibility and the absent generated Squash 0.8 SDK header
remain validation limitations, not completed qualifications. Use new attempt
directories if scanner setup needs correction; preserve every failed receipt.
The older `complete-cix-0-1-release-qualification` automation remains PAUSED.
No new dataset, public publication or Sites work follows before the Silesia report.

The finite history review is [FINAL-OPPORTUNITY-REVIEW.md](FINAL-OPPORTUNITY-REVIEW.md).
CPI1 contained **28 experts** (not 128); the causal gain failed its predeclared gate.
No research result establishes a universal limit on possible compression.
