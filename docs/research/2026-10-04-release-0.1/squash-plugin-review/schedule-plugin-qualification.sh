#!/usr/bin/env bash
# Root-owned schedule only: do not run until an actual Squash 0.8 SDK is installed.
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 REPOSITORY FROZEN_LIBCIX_NATIVE FIXTURE NEW_WORK_DIRECTORY" >&2
  exit 64
fi

repo_root=$1
frozen_library=$2
fixture=$3
work_dir=$4
pkg=squash-0.8

if ! pkg-config --exists "$pkg"; then
  echo "SKIP: Squash 0.8 SDK is unavailable; plugin loading remains unqualified" >&2
  exit 77
fi
if ! command -v squash >/dev/null; then
  echo "SKIP: Squash 0.8 command-line tool is unavailable" >&2
  exit 77
fi
if [[ ! -f $frozen_library || ! -f $fixture ]]; then
  echo "frozen CIX library and fixture must be regular files" >&2
  exit 66
fi
if [[ -e $work_dir ]]; then
  echo "refusing to reuse or overwrite evidence directory: $work_dir" >&2
  exit 73
fi
if [[ ! -f $repo_root/squash/squash-cix.c || ! -f $repo_root/squash/squash.ini ]]; then
  echo "CIX Squash shim sources are unavailable" >&2
  exit 66
fi

api=0.8
plugin_root="$work_dir/plugins"
plugin_dir="$plugin_root/cix"
mkdir -p "$plugin_dir"
cp "$frozen_library" "$plugin_dir/libcix_native.so"
cp "$repo_root/squash/squash.ini" "$plugin_dir/squash.ini"

# Deliberate word splitting: pkg-config emits compiler/linker arguments.
# shellcheck disable=SC2046
cc -std=c11 -fPIC -shared "$repo_root/squash/squash-cix.c" \
  $(pkg-config --cflags "$pkg") \
  -L"$plugin_dir" -lcix_native \
  $(pkg-config --libs "$pkg") \
  -Wl,-rpath,'$ORIGIN' \
  -o "$plugin_dir/libsquash$api-plugin-cix.so"

fixture_sha256=$(sha256sum "$fixture" | awk '{print $1}')
for level in 1 6 9; do
  archive="$work_dir/level-$level.cix"
  restored="$work_dir/level-$level.restored"
  SQUASH_PLUGINS="$plugin_root" squash -k -c cix -"$level" "$fixture" "$archive"
  SQUASH_PLUGINS="$plugin_root" squash -k -d -c cix "$archive" "$restored"
  cmp "$fixture" "$restored"
  printf '%s  %s\n' "$(sha256sum "$archive" | awk '{print $1}')" "$(basename "$archive")" >> "$work_dir/archives.sha256"
done

{
  printf 'purpose=QuixDB Squash 0.8 plugin load and stream round-trip; not Linux SquashFS\n'
  printf 'squash_pkg=%s\n' "$(pkg-config --modversion "$pkg")"
  printf 'fixture_sha256=%s\n' "$fixture_sha256"
  printf 'frozen_library_sha256=%s\n' "$(sha256sum "$frozen_library" | awk '{print $1}')"
  printf 'levels=1,6,9\n'
} > "$work_dir/evidence.properties"

echo "PASS: optional QuixDB Squash 0.8 plugin round trips passed; no SquashFS claim"
