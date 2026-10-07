# Fixed-mix P1 mechanical cleanup — e4e9a10ab

## Scope

This isolated patch is based on `e4e9a10ab` and changes only
`rust/cix-native/src/fixedmix.rs` plus this evidence packet.

- Replace two index-based stretch-table fills with `iter_mut().enumerate()`.
  Both still skip index zero and evaluate the same fixed integer expression in
  ascending index order.
- Give the private recurrence tuple and the private `probabilities` return
  type names.  This only changes type spelling.

It retains the process-wide immutable `OnceLock` stretch table, all fixed
point arithmetic, history ordering, byte framing, and selection behavior.
There is no algorithm, route, or policy change.

## Qualification

The candidate passed, under the declared CPU 18 / 1 GiB / no-swap launch
recipe:

| Command | Result | Receipt |
| --- | --- | --- |
| `cargo test --test fixedmix_recurrence --test decoder_memory --test mixer_allocations -- --test-threads=1` | 12 passed | `raw/candidate-tests.raw` |
| `cargo clippy --lib --all-features --message-format=short` | pass; no fixedmix lint remains except existing duplicate-module architecture notice | `raw/clippy.raw` |

The recurrence suite checks v1 canonical fixture preservation, v2/v3 exact
restoration, prefix history, and malformed/truncated/corrupt rejection.  The
decoder-memory suite checks resource admission and malformed payload handling.
The allocation test retains bounded scratch allocation coverage.

Parent and candidate binaries were separately built from the same base.  Each
encoded the same 16 KiB deterministic generic byte input with
`cix --route mixture -c`, producing byte-identical CIX archives:

```text
input SHA-256:     67529bbad3df686726186dd8515a002c91c259d78a066e390646763e988c6c05
parent archive:    263b3d6aade5c48906f03d1a8f019b71cca6e880f756a6a3849581d9fb104162
candidate archive: 263b3d6aade5c48906f03d1a8f019b71cca6e880f756a6a3849581d9fb104162
```

`cmp` confirmed archive equality.  A fresh parent decoder restored the
candidate archive, and a fresh candidate decoder restored the parent archive;
both outputs match the input SHA-256.  The raw parity receipt records binary
hashes and every resulting file hash.

Completed units were collected by systemd before post-run property readback,
so CPU affinity and cgroup limits for successful runs are declared launch
settings, not independently retained post-run readbacks.  The raw logs retain
the unit invocation and result.  No performance result is claimed from this
refactor.

`raw/base-commit.txt`, `raw/base-tree.txt`, and `raw/artifact-sha256.txt`
record source and artifact identity.  Compiler/build/parity/test/Clippy logs
are retained in `raw/`.
