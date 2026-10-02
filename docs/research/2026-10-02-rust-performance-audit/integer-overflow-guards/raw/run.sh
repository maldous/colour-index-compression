#!/bin/bash
set -u
export RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc
export RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc
export CARGO_TARGET_DIR=/home/user/src/colour-index-compression/benchmark-work/integer-overflow-5b/target
cd /tmp/cix-integer-overflow-5b
cg=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
printf 'cgroup=%s\n' "$cg"
for field in memory.max memory.swap.max cpuset.cpus.effective; do printf '%s=' "$field"; cat "/sys/fs/cgroup$cg/$field"; done
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo test --locked --manifest-path rust/cix-native/Cargo.toml --lib overflow -j1 -- --test-threads=1
rc=$?
printf 'test_exit=%s\n' "$rc"
printf 'memory.peak='; cat "/sys/fs/cgroup$cg/memory.peak"
exit "$rc"
