#!/usr/bin/env bash
set -euo pipefail

readonly EXPERIMENT_ID=2026-10-03-bounded-reader-assembled-a628
readonly BASE=a628bda23e09bb43cceefa2d9e29009fbcc1df67
readonly CANDIDATE=/home/user/src/cix-bounded-reader-cleanup-a628
readonly TOOLCHAIN=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin
readonly TARGET=/tmp/cix-bounded-reader-candidate-target
readonly BASE_BIN=/tmp/cix-bounded-reader-a628-bin
readonly CANDIDATE_BIN=/tmp/cix-bounded-reader-assembled-bin
readonly WORK=/tmp/cix-bounded-reader-assembled-evidence
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
/bin/bash -c 'child_path=$(awk -F: '\''$1 == "0" { print $3 }'\'' /proc/self/cgroup); printf "service_child_cgroup=%s\\n" "$child_path"; printf "service_child_allowed_cpus="; awk '\''/Cpus_allowed_list/ { print $2 }'\'' /proc/self/status'

git -C "$CANDIDATE" diff --binary "$BASE" > assembled-tracked-net.patch
git -C "$CANDIDATE" diff --name-status "$BASE" > assembled-tracked-paths.raw
git -C "$CANDIDATE" diff --name-only "$BASE" > assembled-tracked-path-list.raw
{
    while IFS= read -r path; do
        git -C "$CANDIDATE" show "$BASE:$path" | sha256sum | sed "s|  -$|  $BASE:$path|"
        sha256sum "$CANDIDATE/$path" | sed "s|  .*|  assembled:$path|"
    done < assembled-tracked-path-list.raw
} > assembled-source-hashes.sha256
sha256sum assembled-tracked-net.patch assembled-tracked-paths.raw assembled-source-hashes.sha256 > assembled-snapshot-hashes.sha256

rm -rf "$CANDIDATE_BIN" "$WORK"
mkdir -p "$CANDIDATE_BIN" "$WORK"
env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" build --locked --manifest-path "$CANDIDATE/rust/cix-native/Cargo.toml" \
    --target-dir "$TARGET" --bin cix --bin uncix
cp "$TARGET/debug/cix" "$CANDIDATE_BIN/cix"
cp "$TARGET/debug/uncix" "$CANDIDATE_BIN/uncix"
sha256sum "$BASE_BIN/cix" "$BASE_BIN/uncix" "$CANDIDATE_BIN/cix" "$CANDIDATE_BIN/uncix" > assembled-binary-hashes.sha256

env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" test --locked --manifest-path "$CANDIDATE/rust/cix-native/Cargo.toml" \
    --target-dir "$TARGET" --test bounded_reader -- --nocapture

for n in $(seq 1 80); do printf 'CIXG1\000periodic\377'; done > "$WORK/tiny-periodic.bin"
for backend in gzip bzip2; do
    "$BASE_BIN/cix" --external "$backend" --memory 64MiB -c "$WORK/tiny-periodic.bin" > "$WORK/a628-${backend}.cix"
    "$CANDIDATE_BIN/cix" --external "$backend" --memory 64MiB -c "$WORK/tiny-periodic.bin" > "$WORK/assembled-${backend}.cix"
    cmp "$WORK/a628-${backend}.cix" "$WORK/assembled-${backend}.cix"
    "$BASE_BIN/uncix" --memory 64MiB -c "$WORK/a628-${backend}.cix" > "$WORK/a628-${backend}.restored"
    "$CANDIDATE_BIN/uncix" --memory 64MiB -c "$WORK/assembled-${backend}.cix" > "$WORK/assembled-${backend}.restored"
    cmp "$WORK/tiny-periodic.bin" "$WORK/a628-${backend}.restored"
    cmp "$WORK/tiny-periodic.bin" "$WORK/assembled-${backend}.restored"
    sha256sum "$WORK/tiny-periodic.bin" "$WORK/a628-${backend}.cix" "$WORK/assembled-${backend}.cix" \
        "$WORK/a628-${backend}.restored" "$WORK/assembled-${backend}.restored"
done

env RUSTC="$TOOLCHAIN/rustc" RUSTDOC="$TOOLCHAIN/rustdoc" \
    "$TOOLCHAIN/cargo" test --locked --manifest-path "$CANDIDATE/rust/cix-native/Cargo.toml" \
    --target-dir "$TARGET" --test external_source_buffer -- --nocapture
