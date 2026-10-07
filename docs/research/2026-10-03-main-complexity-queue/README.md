# Native encoder complexity receipt

Parent commit: `0c6028e39fedb3f659bf5985ea0b16cb4ed1b58d`.

This change extracts only two source-preserving boundaries in
`rust/cix-native/src/main.rs`:

- `prepare_candidate_encoder` borrows the existing `EncodeOptions`, keeping
  CIXG header emission, candidate state initialization, retained-buffer
  admission, and budget construction in their original order.
- `finish_m6_encode` keeps the CIXM6 budget-skip report, footer, optional
  CIXF1 name trailer, and flush in their original order.

The candidate loop still owns reading, interruption and EOF handling, route
selection, frame emission, hashes, and selection statistics. The M6 loop still
owns trial order, model/history updates, block bookkeeping, and EOF handling.

## Validation

`cargo build --release --bin cix` succeeded for the candidate. A pristine
detached parent build of `cix` and `uncix`, and a candidate `uncix` build, also
succeeded. Both existing tracked parity sources were encoded with 512-byte
blocks under CIXG1 and CIXG2 at one and two threads, and CIXM6 at its supported
one-thread setting. All ten candidate archives exactly match pristine archive
SHA-256 values and sizes. Candidate and pristine decoders each restored the
input SHA-256 for every candidate archive.

Raw release logs, parent identities, complete source patch, and all parity
archive/output hashes are in `raw/`. The source patch SHA-256 is
`98e5ff2a7b98cb3d386ab217ddfe62902d0847efcdfe7d867a0f5eb6bce810ed`.
