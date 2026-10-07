# Distribution provenance resolution v2

This read-only inventory maps existing local source/provenance mechanisms to
the remaining source-bearing distribution blockers for the mandatory Linux
x86_64 PAQ CLI/SDK closure.

## What already closes identity

* `distribution-engineering-v4/selected-provider-closure.json` binds all
  fourteen selected runtime artifacts by absolute path and SHA-256.
* The existing `stage_provider_sources.py` verifies every file in each of the
  four PAQ source receipts before copying it, writes `SOURCE-IDENTITY.json`,
  binds a bridge SHA-256, and copies the hash-pinned GPL text. This is already
  the right CIX-owned mechanism for PAQ source staging.
* `jxl-bridge-v3/source.json` freezes the CIX bridge inputs; `installed.json`
  hashes the installed bridge, libjxl/Brotli companions, headers, and CMake
  metadata. `provider-provenance-v3.json` further identifies the local libjxl
  checkout and recorded submodule commits.
* Spatial selected bridge, CharLS, and OpenJPEG binary hashes are recorded with
  package name/version/archive-hash evidence.

## Retained canonical identity found

The JXL provision receipt is stronger than the earlier summary: its recorded
clone command names `https://github.com/libjxl/libjxl.git`, branch `v0.12.0`,
and requires commit `a7a9c787341cf703dede03c2009fa460cae5e5df`. The retained
tree has that `HEAD`. Its recursive submodule closure is recorded as
testdata `73695d…5089`, Brotli `028fb5…de29`, googletest `6910c9…38c5`,
Highway `457c89…c48`, lcms `517634…ecc6`, libjpeg-turbo `8ecba3…3d1`,
libpng `872555…73d1`, sjpeg `94e0df…13c9`, skcms `96d917…b722`, and zlib
`51b7f2…9daf`. The provision receipt also stores the complete source-tree
file map, so JXL source identity is available locally.

The four PAQ directories expose a Git worktree whose `origin` and `HEAD`
resolve to the enclosing CIX repository (`8d143466…3cc8`), not a PAQ upstream
repository. That nested metadata is not PAQ provenance. The original retained
source records resolve the missing chain instead. `v215-source.json` identifies
the hxim v215 codeload archive, SHA-256
`e3a86a08961f90bab73b01cb3db27327471a701b6ac2dde0c972e5b6f78c0737`,
and commit `e80eed27ae8a673ccb016f1b158cff1b7150fcf6`; `v216-source.json`
identifies the corresponding v216 archive, SHA-256
`d231d814a0dc79657a2691ed166692a5dfbfa740388357654253ecadbdf8ef75`,
and commit `bf7b658fdcfc045a892920d01e830e6c6a790c21`.

Each RC receipt's complete file map exactly matches its retained reference
tree: v215 (351 files), v216 (350), joint-discount (354), and store-state
(350). The joint-discount retained provenance binds its 354-file fork to the
v215 archive/commit, CIX builder and modified-source hashes, and CIX commit
`b2aef743662c3cf51e3c779ef7410ac5cc4412c5`. The store-state provenance
similarly binds its 350-file fork to the v216 archive/commit, original and
patched compilation-unit hashes, its builder hash, and CIX commit
`b0a5528ce35976e97ae628b6f49a9b88a67eb07a`. These fork overlays have no
separate upstream archive, which is expected: their immutable identity is the
base archive plus the named commit in
`https://github.com/maldous/colour-index-compression.git` and complete
retained-tree receipt.

## Exact remaining blockers

| Component | Missing immutable/source fact | Required source-to-installed-binary record |
| --- | --- | --- |
| PAQ v215/v216/joint_discount/store_state | No unresolved canonical-source fact in the retained evidence; package assembly still needs to carry the records | Carry the two base source records, fork provenance records where applicable, existing per-file receipt map, CIX bridge source/CMake hash, compiler command, bridge artifact SHA, and staged-source identity digest. |
| libjxl/Brotli/Highway/skcms | A source archive or checkout-tree manifest tied to every selected shared-library hash | Record source locator/revision/archive SHA for each component; exact build inputs/commands/toolchain; installed library and required notice hashes. |
| CIX spatial bridge | Current source-to-selected-installed-bridge build record | Freeze bridge CMake/CPP/header hashes, compiler/CMake invocation, CharLS/OpenJPEG package identities, and installed bridge SHA. Existing selected binary binding is explicitly not a later current-source rebuild proof. |
| CharLS/OpenJPEG | Source-package URL/checksum and source-to-package/binary relation | Record source package locator/version/SHA, package archive SHA, package filename/architecture, installed library SHA, and Debian copyright hash. |

## Smallest CIX-owned packaging change

No new staging program is needed for PAQ. Create the **reserved**
`rust/cix-native/packaging/export/final-dependency-closure.json` with a versioned,
machine-readable provider map that consumes the existing PAQ
`SOURCE-IDENTITY.json` and selected-provider closure. That path is referenced
by the allowlist but is not present today. For every provider it
must require: `artifact_sha256`, `source_locator`, `source_identity` (revision
or archive checksum plus tree/file manifest), `build_identity` (CIX source and
commands where CIX builds the artifact), `notice_hashes`, and `target`.

The exporter must reject a mandatory provider unless all fields are present and
hash-match. PAQ’s existing stage result can satisfy `source_identity` from the
resolved base/fork records. JXL and spatial require new captured source/build
records; CharLS/OpenJPEG require package-source records. This is an additive
CIX packaging manifest/schema gate, not a third-party or licence text change.
