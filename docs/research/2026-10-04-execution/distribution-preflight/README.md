# Distribution preflight: source allowlist skeleton

This directory records a preflight only. It does **not** export a source tree,
create a package, select a dependency version, sign an artifact, or qualify an
installed consumer. The proposed native source allowlist and non-mutating
validator live in [`rust/cix-native/packaging/export`](../../../../rust/cix-native/packaging/export).

The skeleton uses the existing conventional Rust layout (`Cargo.toml`, `src/`,
`include/`, `man/`, `packaging/`, `codecs/`, `vendor/`) and retains required
license/notice files. It deliberately excludes source outside the native tree:
research records, corpora, benchmark work/results, Python runtime/reference,
private material and build artifacts. Within the native tree it retains current small native integration/conformance tests, C installed-consumer material, and compact generated fixture sets (`native_ports`, `record_stride`, `regions`,
and `address_relations`) required by `include_bytes!` reference checks. The
private-reference-dependent `tests/fixtures/regions/make_fixtures.py` generator
is explicitly excluded; only its generated bounded fixtures/manifest can ship. It retains the explicitly registered `examples/native_buffer.rs` Rust SDK consumer. It excludes research-only auto-discovered examples, Criterion benches, experimental source, `src/bin` audit fixtures, corpora and large benchmark data.

Codec dependency rules are intentionally blocking rather than invented:

- PAQ bridge CMake files require a packaged, unchanged source root selected by
  the future dependency freeze; a local reference checkout is insufficient. A
  full-engine RC export is blocked until that closure is accepted.
- The JXL bridge requires a provisioned libjxl 0.12 prefix. No local JXL SDK
  was found in the preceding dependency inventory, and a full-engine RC export
  is blocked until its selected JXL closure is accepted.
- A separately named `native-core-optional` profile can omit a bridge only with
  an explicit feature declaration. It cannot be called a full-engine RC or used
  to satisfy the retained-route, compatibility, packaging or RC51 obligations.
- System-codec dependencies remain target-specific and need derivation and
  installed-consumer checks. Existing Debian/RPM recipe entries are source
  material, not qualification.
- Existing vendored codec notices/provenance must stay with any selected vendor
  source. Third-party code is not edited by this preflight.

The validator only reports the exact member set implied by the allowlist. Root
schedules its focused test/receipt later; no test or export was run here.

Sources: [`source-allowlist.json`](../../../../rust/cix-native/packaging/export/source-allowlist.json),
[`validate_source_allowlist.py`](../../../../rust/cix-native/packaging/export/validate_source_allowlist.py),
[`package_release.py`](../../2026-10-04-release-0.1/package_release.py), and
[`requirements.json`](../../2026-10-04-rc-reconciliation/requirements.json).
