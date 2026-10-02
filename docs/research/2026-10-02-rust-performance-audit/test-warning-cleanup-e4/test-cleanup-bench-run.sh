#!/bin/bash
set -u
export RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc
export RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc
export CARGO_TARGET_DIR=/home/user/src/colour-index-compression/benchmark-work/integer-overflow-5b/target
cd /home/user/src/colour-index-compression
taskset -pc $$
"$RUSTC" --version
cg=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
for field in memory.max memory.swap.max cpuset.cpus.effective; do echo "$field"; cat "/sys/fs/cgroup$cg/$field"; done
/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo test --locked --manifest-path rust/cix-native/Cargo.toml --bench ppm_eligible_kernel -j1 -- --test
rc=$?
echo "test_exit=$rc"
cat "/sys/fs/cgroup$cg/memory.peak"
exit "$rc"
