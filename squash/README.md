# Squash plugin

This directory provides a native plugin for the quixdb Squash codec API. It
registers the codec name `cix`, reports a conservative compressed-size bound,
and implements Squash's splice interface. The splice callback drives the Rust
CIXG1 streaming encoder or decoder through a C ABI. It does not start a Python
process or buffer the complete source before encoding. Squash option `level`
maps to CIX levels 1–9; the default is 6.

## Build and install

Install Squash 0.8 development files and `pkg-config`, then run:

```sh
./squash/build-plugin.sh
```

The script builds the Rust release library and installs the shim, Rust shared
library and `squash.ini` under the plugin directory reported by `pkg-config`.
Set `SQUASH_PLUGIN_ROOT` to install into a user-writable plugin directory, and
`SQUASH_API_VERSION` if using a Squash API version other than 0.8. Use
`SQUASH_PLUGINS=/path/to/plugins` to select that plugin directory at runtime.

## Examples

```sh
squash -k -c cix -6 input.bin input.cix
squash -k -d -c cix input.cix restored.bin
cmp input.bin restored.bin
```

The archive is a CIXG1 stream (`.cix`), not ZIP or gzip. The Squash integration
uses independent 32 KiB CIXG1 frames and preserves normal Squash file/pipe
backpressure through its splice callbacks. Test dataset fixtures used to
validate the plugin are correctness inputs only. Compression data comparisons
remain restricted to Silesia.

## Current host status

The Rust shared library and its `cix_squash_splice` callbacks passed a fresh-process
partial-read/write round trip and error checks at source
`ee6b4396df760d19005c4e0800783fef58d52334`. The checked-in host library is
`dist/libcix_native.so`; its binary identity is in `dist/native-release.json`.
The Squash 0.8 development SDK is absent on this host, so the shim/plugin has
not been built or loaded in this checkpoint. The ABI currently uses one worker
and 32 KiB blocks, whereas the ordinary CLI defaults to up to four block workers
and uses larger BEST blocks. Plugin and ordinary CLI measurements must record
those differences. See the [ABI evidence](../docs/research/2026-10-01-cix-optimization/native-ffi-final-smoke.md).
