# Integrated runtime qualification

The 36-cell Silesia confirmation pass has **not started**. These are focused
development and release-construction checks, not compression benchmark results.

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
The source/dependency freeze is being assembled. The stage
is intentionally host-pinned Linux qualification material; integrated portable
source builds, platform packages and public distribution remain unqualified.
