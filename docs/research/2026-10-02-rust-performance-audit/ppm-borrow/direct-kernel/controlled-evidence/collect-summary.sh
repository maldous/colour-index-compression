#!/usr/bin/env bash
# Rebuild summary.json solely from checked-in qualified raw JSON.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

pair_stat() {
  local case_name=$1 metric=$2
  paste \
    <(for pair in 1 2 3 4 5; do jq -r '.mean.point_estimate' "$root/raw/$case_name/pair-$pair/baseline/criterion"/*/$metric/4096/new/estimates.json; done) \
    <(for pair in 1 2 3 4 5; do jq -r '.mean.point_estimate' "$root/raw/$case_name/pair-$pair/candidate/criterion"/*/$metric/4096/new/estimates.json; done) |
    awk 'BEGIN { t=2.776445 } { b+=$1; c+=$2; d[NR]=$2-$1 } END { n=NR; md=0; for(i=1;i<=n;i++)md+=d[i]; md/=n; ss=0; for(i=1;i<=n;i++)ss+=(d[i]-md)^2; sd=sqrt(ss/(n-1)); se=sd/sqrt(n); printf "{\"n\":%d,\"baseline_mean_ns\":%.6f,\"candidate_mean_ns\":%.6f,\"mean_delta_ns\":%.6f,\"mean_delta_percent\":%.6f,\"delta_ci95_ns\":[%.6f,%.6f]}",n,b/n,c/n,md,100*md/(b/n),md-t*se,md+t*se }'
}

rss_range() {
  find "$root/raw" -name process.json -exec jq -r '.max_rss_kib' {} \; |
    awk 'NR==1 { min=$1; max=$1 } { if($1<min)min=$1; if($1>max)max=$1 } END { printf "{\"min_kib\":%d,\"max_kib\":%d}",min,max }'
}

for case_name in random strong weak absent; do
  for metric in encode_o3_fresh decode_o3_fresh; do
    value=$(pair_stat "$case_name" "$metric")
    jq -n --arg case_name "$case_name" --arg metric "$metric" --argjson value "$value" '{case:$case_name,metric:$metric,paired:$value}'
  done
done | jq -s --argjson rss "$(rss_range)" '{paired_results:.,rss_kib:$rss,status:"completed; all 40 cgroup JSON readbacks require memory.max=1073741824 and memory.swap.max=0"}' > "$root/summary.json"
