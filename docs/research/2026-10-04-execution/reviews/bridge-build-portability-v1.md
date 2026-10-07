# Bridge build portability v1

Scope is limited to the four CIX PAQ bridge CMake files and the CIX spatial
bridge CMake file. No upstream PAQ, JXL, CharLS, OpenJPEG, or other vendor file
was modified. No build, target runner, provider load, or benchmark was run.

The PAQ bridge projects retain the exact qualified Linux x86_64 GNU/Clang flags:
`-O3 -fno-fast-math -ffp-contract=off -fno-strict-aliasing` and C++
`-fno-rtti`. MSVC keeps `/O2 /fp:strict /GR-`; AppleClang and other GNU/Clang
targets take the same explicit safe floating-point/RTTI policy, while an
unknown compiler fails configuration rather than inheriting incompatible flags.
The existing install rules already retained `LIBRARY`, `RUNTIME`, and `ARCHIVE`
destinations; no install-layout behavior was changed here.

The spatial bridge now accepts one legacy `CIX_SPATIAL_ROOT` or an explicit
semicolon-separated `CIX_SPATIAL_DEPENDENCY_ROOTS` list. Header and library
search remains confined to those roots. It retains
`CMAKE_LIBRARY_ARCHITECTURE`, which is target-toolchain-aware, for conventional
multiarch SDK layouts; it does not glob arbitrary subdirectories or load SDK
CMake package metadata. Explicit selected library paths still take precedence.
ELF `$ORIGIN` and macOS `@loader_path` were already present and are unchanged.

This is build-system portability only. `src/paq_worker.rs` still refuses PAQ
worker execution outside qualified Linux x86_64, and runtime staging still
requires target-specific provider/companion installation and native runner
receipts. It does not establish Windows, macOS, or ARM64 support.
