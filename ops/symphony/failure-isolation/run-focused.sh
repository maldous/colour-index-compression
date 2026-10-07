#!/bin/bash
set -eu
cd /home/user/src/cix-approved-migration/native-source/elixir
proof=/home/user/src/cix-approved-migration/native-source/elixir/.cix243
cg=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
base=/sys/fs/cgroup$cg
printf 'cgroup=%s\n' "$cg" > "$proof/cgroup.txt"
cat "$base/memory.max" "$base/memory.swap.max" >> "$proof/cgroup.txt"
test "$(cat "$base/memory.max")" -le 2000000000
test "$(cat "$base/memory.swap.max")" = 0
case "$cg" in /cix.slice/cix-bau139.slice/*) ;; *) exit 90;; esac
taskset -pc 0 $$ >> "$proof/cgroup.txt"
rg Cpus_allowed_list /proc/self/status >> "$proof/cgroup.txt"
export CIX243_RUNTIME=/home/user/src/cix-morgan/symphony/pilot-v0.0.3/runtime-v2/install/runtime/.burrito/symphony_erts-16.4_0.0.3
export ROOTDIR="$CIX243_RUNTIME" BINDIR="$CIX243_RUNTIME/erts-16.4/bin" EMU=beam PROGNAME=erl ERL_FLAGS=''
set +e
"$BINDIR/erlexec" +S 1:1 -noshell -boot "$ROOTDIR/releases/0.0.3/start_clean" -boot_var RELEASE_LIB "$ROOTDIR/lib" -pa "$ROOTDIR"/lib/elixir-*/ebin -s elixir start_cli -extra .cix243/validate.exs > "$proof/focused.log" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$proof/exit-code.txt"
cat "$base/memory.peak" > "$proof/memory-peak.txt"
exit "$result"
