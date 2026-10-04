# Integrated runtime qualification

The frozen 36-cell Silesia confirmation pass is **STOPPED BY USER**. Five cells
remain verified, Mozilla BEST was interrupted during encoding and is unqualified,
and 30 cells never started. The controller and all children are gone; the active
service is inactive/dead with no remaining cgroup. Both benchmark continuation
automations are PAUSED. No restart or replacement benchmark is authorized until
the consolidated cross-session feature/backlog requirements are integrated,
checked and frozen as a new RC. Stop evidence is in
`qualification/silesia-confirmation-v1/stop-20261004-user/stop.json`.

The preserved plan is `qualification/silesia-confirmation-v1/plan.json`, product
source `5d93d9f1b`, freeze checkpoint `d026ee070`. All existing source, archives,
scratch and receipts remain preserved. Summary status is STOPPED_BY_USER; its
five verified rows remain valid only for this build. Mozilla native BEST had
completed an internal candidate of 12,306,640 bytes, but portfolio selection and
independent final decode never completed, so this is not a verified BEST result.
At interruption two PAQ candidates were running concurrently. Future scheduling
must address maximum useful parallelism explicitly within the shared limits.

The paragraphs below preserve the earlier milestone/history. All wording about
continuing the pass or waiting for 36 completions is superseded by the user stop.
CIX-owned source/hygiene work may proceed after requirements/ownership reconciliation.

Checkpoint at 2026-10-04 02:21 UTC: **5/36 verified**, with all three Dickens
modes and Mozilla FAST/DEFAULT complete. Mozilla BEST is encoding. All completed
cells passed a fresh-process archive-only exact decode; no cell has failed.

| Member | Mode | Complete archive bytes | Reduction | Full encode wall (s) | Decode wall (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| dickens | FAST | 4,691,307 | 53.97% | 0.254 | 0.132 |
| dickens | DEFAULT | 3,777,545 | 62.94% | 10.793 | 3.195 |
| dickens | BEST | 1,862,182 | 81.73% | 3,656.663 | 1,965.579 |
| mozilla | FAST | 20,527,632 | 59.92% | 1.260 | 0.360 |
| mozilla | DEFAULT | 12,733,922 | 75.14% | 170.369 | 3.033 |

Dickens BEST selected PAQ v215 -9L; all six admitted candidates completed.
Its archive is 40,163 bytes smaller than portfolio26 and equals the retained
known-better CIX reference. This is a verified restoration of that result, not
a new public record. Kernel aggregate memory peaks were 4,565,573,632 bytes
for the complete encode search and 3,917,266,944 bytes for independent decode.
Mozilla DEFAULT automatically selected `ecoff-filter-mode0` at 12,733,922 bytes,
compared with 19,359,815 bytes for the current native DEFAULT candidate in the
same search; all seven admitted candidates completed. This is a measured
specialist-selection benefit, not predictive mixing or a public record claim.
The full mode/corpus comparison remains pending. Timings are single observations.

The user subsequently clarified the release target: **one CIX executable;
integrated codec libraries are acceptable**. The current frozen shell/Python
launcher and separate backend executables provide valid evidence for this exact
candidate, but do not satisfy that packaging target. Successful models remain
required. The next integration will use CIX-owned library bridges and a distinct
build identity after the frozen pass/report and CXX audit; see
[SINGLE-EXECUTABLE-PLAN.md](SINGLE-EXECUTABLE-PLAN.md). No vendor source edits,
renamed external programs or automatic repeat of the full tournament are allowed.

The coordinating task reports a separate [read-only host audit](../2026-10-04-host-performance-audit.md) with active
thermal throttling (CPU10 counter 133325 to 133422 to 133423), one 100 C package
sample, busy clocks about 5.225–5.308 GHz and dynamic PL1 around 55.375–58.5 W
with thermald active. These are attributed observations pending its full audit,
not a measured correction to benchmark times. Root made no host setting change.
Cooling and interacting power policies require review after the pass; do not
raise power limits during the frozen run or claim a proven maximum-speed host.

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
paths throughout. The completed cells above do not establish complete mode or
corpus qualification. Read the live `summary.json` and cell receipts for current
progress.

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

The subsequent user instruction limits remediation to CIX-owned code and tooling.
The audit still scans first-party and third-party C/C++ for visibility, but no
external upstream or vendored source, including bundled/forked PAQ trees, may be
edited to clear findings. Preserve third-party identities and report external
issues separately, without suppressing them to manufacture a clean result.
Analyzer setup corrections and any justified CIX-owned wrapper/boundary fixes
must be distinguished from external repairs. The active heartbeat includes this
boundary; it does not alter the running frozen source or benchmark schedule.

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
