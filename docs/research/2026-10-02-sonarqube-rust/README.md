# Local SonarQube Rust review

## Scope

This is a local-only review of the first-party Rust implementation at
`4fd93df3673608067595829e23bf69f0be3c6144`. It did not send source or
analysis data to SonarCloud, did not run GitHub Actions, and did not run a
benchmark dataset. The scanned paths were `rust/cix-native/src` and
`rust/cix-native/tests`. Vendored `vendor/libzpaq715` and `vendor/libbsc` C/C++
were deliberately outside that Rust scan; their upstream provenance and native
compiler warnings remain a separate dependency-maintenance responsibility.

The current official Rust documentation says that Sonar's Rust analysis uses
Clippy, along with Rust complexity and duplication analysis. A Clippy JSON
report was generated with all Rust targets and imported into the local server.
The report was de-duplicated by rule, primary file and primary line before
import because the same source is compiled repeatedly for the three CLI
binaries, examples and tests. This preserves distinct warnings without
reporting target-build duplicates as separate source findings.

## Reproducible environment

| item | value |
| --- | --- |
| server | `sonarqube:latest`, Community Build `26.9.0.129388` |
| server digest | `sha256:4905574ab8584dcac1a06c01cdc43a4ce9e369723ac4a7ab1d029c1bf71e6fe9` |
| scanner | `sonarsource/sonar-scanner-cli:latest`, Scanner CLI `8.1.0.6389` |
| scanner digest | `sha256:a3f4215076706c95a17a68c19322ee916e40a3acd081a8c1a1e839e0194afa57` |
| Rust inputs | Cargo manifest `rust/cix-native/Cargo.toml`, all targets and features |
| server limits | localhost only, two CPUs, 4 GiB memory, no swap |
| scanner limits | localhost only, two CPUs, 1 GiB memory, no swap |

The first import created 396 duplicated external-Clippy records because each
target supplied the same diagnostic. The de-duplicated rescan closed those
records. The scanner analyzed 57 Rust source/test files and its quality gate
passed.

## Results after the local patch

| category | open count |
| --- | ---: |
| Bugs | 0 |
| Vulnerabilities | 0 |
| Security hotspots | 0 reported |
| Code smells | 75 |

Every open finding is Sonar rule `rust:S3776`, cognitive complexity above the
default threshold of 15. The highest values are selector/CLI/streaming methods
in `main.rs` (156, 135, 132), `streaming_backend.rs` (75),
`portfolio_auto.rs` (66), and mature native codec implementations. These are
real maintainability findings, not correctness failures. Refactoring them is
large enough to change decoder/encoder control flow and needs separately
owned, exact-round-trip-qualified changes; this review does not suppress the
rule or change the quality profile to hide them.

The build also prints warnings from vendored libZPAQ 7.15 and libbsc 3.3.12,
mainly unused upstream portability parameters and signed/unsigned comparisons.
No vendored source was edited in this review.

The Community Build logged `Dependency analysis skipped`; consequently this is
not a dependency-vulnerability or license scan. The zero vulnerability result
above is limited to the Rust source rules that actually ran.

## Applied first-party fixes

The isolated review worktree contains this small behavior-preserving patch:

1. Simplified the XZ result check without changing accepted result values.
2. Used a saturating decrement in FAST LZ probe throttling, retaining the
   existing zero behavior and making the underflow invariant explicit.
3. Removed an obsolete explicit `drop` of a non-`Drop` closure after Rust's
   non-lexical lifetime has already ended its borrow.
4. Documented the public Squash FFI callback safety contract.

`cargo check --all-targets --all-features` passed. Focused local tests passed:
`backend_registry` (11) and `resource_admission` (5). The patch does not alter
archive framing, candidate selection, compression parameters, or decoder
semantics, so it does not require a new compression experiment identity.

## Remaining work

The 75 complexity findings should be addressed by bounded, module-by-module
extractions with exact archive compatibility tests at each step. Priority is
the live CLI and streaming selector paths, then the automatic portfolio, then
individual codec implementations. Do not replace the work with `allow`
attributes, global scanner exclusions, or a relaxed quality profile. A fresh
local Sonar scan and the associated focused decode tests are required after
each group of refactors.
