# CIXM6 chain restore helper packet

Base source is `d172ce8b429adbbe26c01fa4c27545588e4b7f73`.
`source-only.patch` is the complete net source patch against that base and
contains only `rust/cix-native/src/chain.rs`. The evidence directory is
retained directly; the worker's empty documentation patch was excluded. The refactor extracts the existing
word restoration branches into small helpers without changing the decoder
format or encode path.

`restore_words_handles_all_numeric_operations_and_boundaries` covers XOR,
delta, delta2, and delta2-zigzag at 16, 32, and 64 bit widths.  Each operation
covers empty, one-word, two-word, and longer streams.  The zigzag fixture has
negative first and later delta changes and modular wraparound.

`mode7_multinomial_fixture_restores_fresh_archives` constructs 64-byte generic
numeric sources with `transform::apply_id`, IDs 5 through 16 and 29 through
31.  Every payload is exactly `[CHAIN_VERSION, transform_id,
INNER_MULTINOMIAL] + rank::encode_type_class(transformed)`.  When
`CIX_MODE7_FIXTURE_DIR` is set, the test retains source, payload, and complete
single-frame CIXM6 archive fixtures.

The current release `uncix` process decoded each retained archive at 16 MiB and
`cmp` matched all 15 output files to their sources. A separately built,
nearest-pre-helper immutable decoder from `45e7c68e710b6ec928f0350eef52e67662969212`
also decoded all 15 final fixtures with exit zero and exact output comparison.
Its binary SHA-256 and per-output hashes are in `raw/45e-uncix-compatibility.log`.
A footer-truncated ID-29 archive was rejected with exit 2 after emitting its
complete frame (64 bytes), which is valid streaming behavior before final footer
validation.

Raw command output and exits are in `raw/`. `raw/hashes.sha256` records the
current release binaries and fixtures. The recorded execution did not retain
per-child cgroup or affinity readbacks, so it is decoder compatibility evidence,
not child resource-admission proof.
The commands were:

```text
cargo test --release --lib --jobs 1 mode7_multinomial_fixture_restores_fresh_archives
cargo test --release --lib --jobs 1 restore_words_handles_all_numeric_operations_and_boundaries
rust/cix-native/target/release/uncix -c --memory 16MiB -
```

The test and decoder commands exited zero except the deliberate truncated
archive invocation, which exited two.  Build warnings are preserved verbatim
in the raw test logs.
