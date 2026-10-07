# Final combined validation invocation

Status: prepared only. Replace `REVISION` only after root freezes the final
merged source. The worktree and output identity must be new for that exact
revision; do not reuse 45e7 artifacts or receipts.

```text
git worktree add --detach /home/user/src/cix-final-validation-REVISION REVISION
git rev-parse REVISION^{commit}
git rev-parse REVISION^{tree}
```

Run each build, suite, and Criterion phase in a fresh system scope using
`sudo -n systemd-run --scope --uid=user` with `MemoryMax=2147483648`,
`MemorySwapMax=0`, and `AllowedCPUs=10 11`; prefix the direct stable cargo
command with `taskset -c 10,11`. Set all of these explicitly:

```text
CARGO_BUILD_JOBS=2
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc
CARGO_TARGET_DIR=<new-worktree>/rust/cix-native/target-qualified
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo
```

Build command:

```text
cargo build --locked --all-features --profile release-lto --bin cix --bin uncix --bin cixcat --lib -j2
```

Suite command, with an outer `timeout --signal=TERM 1200` and
`-- --test-threads=1`:

```text
cargo test --locked --all-features --profile release-lto --lib --bins --tests --examples -j2
```

Criterion stays separate:

```text
cargo bench --locked --all-features --profile release-lto --bench ppm_borrow_kernel -- --test
```

For every phase, retain outer exit receipt, `/proc/<cargo-and-rustc-pid>/cgroup`
and `taskset -pc` samples, scope memory/swap/peak readback, raw stdout/stderr,
and the exact command. Copy read-only `cix`, `uncix`, `cixcat`, and
`libcix_native.so` to a new external checkpoint; hash those files and every
path resolved by `ldd cix`. Copy textual metadata and raw receipts into a new
tracked evidence directory. A nonzero exit, missing child receipt, incorrect
scope, CPU affinity, memory limit, swap limit, or source/tree mismatch remains
an explicit incomplete result.
