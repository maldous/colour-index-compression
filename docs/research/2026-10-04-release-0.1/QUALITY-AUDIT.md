# Release 0.1 quality audit

## Status

**Not release-ready.** The native runtime has a clean, reproducible Sonar
checkpoint, but the public-export snapshot has not yet been created or scanned
as an export. More importantly, the retained all-target Clippy evidence reports
241 `dead_code` warning instances. They are not Sonar issues, but they prevent
the stronger claim that dead code has been resolved.

The appropriate next action is one bounded release-candidate export: retain
the compatibility surface below, remove research-only material, then run the
standard release build, all-target Clippy with dead-code warnings treated as
release work, tests, and a fresh scan on that immutable export. Do not run a
new compression study as part of this gate.

## Sonar evidence

| Field | Evidence | Interpretation |
| --- | --- | --- |
| Source revision | `d3a2cd416e49f93403d1dbd348a3e9a45db66ec6` | Exact source scanned on 2026-10-03. |
| Checkpoint basis | `20e18503b1d208a552ff8efc1231bab2281fb82e` | Numeric-composition checkpoint preserved. |
| Runtime delta, scan → checkpoint | 0 paths in `rust/cix-native/src`, `Cargo.toml`, `Cargo.lock`, or `build.rs` | The release runtime and build description are byte-for-byte unchanged. |
| Later native additions | 22 paths, all under `rust/cix-native/experiments/` | Research-only; exclude from the public source export. |
| Sonar result | 0 current issues, `projectStatus.status=OK`, `caycStatus=compliant` | Fresh for the unchanged Rust runtime, not a scan of the future export. |
| Compute engine | `SUCCESS`, analysis `9c1a4a91-3b62-4907-89a1-380081ffbe98` | Completed rather than a scanner-only result. |
| Analysis scope | 82 Rust files; Rust Sonar way; tests/examples/benches included | `experiments/` and vendored C/C++ were outside the qualified Rust scope. |
| Known scope warning | One C++ file was detected but not analyzed by this Sonar edition | `src/zpaq_ffi.cpp`/vendored C++ require compiler/test coverage and a separately appropriate C/C++ review before release. |
| Live service | No active CIX Sonar container; `cix-sonarqube-rust-review` is exited | There is no current local API endpoint to query without starting a new scan. |

The historical 2026-10-03 `6ac05f8e9` scan had three open Rust cognitive
complexity findings (`src/chain.rs:1247`, `src/main.rs:2886`, and
`src/main.rs:3830`). The `d3a2cd416` helper refactor is the later source and
its completed scan reports zero issues. Treat the earlier findings as resolved,
not as current findings.

## Dead code and static analysis

The clean Sonar result does **not** mean a zero-warning release. The completed
all-target/all-feature Clippy receipt associated with the prior `6ac05f8e9`
checkpoint contains 241 `dead_code` warning instances. They are inflated by
the fixture targets that include production modules by path, but the following
runtime declarations recur in ordinary source targets and need an explicit
release decision rather than a blanket allowance:

| Area | Recurrent retained warning | Release disposition required |
| --- | --- | --- |
| `src/bwt_legacy.rs:1516` | `encode_version` unused | Remove if legacy encoding is withdrawn, otherwise add a direct compatibility test/use. |
| `src/chain.rs:50,59,1241` | unused candidate-report fields and `encode` | Keep only if exposed by an active encoder/diagnostic; otherwise remove after decoder compatibility review. |
| `src/expertmix.rs:244,252,319,327` | encode/decode entry points unused | Confirm whether CIXM6 modes require them; retain and test if decoder reachable, otherwise remove. |
| `src/stateful.rs:124,342` | unused estimates/model specification | Remove or connect to released selection/observability. |
| `src/transform.rs:400` | `encode_id` unused | Remove or cover the released transform encoder. |
| `src/lib.rs:1` | crate-wide `#![allow(dead_code)]` | Replace with narrowly justified allowances only after resolving the items above. |

The remaining warnings occur predominantly in test/example/audit targets that
compile partial module graphs (`rank`, `histogram`, `adaptive`, `numeric`, and
`limits`). They must be eliminated by changing those fixtures to import the
library API or by putting fixture-only adapters behind an explicit test-only
module. Do not suppress them globally: that would hide dead code in the
shipping library.

## Lean public export boundary

The future public source repository should be a deliberate allow-list, not a
copy with a long deny-list. Its minimum native source set is:

```
Cargo.toml
Cargo.lock
build.rs
src/
vendor/libzpaq715/
vendor/libbsc/
FORMAT-CIXB1.md
FORMAT-CIXZ1.md
THIRD_PARTY_NOTICES.txt
README.md
LICENSE* and NOTICE files
```

`src/` must remain whole for version-0.1 compatibility. In particular it must
retain `bounded_reader`, `bwt_legacy`, `chain`, `expertmix`, `histogram`,
`legacy_lz`, `numeric`, `rank`, `transform`, `wavelet`, and the three public
entry points (`cix`, `uncix`, `cixcat`). Removing an encoder because it is not
the default can break decoding of an already-issued CIXM5/CIXM6 archive.

`build.rs` compiles both vendored libraries, so neither vendor tree can be
silently omitted. Their upstream notices and licenses must accompany source
and binary packages. The optional Squash integration belongs in a separate
subpackage/source bundle: `squash/` plus the native shared library, tested only
where the Squash 0.8 development SDK is installed. It is not a prerequisite
for the core CLI package.

Exclude from the public export: `docs/research/`, `benchmarks/`,
`benchmark-work/`, `results/`, `.hutter-experiment-scheduler/`, the native
`experiments/`, `benches/`, `examples/`, development-only Python package and
tests, locally built `target/` output, and historical `dist/` binaries. Do not
copy `.github/workflows/`: every checked-in workflow is a research workflow and
the project policy keeps Actions disabled. A fresh public repository should
add only release-oriented CI after its package gate is defined.

## Release gates

1. Create an immutable public-export candidate from the allow-list and record
   its source hash and file manifest.
2. Resolve all retained dead-code warnings without changing supported decoder
   behaviour; validate CIXM5/CIXM6 and CIXG1/CIXG2/CIXB1 decoding before each
   removal.
3. Build and test that export on its supported toolchains, including its C++
   bridge and vendored dependencies.
4. Run Sonar and Clippy against the export itself. A zero-issue Sonar result
   must state the language scope; it is not a substitute for C/C++ review.
5. Build/package the core CLI and independently qualify the optional Squash
   subpackage on a host with the required SDK.

Evidence locations: `docs/research/2026-10-03-rust-rnd/sonar-d3a2/REPORT.md`,
`run-v1/manifest.json`, `run-v1/raw/{issues,quality-gate,ce-task}.json`, and
the preceding `sonar-6ac0` report/Clippy receipt. No new scan or build was run
for this audit.
