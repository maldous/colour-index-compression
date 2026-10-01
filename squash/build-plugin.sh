#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pkg="${SQUASH_PKG_CONFIG_NAME:-squash-0.8}"
if ! pkg-config --exists "$pkg"; then
  echo "build-plugin: pkg-config could not find $pkg" >&2
  exit 2
fi

api="${SQUASH_API_VERSION:-0.8}"
plugin_root="${SQUASH_PLUGIN_ROOT:-$(pkg-config --variable=libdir "$pkg")/squash/$api/plugins}"
plugin_dir="$plugin_root/cix"
target_dir="$repo_root/rust/cix-native/target/release"

cargo build --release --manifest-path "$repo_root/rust/cix-native/Cargo.toml"
mkdir -p "$plugin_dir"
cp "$target_dir/libcix_native.so" "$plugin_dir/libcix_native.so"
cp "$repo_root/squash/squash.ini" "$plugin_dir/squash.ini"

# pkg-config flags are compiler arguments; deliberate word splitting is needed.
# shellcheck disable=SC2086
cc -std=c11 -fPIC -shared "$repo_root/squash/squash-cix.c" \
  $(pkg-config --cflags "$pkg") \
  -L"$plugin_dir" -lcix_native \
  $(pkg-config --libs "$pkg") \
  -Wl,-rpath,'$ORIGIN' \
  -o "$plugin_dir/libsquash$api-plugin-cix.so"

echo "Installed Squash CIX plugin to $plugin_dir"
