# Release source quality closure

## Implemented source changes

- Moved the complete command implementation from `src/main.rs` to `src/cli.rs`
  and compiled it once as the library implementation through `src/lib.rs`.
- Replaced the `cix`, `uncix`, and `cixcat` entry files with small wrappers
  that call `cix_native::main_entry()`. The command parser still derives decode
  mode from the executable basename, so `uncix` and `cixcat` retain their
  existing command behavior.
- Kept `cix_squash_splice` in the library build, preserving the C ABI used by
  the optional Squash plugin.
- Removed the crate-wide `allow(dead_code)` and removed the research-only
  `oracle` library export.
- Confined test-only encoder convenience functions and transform-chain
  candidate measurement records to unit-test builds. The shipping chain
  selector still materializes the same candidates and chooses on the same
  complete-payload comparison; it no longer retains diagnostic measurements in
  a release binary.
- Removed unused stateful-model log-loss/model-specification APIs that were
  not reachable from the released codec.

## Compatibility boundary

All decoder modules remain in `src/cli.rs`'s module inventory. This includes
legacy BWT, chain, expert-mix, numeric, rank, transform, and wavelet decoding,
as well as CIXG1/CIXG2/CIXM5/CIXM6/CIXF1/CIXB1 container handling. No archive
format or encoder-selection behavior was deliberately changed.

## Superseded pre-prune validation

The release scheduler completed these source-level checks against this export:

- `cargo check --locked --offline --all-targets` passed on 2026-10-04
  (`raw/cargo-check-v3/result.json`, exit 0). The Rust crate emitted no
  warnings. The compiler output contains pre-existing warnings from vendored
  third-party C/C++ sources only.
- `cargo test --locked --offline --profile release-lto` passed on 2026-10-04
  (`raw/cargo-test-v1/result.json`, exit 0): 112 library tests, 4 CLI smoke
  tests, and 7 streaming-pipe tests passed. Those integration tests exercise
  the public encoder/decoder wrappers and malformed/streaming behavior.

These receipts predate the accepted exact-prune change and remain historical
evidence only. The final qualification is below.

## Superseded first static-analysis binding

The fixed export tree digest is
`3d7b979a6b330a6efa5df7a5d5bedc9426c5470f91a3e7cff7d04516a9a4ebb8`.

- `cargo clippy --locked --offline --all-targets -- -D warnings` passed under
  the bounded `cargo-clippy-v2` receipt with zero Rust diagnostics.
- The hash-bound local Sonar scan completed with exit 0. Its quality gate is
  `OK`, Clean-as-You-Code status is `compliant`, and current issue count is
  zero. The receipt imported zero Clippy diagnostics, binds the source tree and
  scanner image digests, and records successful temporary-token revocation.

The retained evidence is `raw/cargo-clippy-v2/result.json` and
`sonar-release/run-v1/`; it is superseded by the final binding below.

### Binding distinction before the final prune

The Sonar receipt binds the then-complete export tree
`3d7b979a6b330a6efa5df7a5d5bedc9426c5470f91a3e7cff7d04516a9a4ebb8`.
After that scan, ten non-runtime paths changed: `.gitignore`, `README.md`, the
manual pages, Debian/RPM package metadata, and the relocation of the release
security notice. The current export therefore does not have the old *whole
tree* digest.

A direct hash comparison against both the B0 performance-plan source binding
and the Sonar manifest found zero differences in the shipping runtime set:
`Cargo.toml`, `Cargo.lock`, `build.rs`, `src/**`, and `vendor/**`. The clean
Rust Sonar and Clippy conclusions remain bound to that unchanged runtime set;
they were not a fresh source-analysis claim about the changed documentation or
package metadata. Final Sonar v2 now binds the complete frozen export.

## Final frozen-source qualification

The final export tree digest is
`bd28975a504abbeb011d2aaba36224af6b5c7f3fa844f491c224166750cab1e7`.
It is the tree used by the final portable `opt-level=3`, fat-LTO,
codegen-units=1 artifact set in `/home/user/src/cix-0.1-artifacts/final/bin`.

- The final release build of all binaries and the shared library passed:
  `raw/prune-build-v1/result.json` (exit 0).
- The final release test run passed: 115 library tests, 4 CLI smoke tests, and
  7 streaming-pipe tests (`raw/prune-test-v1/result.json`, exit 0).
- Final all-target Clippy with `-D warnings` passed with zero Rust diagnostics:
  `raw/cargo-clippy-prune-v1/result.json`.
- Final hash-bound Sonar v2 completed with launcher exit 0, compute-engine
  success, quality gate `OK`, Clean-as-You-Code `compliant`, zero current
  issues, zero imported Clippy diagnostics, and successful temporary-token
  revocation (`sonar-release/run-v2/`). Its scanner detected and analyzed Rust.
- The matched completed-set prune controls passed without deadline omissions:
  the 3,721-byte small-native case produced an identical 1,096-byte archive,
  and the 1,029,744-byte medium-predictor case produced an identical
  79,507-byte archive. Both after-build restores were exact
  (`prune-match-results.json`). This establishes output equivalence for these
  matched controls; deadline-limited searches remain deliberately outside that
  identity claim.
- Final qualification passed for source/package build and Debian/RPM runtime
  round trips, CIXM6 streaming parity, the `cix_squash_splice` callback ABI,
  and opaque CIX transport through Zstd SquashFS
  (`raw/final-qualification-v1/result.json` and
  `final-qualification-results.json`).

## Scope and limits of the clean result

This is a Rust source-quality result. The scanner detected one language
(`rust`), ran the Rust analyzer and the Clippy importer, and did not analyze
the vendored C/C++ implementation. The retained build receipts still show
existing compiler warnings in `vendor/libzpaq715` and `vendor/libbsc`; those
warnings are neither suppressed nor represented as a clean C/C++ audit.

The no-dead-code conclusion is likewise limited to the released Rust targets:
there is no crate-wide `allow(dead_code)` in the export, and the fresh
all-target Clippy run with warnings denied reported no Rust diagnostic. It
does not make a claim about unused functions inside third-party vendor trees.

Compatibility evidence covers the 115 final release library tests and 11
public process tests, including streaming round trips and malformed footer
rejection. Final qualification also covers the shared-library callback ABI,
package round trips, and a CIXM6 stream-parity control. It is evidence for the
qualified cases, not a claim that every possible historic archive fixture has
been exhaustively enumerated.

Static command-line review also confirmed that `-t` and `-l` both set
`decode = true` before `finish_parse`. When no explicit `--memory` is given,
`finish_parse` assigns the intended 2 GiB decode limit. No parse-path defect
was found.
