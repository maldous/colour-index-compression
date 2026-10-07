# Rust audit-only instrumentation — 8865bfbcc

Production source under audit: `8865bfbccba354b02920da86c7088c17e5f96aab`.

Instrumentation source revisions:

- `4b598673152336ddb4794729146494294bed1d40` adds the optional allocator
  binary and Criterion targets.
- `e88cde24f0428b049101fe9263f9bbfe1be11133` adds the exact count-range
  reconstruction check to the allocator binary.

The Rust production tree is unchanged between `8865bfbcc` and the parent of
`4b5986731`; the later commits add Cargo audit declarations, audit-only source
and this documentation. Checking out `8865bfbcc` alone therefore does not
provide the instrumentation targets.

The matched BEST probe's inherited source-state field is interpreted in
[`matched-best-grammar-v2-provenance-erratum.md`](matched-best-grammar-v2-provenance-erratum.md).

The production command source and default runtime allocator are unchanged. The
additions are:

- `cix_hot_kernels`: Criterion 0.5.1 synthetic 4 KiB composition-rank,
  count-range and fixed-mix encoding probes.
- `count_range_audit`: a standalone Criterion target for the count-range
  encoder, so that count-range results do not depend on an uncommitted local
  audit binary.
- `cix-dhat-audit`: a non-default `audit-dhat` feature binary. It alone
  installs DhAT's global allocator and checks exact composition, count-range
  and fixed-mix reconstruction before exiting.

The `dhat` dependency is optional, `audit-dhat` is not a default feature, the
audit binary requires that feature, and Criterion is a development dependency.
Normal `cix`, `uncix` and `cixcat` builds therefore do not install the DhAT
allocator or execute Criterion code. The audit program's allocator covers the
whole audit process, including fixture construction and all three encode/decode
pairs; its totals are not per-kernel allocation counts.

## Aggregate-suite attribution

The separate aggregate Cargo test recorded in
`benchmark-work/rust-performance-audit/combined-8865-allocator-feature-tests.log`
started at 2026-10-02 16:59:03 +10:00. Its test executables were compiled by
16:59:15, before the audit Cargo manifest and lockfile changed at 17:07:23.
Cargo therefore resolved that invocation against the `8865bfbcc` production
tree, before the `audit-dhat` feature and Criterion targets existed. Later
manifest edits cannot change already compiled test executables.

That long-running command is evidence for the production Rust tree only. It
does not qualify the new audit targets, despite having been invoked with
`--all-features`, and it is not a completed-suite result unless its exit receipt
records success. The positive audit checks below are the separate qualification
for the instrumentation commits.

## Reproducible local commands

Run only when the performance audit owns its WaveScheduler lease. The smoke
run below was pinned to CPU 30 and used two Cargo build jobs; it is a tooling
qualification, not a cross-revision performance claim.

```sh
CARGO_BUILD_JOBS=2 cargo check --manifest-path rust/cix-native/Cargo.toml \
  --features audit-dhat --bin cix-dhat-audit
CARGO_BUILD_JOBS=2 cargo check --manifest-path rust/cix-native/Cargo.toml --all-features
CARGO_BUILD_JOBS=2 cargo check --manifest-path rust/cix-native/Cargo.toml --benches
taskset -c 30 env CARGO_BUILD_JOBS=2 cargo run --manifest-path rust/cix-native/Cargo.toml \
  --features audit-dhat --bin cix-dhat-audit
taskset -c 30 env CARGO_BUILD_JOBS=2 cargo bench --manifest-path rust/cix-native/Cargo.toml \
  --bench count_range_audit -- --sample-size 10 --warm-up-time 0.1 --measurement-time 0.1
taskset -c 30 env CARGO_BUILD_JOBS=2 cargo bench --manifest-path rust/cix-native/Cargo.toml \
  --bench cix_hot_kernels -- --sample-size 10 --warm-up-time 0.1 --measurement-time 0.1
```

## Positive checks at the instrumentation revisions

- `cargo check --features audit-dhat --bin cix-dhat-audit`: passed.
- `cargo check --all-features`: passed.
- `cargo check --benches`: passed.
- DhAT smoke output verified all three decoding checks and reported 4,096 input
  bytes, 4,163 composition bytes, 4,171 count-range bytes and 4,122 fixed-mix
  bytes. DhAT reported 118,848,657 allocated bytes in 59,768 blocks, peak
  live 13,515,278 bytes in 24 blocks, and 17,578 bytes in 5 blocks at exit.
  The profiler begins before deterministic fixture construction and ends after
  all encodes and decodes, so these are whole audit-program allocation figures,
  not encoder-only metrics and must not be compared to encoder-only DhAT runs.
- Both Criterion targets completed on CPU 30. The generated Criterion output
  is transient build evidence and is intentionally not committed. Do not use
  these short samples as an optimization claim; collect repeated isolated
  measurements through the frozen performance-audit plan.

| Probe | Mean interval, 4 KiB synthetic input |
| --- | ---: |
| standalone count-range | 1.055–1.064 ms |
| hot-kernel composition rank | 6.614–6.645 ms |
| hot-kernel count-range | 1.033–1.063 ms |
| hot-kernel fixed-mix | 163.372–166.307 ms |
