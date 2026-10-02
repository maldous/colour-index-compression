# Rust audit-only instrumentation — 8865bfbcc

Source revision: `8865bfbccba354b02920da86c7088c17e5f96aab`.

The production commands and default allocator are unchanged. The additions are:

- `cix_hot_kernels`: Criterion 0.5.1 synthetic 4 KiB composition-rank,
  count-range and fixed-mix encoding probes.
- `count_range_audit`: a standalone Criterion target for the count-range
  encoder, so that count-range results do not depend on an uncommitted local
  audit binary.
- `cix-dhat-audit`: a non-default `audit-dhat` feature binary. It alone
  installs DhAT's global allocator and checks exact composition and fixed-mix
  reconstruction before exiting.

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

## Positive checks at this revision

- `cargo check --features audit-dhat --bin cix-dhat-audit`: passed.
- `cargo check --all-features`: passed.
- `cargo check --benches`: passed.
- DhAT smoke output verified both decoding checks and reported 4,096 input
  bytes, 4,163 composition bytes, 4,171 count-range bytes and 4,122 fixed-mix
  bytes. DhAT reported 118,077,983 allocated bytes in 45,092 blocks, peak
  live 13,515,278 bytes in 24 blocks, and 17,578 bytes in 5 blocks at exit.
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
