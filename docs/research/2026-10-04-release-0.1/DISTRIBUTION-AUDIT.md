# CIX 0.1 public-distribution audit

## Decision

This is a release-design audit, not a release. The public repository must be a new source-only repository created from an explicit allowlist, rather than a copy of this research repository. The incumbent scope is production revision `d3a2cd416`; compatibility readers may remain, but no experiment, corpus, benchmark receipt, local result, hosted site, workflow, built host binary, or research selector evidence belongs in the export.

The present tree is **not yet publishable**. The two blocking conditions are:

1. The project has no licence granting recipients permission for CIX-authored source. `Cargo.toml` has neither `license` nor `license-file`, and no project-level `LICENSE` is tracked. A release owner must select and add an actual licence before a public source or binary release. This audit does not invent that grant.
2. The executable is not portable simply because Rust cross-compiles. It links system zlib, bzip2, liblzma, Zstandard, Brotli encoder/decoder and a platform C++ runtime. The current code has only Linux/macOS C++ runtime link directives, and the native dependency contract has not been built and verified on macOS or Windows.

The current tracked `rust/cix-native/THIRD_PARTY_NOTICES.txt` is adequate starting material for the vendored code, and must be retained in both source and every binary release. The duplicate under `dist/` is a host-release artifact and must not be the source repository's canonical legal file.

## Actual build and runtime inventory

The package is one Rust crate (`rust/cix-native`) with three CLI binaries: `cix`, `uncix`, and `cixcat`. The shared library is only required by the optional Squash integration; ordinary command-line packaging must not install it unless that subpackage is selected.

`build.rs` compiles vendored ZPAQ 7.15 and libbsc 3.3.12 sources through `cc`. It needs a C++17-capable compiler. `external.rs` and `streaming_backend.rs` link the following non-Rust libraries directly:

| Role | Link name(s) in code | Debian/Ubuntu build package | RPM-family build package |
| --- | --- | --- | --- |
| gzip support used by `flate2` | `z` | `zlib1g-dev` | `zlib-devel` |
| bzip2 CIXB1 backend | `bz2` | `libbz2-dev` | `bzip2-devel` |
| XZ CIXB1 backend | `lzma` | `liblzma-dev` | `xz-devel` |
| Zstandard CIXB1 and streaming backend | `zstd` | `libzstd-dev` | `libzstd-devel` |
| Brotli CIXB1 backend | `brotlienc`, `brotlidec` | `libbrotli-dev` | `brotli-devel` |
| vendored C++ bridge | `stdc++` on Linux, `c++` on macOS | compiler runtime | `libstdc++-devel`/toolchain |

Rust crates are pinned by `Cargo.lock`; a source build must use `cargo build --locked`. There is no declared MSRV or pinned Rust toolchain. The checked host attestation records Rust 1.98.1, which is evidence for that host only. The release must declare a supported stable Rust version and test it before claiming a source-build floor.

The code conditionally implements Unix pipe polling and SIGPIPE-related behaviour. Non-Unix builds compile a simpler readiness path. That is not a Windows qualification. The current FFI link names, C++ source and platform assumptions require a native Windows build and round-trip test before Windows binary packages are offered.

## Third-party obligations

| Component | Evidence in tree | Distribution action |
| --- | --- | --- |
| libzpaq 7.15 | `vendor/libzpaq715/UPSTREAM.md`; public-domain remainder | Preserve provenance and the embedded MIT divsufsort-lite notice. The CIX watchdog patch must remain documented as a local modification. |
| libbsc 3.3.12 | `vendor/libbsc/LICENSE`, `AUTHORS`, `UPSTREAM.md` | Preserve Apache-2.0 text, authors/attributions, provenance and any changed-file notice required by Apache-2.0. |
| libbsc bundled libsais | `vendor/libbsc/libbsc/bwt/libsais/LICENSE` | Preserve Apache-2.0 text and attribution. |
| system libraries | dynamically linked, not vendored | Debian/RPM packages declare runtime dependencies; source packages declare development build dependencies. Binary bundles must include the applicable notices only if they carry those libraries. |
| Rust crates | locked registry dependencies | Generate and review a dependency licence/SBOM report from the exact lockfile during release; this audit does not infer all transitive licence terms from package names. |

The planned public repository must contain a project-owned `LICENSE`, a canonical `THIRD_PARTY_NOTICES.txt`, and a machine-readable SBOM/licence report for the exact release artefacts. It must not present a library's licence as the licence of CIX itself.

## Exact public source allowlist

Create the new repository with these paths only after a fresh export review:

