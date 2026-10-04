#!/usr/bin/env sh
set -eu

package_name=$(printenv SQUASH_PKG_CONFIG_NAME || true)
api_version=$(printenv SQUASH_API_VERSION || true)
if [ -z "$package_name" ]; then package_name=squash-0.8; fi
if [ -z "$api_version" ]; then api_version=0.8; fi
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

if ! pkg-config --exists "$package_name"; then
  echo "Squash 0.8 development files were not found by pkg-config." >&2
  exit 1
fi

plugin_root=$(printenv SQUASH_PLUGIN_ROOT || true)
if [ -z "$plugin_root" ]; then
  plugin_root=$(pkg-config --variable=libdir "$package_name")/squash/$api_version/plugins
fi
plugin_dir=$plugin_root/cix
target_dir=$repo_root/target/release

cargo build --locked --release --manifest-path "$repo_root/Cargo.toml" --lib
install -d "$plugin_dir"
install -m 0755 "$target_dir/libcix_native.so" "$plugin_dir/libcix_native.so"
install -m 0644 "$repo_root/packaging/squash/squash.ini" "$plugin_dir/squash.ini"

# pkg-config output is a compiler/linker argument list by contract.
# shellcheck disable=SC2046
cc -std=c11 -fPIC -shared "$repo_root/packaging/squash/squash-cix.c" \
  $(pkg-config --cflags "$package_name") \
  -L"$plugin_dir" -lcix_native \
  $(pkg-config --libs "$package_name") \
  -Wl,-rpath,'$ORIGIN' \
  -o "$plugin_dir/libsquash$api_version-plugin-cix.so"
