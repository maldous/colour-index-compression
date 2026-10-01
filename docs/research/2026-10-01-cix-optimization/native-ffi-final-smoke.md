# Native C ABI final smoke — current Unix host

Date: 2026-10-01

## Scope

This is a local correctness smoke of the exported Rust shared-library entry
point, not a Squash plugin qualification or a compression benchmark. It used
the release-LTO library built from source revision
`ee6b4396df760d19005c4e0800783fef58d52334`:

```text
rust/cix-native/target/release-lto/libcix_native.so
SHA-256 d7918dfc8f9a550beff20aafe0610b8f34dc9f2266329738e351de4e3485de8d
size     1,194,112 bytes
```

`nm -D --defined-only` reported the expected exported symbol:

```text
000000000009efb0 T cix_squash_splice
```

The host has no Squash 0.8 development package:

```text
pkg-config --modversion squash-0.8
Package squash-0.8 was not found ...
```

Therefore the C shim was not compiled and no claim is made about loading or
qualifying the Squash plugin. No download, dataset acquisition, or benchmark
input was used.

## Harness

[`tests/native_ffi_smoke.c`](../../../tests/native_ffi_smoke.c) is the
source-only harness used for this smoke. It was compiled with the host C
compiler against this exact shared library. It declares only the documented C
ABI:

```c
int32_t cix_squash_splice(int32_t direction, int32_t level,
                          CixRead read_cb, CixWrite write_cb, void *user);
```

To rebuild against the packaged library, set `LIBDIR` to the directory
containing the supplied `libcix_native.so`. The first command applies to a
packaged `dist/` directory; the second is the command used for the current
release-LTO build.

```sh
LIBDIR="$PWD/dist"
# LIBDIR="$PWD/rust/cix-native/target/release-lto"
cc -O2 -std=c11 -Wall -Wextra -Werror tests/native_ffi_smoke.c \
  -L"$LIBDIR" -Wl,-rpath,"$LIBDIR" -lcix_native -o /tmp/cix_ffi_smoke
```

The harness generated a 131,071-byte synthetic mixed byte sequence. Its read
callback returned irregular chunks of 1, 7, 113, 2, 4093, 31, 8191, 5, and
257 bytes. Its write callback accepted only irregular partial chunks of 3, 1,
79, 5, 4096, 13, and 257 bytes. This exercised callback partial-read and
partial-write handling without using a corpus input.

The encoder and decoder were separate harness process invocations. The fresh
decoder consumed the physical archive written by the encoder. The commands
were:

```sh
/tmp/cix_ffi_smoke make /tmp/cix_ffi_input.bin
/tmp/cix_ffi_smoke encode /tmp/cix_ffi_input.bin /tmp/cix_ffi_archive.cix
/tmp/cix_ffi_smoke decode /tmp/cix_ffi_archive.cix /tmp/cix_ffi_restored.bin
cmp /tmp/cix_ffi_input.bin /tmp/cix_ffi_restored.bin
/tmp/cix_ffi_smoke errors
```

## Result

```text
direction=1 level=6 status=1 input=131071 output=2835 read_callbacks=107 write_callbacks=38
direction=2 level=6 status=1 input=2835 output=131071 read_callbacks=46 write_callbacks=222
```

The original and fresh-decoded outputs both had SHA-256
`a21b2e46717cd64e0f6637a5e6b9e234cdba72c7bccaa55ba658e7df1812d921`.
The archive had SHA-256
`3bff0a577fa96a17a157d7229640f3d789a5965dc2d0643e8185ce23b26af5e3`.
Its first 13 bytes were:

```text
43 49 58 47 31 00 80 00 00 00 00 00 00
```

This is a CIXG1 header with a 32 KiB block size. Exact restoration was also
checked by `cmp`.

The error path smoke returned `-1` for each of a failing read callback, a
failing write callback, a truncated decode input, and compression level zero:

```text
error_statuses read=-1 write=-1 truncated_decode=-1 invalid_level=-1
```

## ABI settings and CLI comparison

The Rust entry point accepts compression directions `1` and `2`; successful
calls return `1` and every exercised error path returned `-1`. For compression it
accepts levels 1 through 9. The C Squash shim declares level 6 as its default.

At level 6, the ABI calls the native encoder with: 32 KiB blocks; route unset;
backend string `hybrid` with `backend_set = false`; format `auto`; no input fd
polling; no idle flush interval; a 512 MiB estimated working-memory budget;
one worker; and no explain or verbose output. This produced CIXG1 for this
smoke input.

The ordinary `cix` CLI default also starts at level 6, 32 KiB blocks, a 512
MiB memory setting, automatic route selection, automatic format, and the
`hybrid` backend default. It normally selects up to four block workers from
available CPU parallelism, while the ABI fixes one worker. The ABI smoke thus
does not establish byte identity with a multiworker CLI run, timing,
throughput, memory, or compression-ratio parity. It establishes callback ABI
round-trip behavior on this host library only.

The shared object linked successfully on this host with its native codec
dependencies present, including bzip2, lzma, zstd, Brotli decoder, and zlib.
