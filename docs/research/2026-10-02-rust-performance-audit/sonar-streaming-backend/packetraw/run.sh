#!/bin/sh
set -eu
root=/tmp/cix-streaming-2cb
out=/tmp/stream-audit-rerun
mkdir -p "$out"
cd "$root/rust/cix-native"
cargo check --lib
cargo build --bin cix --bin uncix
printf 'persistent stream fixture %.0s' $(seq 1 128) > "$out/input"
./target/debug/cix --stream --format cixg1 -f -o "$out/archive" "$out/input"
./target/debug/uncix -f -o "$out/output" "$out/archive"
cp "$out/archive" "$out/truncated"
truncate -s -1 "$out/truncated"
if ./target/debug/uncix -f -o "$out/bad" "$out/truncated"; then exit 1; else echo truncation_rejected; fi
sha256sum "$out/input" "$out/archive" "$out/output" target/debug/cix target/debug/uncix
git -C "$root" diff 2cb5716b6 -- rust/cix-native/src/streaming_backend.rs | sha256sum
