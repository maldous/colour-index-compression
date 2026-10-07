#!/bin/bash
set -eu
set +x
root=/home/user/src/cix-approved-migration/cix245-compatibility-candidate
cg=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
case "$cg" in /cix.slice/cix-bau139.slice/cix245-compatibility-v1.service) ;; *) exit 90;; esac
base=/sys/fs/cgroup$cg
test "$(cat "$base/memory.max")" -le 2000000000
test "$(cat "$base/memory.swap.max")" = 0
printf '%s\n' "$cg" > "$root/cgroup.txt"
cat "$base/memory.max" "$base/memory.swap.max" >> "$root/cgroup.txt"
taskset -pc 0 $$ >> "$root/cgroup.txt"
runtime=/home/user/src/cix-approved-migration/runtime-cix243-v2
set +e
env -i PATH=/usr/bin:/bin ROOTDIR="$runtime" BINDIR="$runtime/erts-16.4/bin" EMU=beam PROGNAME=erl \
 "$runtime/erts-16.4/bin/erl" +S 1:1 -noshell -boot "$runtime/releases/0.0.3/start_clean" \
 -boot_var RELEASE_LIB "$runtime/lib" -pa "$runtime"/lib/elixir-*/ebin -s elixir start_cli \
 -extra "$root/validate.exs" > "$root/focused.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$root/exit-code.txt"
cat "$base/memory.peak" > "$root/memory-peak.txt"
exit "$code"