```
README.md
LICENSE                         # selected by the release owner
THIRD_PARTY_NOTICES.txt         # copied from rust/cix-native, then reviewed
Cargo.toml
Cargo.lock
build.rs
src/**                           # production modules plus main.rs, uncix.rs and cixcat.rs
vendor/libzpaq715/{UPSTREAM.md,libzpaq.cpp,libzpaq.h}
vendor/libbsc/{AUTHORS,LICENSE,UPSTREAM.md,VERSION}
vendor/libbsc/libbsc/{adler32,bwt,coder,filters,libbsc,lzp,platform,st}/**
docs/formats/{FORMAT-CIXB1.md,FORMAT-CIXZ1.md}
docs/release/{SECURITY.md,SUPPORT.md,RELEASING.md}
man/{cix.1,uncix.1,cixcat.1}
packaging/debian/**
packaging/rpm/**
packaging/homebrew/**
packaging/windows/**
packaging/squash/**              # optional source subpackage only
distribution-manifest.json
.gitignore
```

The actual crate root should be the public repository root. Moving the Rust crate out of `rust/cix-native` removes internal path assumptions and lets `cargo install --path . --locked` be the documented source installation. Do not export `dist/`, `.github/`, Python code, benchmark/data directories, results, research docs, experiment/bench/example/test-only binaries, current Squash fixture evidence, scheduler state, local virtual environments, or any archive/input/output artefacts.

The libbsc allowlist deliberately includes the header-only CUDA stubs and `libcubwt` header path because `bwt.cpp` includes them even when CUDA support is disabled. It excludes no source that the current `build.rs` compiles.

## Packaging design

The base package is a terminal-only command-line utility:

| Package | Contents | Status needed before release |
| --- | --- | --- |
| source tarball | allowlisted source, lockfile, notices, manual pages | reproducible `--locked` build and source checksum |
| Linux `.deb` | `/usr/bin/cix`, `/usr/bin/uncix`, `/usr/bin/cixcat`, three section-1 man pages, notices and docs | install/remove/upgrade/purge test on a supported Debian release |
| Linux `.rpm` | same CLI/man/legal contents | build/install/remove test on a supported RPM release |
| macOS archive | three signed/notarized universal or architecture-specific binaries, notices and README | native arm64 and x86_64 qualification; do not bundle libraries without a reviewed dependency/licence policy |
| Windows archive | `cix.exe`, `uncix.exe`, `cixcat.exe`, notices and README | native MSVC or documented MinGW build, clean-machine execution and archive round-trip |
| Squash plugin (optional) | shared CIX library, Squash shim, `squash.ini`, notices | only after the host has the Squash 0.8 SDK and a real load/compress/decompress test passes |

Debian/RPM packages should rely on distribution-provided shared libraries, declare ABI/runtime dependencies generated or verified by their package tools, and avoid embedding duplicate copies. A standalone Linux tarball has no defined dependency strategy today and must not be offered as "portable" until it either bundles legal, tested libraries or explicitly targets a compatible system-library baseline.

The existing Squash integration is source-present but not locally qualified: the repository states that the Squash 0.8 development SDK is absent. It is therefore an optional post-0.1 package target, not a base-package promise.

## Required release test matrix

| Target | Build | Required acceptance |
| --- | --- | --- |
| Linux x86_64 (current) | locked LTO build | all three CLIs, `--help`, `--version`, stdin/stdout, named-file atomic output, CIXG/CIXM/CIXB decode compatibility, malformed input, SIGINT/pipe handling, package install/remove, man-page lookup |
| Debian stable x86_64 | source package and `.deb` | clean chroot build, dependency resolution, install/upgrade/purge, no files outside package ownership |
| Fedora or RHEL-compatible x86_64 | source RPM and `.rpm` | clean mock/container build, install/remove, dependency resolution |
| macOS arm64 and x86_64 | native locked release build | all CLI round trips, codesigning/notarization verification if distributed outside a package manager |
| Windows x86_64 | native locked release build | PowerShell/cmd stdin and files, paths with spaces, overwrite/error exit codes, round trips and malformed input |
| Squash on Linux | optional shared-library build | `pkg-config` discovery, plugin load, level 1/6/9 compress/decompress and failed callback paths |

For every binary artifact, capture SHA-256, source revision, dirty-tree state (which must be clean), Rust/toolchain version, compiler version, full build command, dynamic dependency list, SBOM, and exact test receipt. Run the same fixed corpus-independent correctness fixtures for every target; performance figures are measured separately and never substituted for these checks.

## Release sequence

1. Select the CIX licence; add copyright ownership and `license`/`license-file` metadata.
2. Freeze a clean `0.1.0` source revision with retained decoder compatibility; update `Cargo.toml` version from the research `0.2.0` only in the new export.
3. Implement and review the minimal root crate layout, manual pages, legal files, SBOM generation and Debian/RPM package recipes.
4. Build and test the matrix above. Treat every unsupported target as absent, not as implicitly portable.
5. Produce signed/checksummed source and binary artefacts, then run the package-version benchmark suite. The public README may only cite results tied to that immutable artifact and their full methods.

No optimisation conclusion follows from a packaging audit. The public release must retain the completed research conclusion: portfolio archive selection is different from a predictive mixture, and the measured causal mixture result did not justify a new codec route.

