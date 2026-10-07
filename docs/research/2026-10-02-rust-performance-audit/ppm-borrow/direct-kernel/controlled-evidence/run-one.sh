#!/usr/bin/env bash
set -euo pipefail
case_name=$1
cpu=$2
binary=$3
run_dir=$4
mkdir -p "$run_dir"
systemd-run --user --scope --quiet --collect -p MemoryMax=1073741824 -p MemorySwapMax=0 -- \
  bash -c 'cg=$(cut -d: -f3 /proc/self/cgroup); jq -n --arg cgroup "$cg" --arg memory_max "$(cat /sys/fs/cgroup${cg}/memory.max)" --arg memory_swap_max "$(cat /sys/fs/cgroup${cg}/memory.swap.max)" "{cgroup:\$cgroup,memory_max:\$memory_max,memory_swap_max:\$memory_swap_max}" > "$4/cgroup.json"; exec taskset -c "$2" /usr/bin/time -f "{\"elapsed_seconds\":%e,\"user_seconds\":%U,\"system_seconds\":%S,\"max_rss_kib\":%M,\"exit_status\":%x}" -o "$4/process.json" env CIX_AUDIT_CASE="$1" CIX_AUDIT_CRITERION_DIR="$4/criterion" "$3" --bench --noplot --sample-size 10 --warm-up-time 0.05 --measurement-time 0.2' \
  _ "$case_name" "$cpu" "$binary" "$run_dir" >"$run_dir/stdout.log" 2>"$run_dir/stderr.log"
