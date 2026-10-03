#!/usr/bin/env bash
# Prepared COND-CONTEXT-1 runner. Root supplies a scheduler lease and sealed
# paths before invoking it. This file is not executed during preparation.
set -euo pipefail

: "${RLIB:?set sealed libcix_native.rlib path}"
: "${DEPS:?set sealed dependency directory}"
: "${NUM_BIGINT_RLIB:?set sealed libnum_bigint rlib path}"
: "${NUM_TRAITS_RLIB:?set sealed libnum_traits rlib path}"
: "${WORK:?set scheduler-owned writable output directory}"

driver="$WORK/conditional-context-closure"
mkdir -p "$WORK"
rustc --edition=2021 \
  rust/cix-native/experiments/conditional-context-closure/conditional_context_closure.rs \
  --extern cix_native="$RLIB" \
  --extern num_bigint="$NUM_BIGINT_RLIB" \
  --extern num_traits="$NUM_TRAITS_RLIB" \
  -L dependency="$DEPS" -o "$driver"

for case in strong weak absent; do
  "$driver" generate "$case" "$WORK/$case.input"
  sha256sum "$WORK/$case.input" > "$WORK/$case.input.sha256"
done

for case in strong weak absent; do
  for variant in global context-1-4 context-2-8 raw; do
    stem="$WORK/$case-$variant"
    /usr/bin/time -v -o "$stem.encode.time" "$driver" encode "$variant" "$case" "$stem.cixctx" > "$stem.encode.json"
    /usr/bin/time -v -o "$stem.decode.time" "$driver" decode "$stem.cixctx" "$stem.restored" > "$stem.decode.json"
    sha256sum "$stem.cixctx" > "$stem.archive.sha256"
    sha256sum "$stem.restored" > "$stem.restored.sha256"
    cmp "$WORK/$case.input" "$stem.restored"
  done
done

# These are parser checks, outside the measured configuration rows.
cp "$WORK/strong-global.cixctx" "$WORK/bad-header.cixctx"
printf '\0' | dd of="$WORK/bad-header.cixctx" bs=1 count=1 conv=notrunc status=none
"$driver" reject "$WORK/bad-header.cixctx" > "$WORK/bad-header.reject.json"
head -c 12 "$WORK/strong-global.cixctx" > "$WORK/truncated.cixctx"
"$driver" reject "$WORK/truncated.cixctx" > "$WORK/truncated.reject.json"
