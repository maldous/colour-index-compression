#!/usr/bin/env bash
set -euo pipefail
root=/home/user/src/cix-perf-reader-audit
out="$root/docs/research/2026-10-02-rust-performance-audit/bounded-reader-allocation/raw"
cd "$root"
mkdir -p "$out"
cgroup=$(awk -F: '$1=="0" {print $3}' /proc/self/cgroup)
{
  taskset -pc $$
  for name in memory.max memory.swap.max cpuset.cpus.effective memory.peak; do
    printf '%s=' "$name"; cat "/sys/fs/cgroup$cgroup/$name"
  done
} > "$out/cgroup-before.txt"
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc \
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc \
env CARGO_BUILD_JOBS=2 cargo build --quiet --manifest-path "$root/rust/cix-native/Cargo.toml" --locked \
  --features audit-dhat --bin bounded-reader-allocation
bin="$root/rust/cix-native/target/debug/bounded-reader-allocation"
for mode in old new; do
  for size in 0 2048 65537 1048576; do
    stem="$out/$mode-$size"
    "$bin" "$mode" "$size" > "$stem.log" 2>&1
    cp dhat-heap.json "$stem.json"
  done
done
printf 'memory.peak=' > "$out/cgroup-after.txt"
cat "/sys/fs/cgroup$cgroup/memory.peak" >> "$out/cgroup-after.txt"
