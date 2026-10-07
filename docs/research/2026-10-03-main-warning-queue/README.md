# Rust main warning queue receipt

## Scope and immutable inputs

- Parent commit: `fcf0cbc4441112945ea859da8282665bfd7afe26`
- Parent tree: `f4e6ece09fa47da3d2dbc2351b42d3fd1c4330f0`
- Worktree: `/tmp/cix-main-warning-queue` (detached at the parent commit)
- Changed source: `rust/cix-native/src/main.rs`, plus the two selector request
  call sites in `src/gstream.rs` and the coordinated `EncodeRequest` API in
  `src/streaming_backend.rs`.
- No corpus was acquired. The two existing tracked Rust test sources were
  `tests/cli_archive_oracle.rs` (SHA-256
  `d9d6fb612aa17d2e3731fec0529416d514181327e922e2b37442e245c2750cbc`)
  and `tests/streaming_pipe.rs` (SHA-256
  `38c92f379b8e9308fa515f0189548dd4f00ffafee76bdd2497b1f0aaeec4b53b`).

## Change

`main.rs` replaces the remaining multi argument boundaries with typed request
objects. It preserves selector candidate generation, route filtering, raw
incumbent and tie handling, complete-cost comparisons, side effects, errors,
and timeout values. The small idiom changes preserve equivalent arithmetic and
byte layout. `gstream.rs` constructs the same selector values in those request
objects. The coordinated streaming interface groups only its already admitted
request fields.

The exact three-source patch is outside Git at
`/tmp/cix-main-warning-queue.patch`, SHA-256
`1fd76d5b10590e24f4af43623e9f65dc9513e598dfe692fb3d648ee13ff19e7c`.

## Commands and results

All commands were run serially with the normal stable Cargo toolchain, no
swap, one build process, and at most the requested two codec threads. Raw
stderr/stdout receipts, command and exit journal, parent source identity,
full tracked source patch, input identities, binary identities, archive and
restoration hashes, and the available cgroup sample are preserved under
`raw/`. `raw/SHA256SUMS` covers every raw evidence file except itself. The
temporary `/tmp` paths named below are source locations only; the durable
copies in this packet are the review artifacts.

1. `cargo clippy --bin cix --message-format=json -- -W clippy::all`
   exited 0. It emitted no warnings for `src/main.rs`, `src/gstream.rs`, or
   `src/streaming_backend.rs`.
2. `cargo build --release --bin cix` exited 0.
3. Fresh parent and candidate `uncix` binaries were built with
   `cargo build --release --bin uncix`; each exited 0.
4. A pristine detached worktree at the parent commit built its `cix` and
   `uncix` release binaries successfully.
5. `cargo test --test cli_archive_oracle -- --nocapture` exited 0: its one
   complete CIXG1 archive-oracle test passed.
6. Parent and candidate each encoded both inputs using 512-byte blocks for
   CIXG1 and CIXG2 with `--threads 1` and `--threads 2`, and CIXM6 with its
   supported single thread. Candidate archives were decoded by both fresh
   candidate and pristine native decoders. All ten archive SHA-256 values and
   sizes exactly match their parent controls; every restored SHA-256 matches
   its input.

The tab separated result receipt is
`/tmp/cix-main-warning-parity/results.tsv`, SHA-256
`34733c2d9393933729b920ab10c7f2fe2098f8a64c4255403d66e64194c5b8ac`.
The complete archive/output hash manifest is
`/tmp/cix-main-warning-parity/hashes.txt`, SHA-256
`832261d89885fd8941bfaf6cab928e8de724af6489c25026c0cbde2b843bd572`.

## Limitation

CIXM6 deliberately rejects `--threads 2` with exit 2 and the established
message `--threads >1 applies to native CIXG1/CIXG2 block or candidate
selection`; it was attempted and retained in
`/tmp/cix-main-warning-parity/m6-thread2.stderr`. This is an existing option
contract, so CIXM6 parity is recorded at its supported one-thread setting.
