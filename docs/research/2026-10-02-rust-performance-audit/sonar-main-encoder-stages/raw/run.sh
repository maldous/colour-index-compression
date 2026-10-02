#!/usr/bin/env bash
set -euo pipefail

# Exact d52 parent/candidate route parity under a 1 GiB, no-swap cgroup and taskset CPU 12.
# The temporary input, archives, and restored bytes deliberately remain outside Git.
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d /tmp/cix-main-encoder-stages.XXXXXX)
trap 'rm -rf "$work"' EXIT
parent=/home/user/src/cix-current-validation-d52/rust/cix-native/target/release
candidate=/home/user/src/cix-sonar-main-encoders-d52/rust/cix-native/target/release
: > "$root/archive-hashes.txt"

python3 - "$work/input.bin" <<'PY'
import sys
path = sys.argv[1]
data = (bytes(range(256)) * 8 + b"abcabcabcabcabcabc" * 256 + b"\0\xff" * 512)
open(path, "wb").write(data)
PY

{
  printf 'parent_source=d52fa7f72\n'
  printf 'candidate_source=0f8bda5bb5c99d1b2c6d93bd93637f501d15e017\n'
  sha256sum "$work/input.bin" "$parent/cix" "$parent/uncix" "$candidate/cix" "$candidate/uncix"
  ldd "$parent/cix"
  ldd "$candidate/cix"
} > "$root/identities.txt"

run_child() {
  local name=$1; shift
  printf '%q ' "$@" > "$root/$name.command"
  printf '\n' >> "$root/$name.command"
  systemd-run --user --scope --expand-environment=no \
    -p MemoryMax=1073741824 -p MemorySwapMax=0 \
    taskset -c 12 bash -c '
      cg=$(cut -d: -f3 /proc/self/cgroup)
      printf "cgroup=%s\n" "$cg"
      printf "memory.max="; cat "/sys/fs/cgroup$cg/memory.max"
      printf "memory.swap.max="; cat "/sys/fs/cgroup$cg/memory.swap.max"
      if test -r "/sys/fs/cgroup$cg/cpuset.cpus.effective"; then
        printf "cpuset.cpus.effective="; cat "/sys/fs/cgroup$cg/cpuset.cpus.effective"
      else
        printf "cpuset.cpus.effective=unavailable\n"
      fi
      printf "affinity="; taskset -pc $$
      "$@"
      status=$?
      printf "exit=%s\n" "$status"
      exit "$status"
    ' bash "$@" > "$root/$name.stdout" 2> "$root/$name.stderr"
}

for route in predictor lz; do
  run_child "$route.parent.encode" "$parent/cix" --format cixg1 --route "$route" --explain -o "$work/$route.parent.cix" "$work/input.bin"
  run_child "$route.candidate.encode" "$candidate/cix" --format cixg1 --route "$route" --explain -o "$work/$route.candidate.cix" "$work/input.bin"
  cmp "$work/$route.parent.cix" "$work/$route.candidate.cix"
  sha256sum "$work/$route.parent.cix" "$work/$route.candidate.cix" >> "$root/archive-hashes.txt"
  wc -c "$work/$route.parent.cix" "$work/$route.candidate.cix" >> "$root/archive-hashes.txt"
  run_child "$route.parent.decode-candidate" "$parent/uncix" -o "$work/$route.parent.restore" "$work/$route.candidate.cix"
  run_child "$route.candidate.decode-parent" "$candidate/uncix" -o "$work/$route.candidate.restore" "$work/$route.parent.cix"
  cmp "$work/input.bin" "$work/$route.parent.restore"
  cmp "$work/input.bin" "$work/$route.candidate.restore"
  head -c 1 "$work/$route.parent.cix" > "$work/$route.truncated.cix"
  if run_child "$route.candidate.malformed" "$candidate/uncix" -o "$work/$route.bad.restore" "$work/$route.truncated.cix"; then
    printf 'unexpected successful malformed decode\n' >&2
    exit 1
  fi
done
