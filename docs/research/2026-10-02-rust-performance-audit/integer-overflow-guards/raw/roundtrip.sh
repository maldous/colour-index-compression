#!/bin/bash
set -u
export RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc
export RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc
export CARGO_TARGET_DIR=/home/user/src/colour-index-compression/benchmark-work/integer-overflow-5b/target
cd /tmp/cix-integer-overflow-5b
cg=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
printf 'cgroup=%s\n' "$cg"
for field in memory.max memory.swap.max cpuset.cpus.effective; do printf '%s=' "$field"; cat "/sys/fs/cgroup$cg/$field"; done
rc=0
for filter in adaptive::tests stateful::tests fixedmix::tests wavelet::tests expertmix::tests legacy_lz::tests numeric::tests histogram::tests; do
 /home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo test --locked --manifest-path rust/cix-native/Cargo.toml --lib "$filter" -j1 -- --test-threads=1
 phase_rc=$?
 printf 'filter=%s exit=%s\n' "$filter" "$phase_rc"
 if [ "$phase_rc" -ne 0 ]; then rc="$phase_rc"; break; fi
done
printf 'test_exit=%s\n' "$rc"
printf 'memory.peak='; cat "/sys/fs/cgroup$cg/memory.peak"
exit "$rc"
