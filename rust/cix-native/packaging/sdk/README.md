# CIX native SDK package skeleton

This is a source-side installation helper for the current **native-buffer-v1**
ABI. It installs `cix.h`, `cix_stream.h`, the C++17 RAII convenience header
`cix.hpp`, one already-built `libcix_native` library, `find_package(CIX CONFIG)` metadata, and
`pkg-config` metadata. It does not build Rust itself, create an SDK artifact, or
qualify an installed consumer.

## Capability boundary

The installed `CIX::native` target exposes process-free, complete-buffer
operations from `cix.h`: option defaults, opaque contexts, encode, decode and
context diagnostics. Calls on a context are serialized; different contexts may
be used concurrently. The complete-buffer ABI does not provide incremental process/flush/finish/reset
calls, callbacks, hard process-RSS limits, cancellation-handle transfer, or
full-engine/same-CIX worker selection. The package configuration identifies it
as `native-buffer-v1`.

`cix_stream.h` separately exposes the native independent-block `CIXG1` stream
API: opaque encoder/decoder handles plus process, flush, finish and reset. It
is not a full-engine route, retained-history decoder, specialist selector, or
streaming archive adapter. The installed C stream consumer in
`packaging/sdk/tests/c_stream_installed_consumer.c` exercises fragmented input
and output using only public C headers.

A library found through `CIX::native` is not proof that PAQ/JXL bridges,
historical full-engine decoders, automatic specialist selection, platform
adapters or a full CIX release candidate are present. The full-engine source
export remains blocked by the dependency-closure rule in
`packaging/export/source-allowlist.json`.

## Prepare an install tree after a selected native build

Do not run this command until a selected library exists and its dependency
closure has been recorded. For a shared Linux build, for example:

```sh
cmake -S packaging/sdk -B sdk-build \
  -DCIX_NATIVE_LIBRARY="$PWD/target/release/libcix_native.so" \
  -DCMAKE_INSTALL_PREFIX="$PWD/sdk-prefix"
cmake --install sdk-build
```

The generated `cix-native.pc` derives `prefix` from `pcfiledir` and the
configured prefix-relative library directory, so moving a complete staged
prefix preserves its include and library paths, including multiarch libdirs.
The SDK CMake project enables C deliberately so GNUInstallDirs selects an
architecture-appropriate default library directory rather than guessing under
`LANGUAGES NONE`.
The installer rejects absolute include/library install directories because that
would make a relocatable package claim false.

The helper currently accepts only Unix `libcix_native.so`,
`libcix_native.dylib`, or `libcix_native.a` inputs. It deliberately rejects a
Windows DLL/import-library input because a paired install layout has not been
implemented or qualified. When a static archive is installed, its generated
CMake package resolves the system codecs directly linked by `src/external.rs`,
the platform thread/dynamic-loader facilities, and the C++ runtime explicitly
selected by `build.rs` (`c++` on Apple, `stdc++` on other Unix targets). These
are passed as compiler-resolved linker names, never as a build-host library
path. On Linux its static metadata also carries the math, dynamic-loader,
pthread, realtime and util links recorded in the target link receipt:
`-lstdc++ -lm -ldl -lpthread -lrt -lutil`. This is Linux-only; the CMake package
does not project those flags onto other platforms. The libzpaq/libbsc C++
objects are bundled by the Rust static archive. The actual target dependency
receipt remains required.

An installed CMake consumer uses:

```cmake
find_package(CIX 0.1 CONFIG REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE CIX::native)
target_compile_features(consumer PRIVATE cxx_std_17)
```

`tests/cpp_installed_consumer.cpp` is the small installed C++ consumer source.
It should be built only against a staged prefix by the focused RC24 receipt.
The Linux static-link set is evidenced by
`benchmark-work/best-expanded-local/backend-tests.log` and the build-script
link records in
`docs/research/2026-10-04-release-0.1/raw/cargo-clippy-v2/cix-rel01-cargo-clippy-v2.stdout.log`;
those historical receipts do not qualify the current source.
