# Integrated-source hygiene gate plan

**Status:** preparation only. No scan, formatter, build, test, container, or source mutation was run while preparing this plan.

## Freeze inputs

The final gate needs two separately bound inputs:

| Scope | Source to bind | Evidence required | Not covered by an earlier result |
|---|---|---|---|
| Native distribution | `/home/user/src/cix-0.1-distribution` | complete file manifest and SHA-256 tree digest, `Cargo.lock`, Cargo package version | Rust/C++ source changes after the earlier release tree scan |
| Integrated Python runtime | `runtime/cix_runtime`, `runtime/tests`, and runtime staging manifest in the current development tree | complete file manifest and SHA-256 tree digest | all Python runtime code, extracted legacy modules, and tests |

The existing `docs/research/2026-10-04-release-0.1/sonar-release/run-v2` evidence applies only to the previously frozen Rust-native source tree. It is not evidence for the current Python runtime, current integrated source, or vendor C++.

## Required scheduler-owned sequence

1. Freeze both source manifests and write their digests before executing any check.
2. Run `cargo fmt --manifest-path /home/user/src/cix-0.1-distribution/Cargo.toml -- --check`.
3. Run the already-required native Clippy command with `--all-targets -- -D warnings`, save JSON output, and bind it to the native manifest digest.
4. Run `runtime/tools/quality_check.py --runtime <runtime-root> --json <receipt>` for static Python closure, syntax, forbidden-path, and broad-exception evidence. This is a static hygiene receipt, not a Python type-check or a Sonar substitute.
5. Run the frozen runtime test command selected by the root scheduler and record its exact interpreter and dependency environment. A test result must use the same runtime tree digest as step 4.
6. Run Sonar under the existing lease/cgroup/token-lifecycle harness. Use **two explicitly labelled scopes**:
   - `native-rust`: `/home/user/src/cix-0.1-distribution/src/**/*.rs` with the fresh Clippy JSON importer. Exclude `vendor/**`, generated build output, package staging, artifacts, and documentation.
   - `native-cpp-first-party`: only `/home/user/src/cix-0.1-distribution/src/zpaq_ffi.cpp`, with a compilation database or Sonar build-wrapper evidence created during the matching native build. Do not include `vendor/libbsc/**` or `vendor/libzpaq715/**` in the zero-issue assertion.
   - `runtime-python`: `runtime/cix_runtime/**/*.py`, `runtime/tools/**/*.py`, and `runtime/tests/**/*.py`, mounted as a separately digest-bound scanner source. Keep every retained legacy module in scope; exclude only caches and generated output.
7. Query and archive Sonar issues and quality-gate results separately for all three keys. “Zero issues” may be reported only per scope, source digest, scanner-image digest, and quality gate.
8. Re-read static closure receipt after Sonar. If file digests changed at any point, discard the affected result and restart from step 1.

## Exact candidate configuration

The retained `benchmark-work/sonar-4af6/run_scan.py` is suitable as a reference for lease enforcement, scanner-image pinning, cgroup receipts, token revocation, and Rust Clippy importer accounting. It currently hard-codes `rust/cix-native` and a Git revision, so it must be copied/adapted by the scheduler for the standalone distribution directory. It must **not** be run unchanged against the integrated source.

Suggested scanner properties, supplied as scheduler arguments rather than committed credentials:

```text
# native-rust
sonar.projectKey=cix-0.1-native-rust-final
sonar.sources=src
sonar.tests=tests
sonar.inclusions=src/**/*.rs
sonar.test.inclusions=tests/**/*.rs
sonar.exclusions=vendor/**,target/**,packaging/**,docs/**
sonar.rust.clippy.enabled=false
sonar.rust.clippyReport.reportPaths=<fresh-clippy-jsonl>

# native-cpp-first-party
sonar.projectKey=cix-0.1-native-cpp-final
sonar.sources=src/zpaq_ffi.cpp
sonar.exclusions=vendor/**,target/**,packaging/**,docs/**
sonar.cfamily.compile-commands=<fresh-compile-commands.json>

# runtime-python
sonar.projectKey=cix-0.1-runtime-python-final
sonar.sources=cix_runtime,tools
sonar.tests=tests
sonar.inclusions=cix_runtime/**/*.py,tools/**/*.py
sonar.test.inclusions=tests/**/*.py
sonar.exclusions=**/__pycache__/**,**/*.pyc
sonar.python.version=3.12
```

If the installed Sonar edition lacks CFamily analysis, record that as an unavailable tool rather than extending a Rust-only zero-issue conclusion to C++. In that case retain compiler warning output for `src/zpaq_ffi.cpp` separately; no local `clang-tidy` or `cppcheck` executable was discovered during preparation.

## Local tooling observed

- Available: `cargo` and `sonar-scanner`.
- Not found on PATH: `ruff`, `black`, `flake8`, `pylint`, `pyright`, `clang-tidy`, `cppcheck`.
- A local PostgreSQL service is present, but no active Sonar Java service was observed. Do not assume it is an authorized reusable Sonar instance; the pinned isolated-server harness remains the reproducible path.

## Actual runtime hygiene risks for the gate

1. `runtime/cix_runtime/legacy/multinomial.py` contains lazy imports for modules such as `.bwt`, `.ppm`, `.expertmix`, `.fixedmix`, `.transforms`, `.numeric`, `.record`, `.periodic`, `.bitplanes`, `.chain`, and `.histogram` that are absent from the retained legacy directory. The current specialist callers use only its shared arithmetic/type-class helpers, but any invocation of its legacy portfolio entry points can fail at runtime. The static receipt must report each unresolved lazy target. Release resolution is to remove unreachable entry points or retain every required dependency; do not hide this with a blanket dead-code suppression.
2. Multiple directly dispatched legacy decoders remain outside this task’s chemical/database scope and use unrestricted LZMA/Brotli/image decoder expansion. The existing runtime review identifies these paths. Their bounded-decoder repair and proof are required before a whole-runtime safety/quality claim.
3. The current Python tree has broad exception handlers. The receipt records their locations for review; it does not classify them as dead code. Candidate omission handlers may be intentional, but silent exception handlers in retained codec paths require a specific justification or repair.
4. Python style/type tooling is not installed locally. Sonar can still analyse the Python scope, but do not claim formatter, standalone linter, or type-checker compliance unless the scheduler provides a pinned tool and records its version and configuration.

## Completion evidence

The final gate needs a single combined manifest containing both source tree digests, every command line, tool/scanner image versions, raw reports, Sonar project keys and quality-gate responses, scope exclusions, static closure receipt, and test/Clippy result hashes. This allows the 36-cell qualification to bind to one immutable integrated source state.
