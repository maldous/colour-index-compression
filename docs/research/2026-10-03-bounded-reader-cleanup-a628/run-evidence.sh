#!/usr/bin/env bash
set -euo pipefail

readonly EXPERIMENT_ID=2026-10-03-bounded-reader-cleanup-a628
readonly CANDIDATE=/home/user/src/cix-bounded-reader-cleanup-a628
readonly BASE=/home/user/src/cix-final-validation-a628bda
readonly TOOLCHAIN=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin
readonly TARGET_BASE=/tmp/cix-bounded-reader-a628-target
readonly TARGET_CANDIDATE=/tmp/cix-bounded-reader-candidate-target
readonly BIN_BASE=/tmp/cix-bounded-reader-a628-bin
readonly BIN_CANDIDATE=/tmp/cix-bounded-reader-candidate-bin
readonly WORK=/tmp/cix-bounded-reader-evidence
readonly EVIDENCE=/home/user/src/cix-bounded-reader-cleanup-a628/docs/research/2026-10-03-bounded-reader-cleanup-a628

cd "$EVIDENCE"

printf 'experiment_id=%s\n' "$EXPERIMENT_ID"
printf 'service_pid=%s\n' "$$"
cg_path=$(awk -F: '$1 == "0" { print $3 }' /proc/self/cgroup)
printf 'service_cgroup=%s\n' "$cg_path"
for controller in memory.max memory.swap.max cpuset.cpus.effective; do
    printf '%s=' "$controller"
    cat "/sys/fs/cgroup${cg_path}/${controller}"
done
printf 'allowed_cpus='
awk '/Cpus_allowed_list/ { print $2 }' /proc/self/status

rm -rf "$TARGET_BASE" "$TARGET_CANDIDATE" "$BIN_BASE" "$BIN_CANDIDATE" "$WORK"
mkdir -p "$BIN_BASE" "$BIN_CANDIDATE" "$WORK"

env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" build --locked --manifest-path "$BASE/rust/cix-native/Cargo.toml" \
    --target-dir "$TARGET_BASE" --bin cix --bin uncix
env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" build --locked --manifest-path "$CANDIDATE/rust/cix-native/Cargo.toml" \
    --target-dir "$TARGET_CANDIDATE" --bin cix --bin uncix

cp "$TARGET_BASE/debug/cix" "$BIN_BASE/cix"
cp "$TARGET_BASE/debug/uncix" "$BIN_BASE/uncix"
cp "$TARGET_CANDIDATE/debug/cix" "$BIN_CANDIDATE/cix"
cp "$TARGET_CANDIDATE/debug/uncix" "$BIN_CANDIDATE/uncix"
sha256sum "$BIN_BASE/cix" "$BIN_BASE/uncix" "$BIN_CANDIDATE/cix" "$BIN_CANDIDATE/uncix" | tee binary-hashes.raw

env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" test --locked --manifest-path "$CANDIDATE/rust/cix-native/Cargo.toml" \
    --test bounded_reader -- --nocapture

for n in $(seq 1 80); do printf 'CIXG1\000periodic\377'; done > "$WORK/tiny-periodic.bin"

for backend in gzip bzip2; do
    "$BIN_BASE/cix" --external "$backend" --memory 64MiB -c "$WORK/tiny-periodic.bin" > "$WORK/a628-${backend}.cix"
    "$BIN_CANDIDATE/cix" --external "$backend" --memory 64MiB -c "$WORK/tiny-periodic.bin" > "$WORK/candidate-${backend}.cix"
    cmp "$WORK/a628-${backend}.cix" "$WORK/candidate-${backend}.cix"
    "$BIN_BASE/uncix" --memory 64MiB -c "$WORK/a628-${backend}.cix" > "$WORK/a628-${backend}.restored"
    "$BIN_CANDIDATE/uncix" --memory 64MiB -c "$WORK/candidate-${backend}.cix" > "$WORK/candidate-${backend}.restored"
    cmp "$WORK/tiny-periodic.bin" "$WORK/a628-${backend}.restored"
    cmp "$WORK/tiny-periodic.bin" "$WORK/candidate-${backend}.restored"
    sha256sum "$WORK/tiny-periodic.bin" "$WORK/a628-${backend}.cix" "$WORK/candidate-${backend}.cix" \
        "$WORK/a628-${backend}.restored" "$WORK/candidate-${backend}.restored"
done

env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" test --locked --manifest-path "$CANDIDATE/rust/cix-native/Cargo.toml" \
    --test external_source_buffer -- --nocapture
