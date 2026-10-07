#!/usr/bin/env bash
set -euo pipefail

# FCBench's authoritative README identifies each of its 33 raw files by a
# Google Drive ID and separately declares its scalar type and shape. This
# script preserves the source file bytes; it never changes dtype, byte order
# or layout. It is resumable through gdown's --continue option.
repo_root=$(cd "$(dirname "$0")/.." && pwd)
dataset_root=${CIX_DATASET_ROOT:-/home/user/cix-datasets}
destination="$dataset_root/originals/fcbench"
tool_path="$dataset_root/working/python-tools"
table="$repo_root/docs/research/2026-09-30-dataset-preparation/fcbench-files.tsv"
minimum_free_bytes=$((30 * 1024 * 1024 * 1024))
mkdir -p "$destination"

while IFS=$'\t' read -r name file_id dtype shape bytes category; do
  [[ -z "$name" || "$name" = \#* ]] && continue
  target="$destination/$name"
  if [[ -f "$target" && $(stat -c%s "$target") = "$bytes" ]]; then
    continue
  fi
  if [[ -f "$target" ]]; then
    printf 'existing size mismatch for %s: expected %s got %s; retained without overwrite\n' \
      "$name" "$bytes" "$(stat -c%s "$target")" >&2
    continue
  fi
  available_bytes=$(df --output=avail -B1 "$destination" | tail -n 1 | tr -d ' ')
  if (( available_bytes < minimum_free_bytes )); then
    printf 'stopping before %s: only %s bytes free; retaining a 30 GiB safety reserve\n' \
      "$name" "$available_bytes" >&2
    exit 2
  fi
  PYTHONPATH="$tool_path" python3 -m gdown --continue --retries 3 --timeout 60 \
    "https://drive.google.com/uc?id=$file_id" -O "$target"
  [[ $(stat -c%s "$target") = "$bytes" ]] || printf \
    'download size mismatch for %s: expected %s got %s; retained for audit\n' \
    "$name" "$bytes" "$(stat -c%s "$target")" >&2
done < "$table"
