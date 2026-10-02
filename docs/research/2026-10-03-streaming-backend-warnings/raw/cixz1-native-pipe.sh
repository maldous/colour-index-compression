#!/usr/bin/env bash
set -euo pipefail

repo=/home/user/src/cix-streaming-backend-warnings-clean
raw="$repo/docs/research/2026-10-03-streaming-backend-warnings/raw"
bin="$repo/target-streaming/release"
input="$raw/cixz1-native-pipe.input.rs"
archive="$raw/cixz1-native-pipe.archive"
output="$raw/cixz1-native-pipe.restored.rs"

cp "$repo/rust/cix-native/src/streaming_backend.rs" "$input"
cat "$input" | "$bin/cix" --best --stream --threads 1 --memory 2GiB --block-size 64KiB -c - > "$archive"
test "$(head -c 5 "$archive")" = CIXZ1
cat "$archive" | "$bin/uncix" --stream -c - > "$output"
cmp -s "$input" "$output"
sha256sum "$bin/cix" "$bin/uncix" "$input" "$archive" "$output" > "$raw/cixz1-native-pipe.sha256"
