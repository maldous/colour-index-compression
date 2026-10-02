#!/bin/bash
out=/home/user/src/colour-index-compression/benchmark-work/final-a628-validation
src=/home/user/src/cix-final-validation-a628bda/rust/cix-native
cg=$(sed -n 's/^0:://p' /proc/self/cgroup)
base=/sys/fs/cgroup
cd "$src" || exit 125
CARGO_BUILD_JOBS=2 \
RUSTC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc \
RUSTDOC=/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustdoc \
CARGO_TARGET_DIR=/home/user/src/cix-final-validation-a628bda/rust/cix-native/target-qualified \
taskset -c 10,11 /home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo bench --locked --all-features --profile release-lto --bench ppm_borrow_kernel -- --test > "$out/logs/criterion.log" 2>&1 &
p=$!
while kill -0 "$p" 2>/dev/null; do
  printf 'pid=%s\n' "$p" >> "$out/logs/criterion-children.log"
  cat "/proc/$p/cgroup" >> "$out/logs/criterion-children.log" 2>/dev/null || true
  taskset -pc "$p" >> "$out/logs/criterion-children.log" 2>&1 || true
  sleep 1
done
wait "$p"
rc=$?
printf 'scope=%s\nmemory.max=%s\nmemory.swap.max=%s\ncriterion_rc=%s\npeak=%s\n' "$cg" "$(cat "$base$cg/memory.max")" "$(cat "$base$cg/memory.swap.max")" "$rc" "$(cat "$base$cg/memory.peak")" > "$out/logs/criterion-cgroup.log"
printf 'exit=%s\n' "$rc" > "$out/logs/criterion.exit"
exit "$rc"
