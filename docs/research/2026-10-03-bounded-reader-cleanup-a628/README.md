# Bounded reader cleanup — 2026-10-03

Experiment `2026-10-03-bounded-reader-cleanup-a628` refactors
`read_bounded` after the `a628bda23e09bb43cceefa2d9e29009fbcc1df67` source
snapshot. It extracts initial allocation, read/probe, and growth reservation
without altering input admission, retry, allocation, or overflow behavior.

The bounded runner uses one service cgroup on CPU 18 with `MemoryMax=1G` and
`MemorySwapMax=0`. Its cgroup readback describes the service shell that runs
the build and tests; it does not claim a direct child-process cgroup probe.

`run-evidence.sh` is the exact command body. `systemd-run.raw.log` retains its
complete output. The run builds base and candidate binaries with the explicit
stable Rust toolchain, runs all six `bounded_reader` boundary tests, and checks
that independent `a628` and candidate gzip/bzip2 archives of one tiny periodic
input are byte-identical and restore the original bytes. It also runs the
existing external-source-buffer test, including empty, short, and 65,537-byte
inputs plus truncated-archive rejection.

## Result

The service exited successfully. The retained cgroup readback is CPU `18`,
`memory.max=1073741824`, and `memory.swap.max=0`. The six reader tests passed.
The `external_source_buffer` test passed its gzip and bzip2 cases, including
independent restoration and truncated-archive rejection.

For the 1,200-byte periodic input, both base and candidate produced the same
gzip archive SHA-256 `f69dc0f2ab58f27164b018291360af98cafb2adbbe7e23b8a3b45639c194471e`
and the same bzip2 archive SHA-256
`8c3380fa552dd57f265454a344817b026e780f25263578e45ecf4b8ba81de5f2`.
Each fresh base and candidate decode matched input SHA-256
`785413f885bcff4b395050e52d24c2f7b7030b8318e65e8f6cf57657d60a3b2c`.

The scoped patch includes only the owned reader and boundary-test changes.

## Assembled-source qualification

The reader-scoped patch remains the approved mechanical refactor. The current
worktree also carries an independently owned `chain.rs` cleanup, so a second
service run records the complete tracked diff from `a628` before its cached
candidate rebuild. `assembled-tracked-net.patch`, path list, source hashes,
binary hashes, and the raw service output bind that assembled reader-plus-chain
source snapshot to the subsequent six boundary tests and gzip/bzip2 parity.
The child cgroup line is a direct shell-child readback and is labelled as such;
it does not claim an in-process CIX binary readback.

The assembled run exited successfully. Its pre-build tracked snapshot lists
`bounded_reader.rs`, `chain.rs`, and the bounded-reader test. Snapshot SHA-256
values, including the tracked net-patch hash, are recorded in
`assembled-snapshot-hashes.sha256`.
The cached candidate build's named `cix` and `uncix` binary hashes are retained
in `assembled-binary-hashes.sha256`. The six boundary tests and existing
external-source-buffer test passed. The base and assembled candidate again
produced byte-identical gzip and bzip2 archives for the 1,200-byte periodic
input, and both fresh decoders matched its SHA-256.
