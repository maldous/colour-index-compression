# Portable source batch review v1

**Scope:** read-only review of the pending CLI alias helper, runtime staging
CMake/README, four PAQ bridge CMake files, and the spatial bridge CMake file.
`runtime-alias-layout-v1` is treated only as the focused synthetic-layout and
extracted-helper receipt it declares; no whole CLI, native runner, or Windows
binary claim is inferred.

## Required correction

`rust/cix-native/packaging/runtime/CMakeLists.txt` documents and intends
full-engine staging to be ELF/Linux-only, but the gate is:

```cmake
if(APPLE OR WIN32)
  message(FATAL_ERROR ...)
endif()
```

This permits any other non-Linux target (for example Android, FreeBSD, or an
unrecognised cross target) to continue through Linux `.so` companion names,
`readelf`, `$ORIGIN`, and ELF SONAME-link installation.  That contradicts the
README’s stated Linux-only support and can stage an invalid target layout.

Replace the platform condition with a positive Linux gate for the full-engine
path, for example:

```cmake
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "full-engine companion staging is implemented only for qualified ELF/Linux inputs; use native-only or provide a target-specific runtime installer")
endif()
```

The existing `WIN32` native-only alias branch remains appropriate.  The
focused receipt proves Windows native-only copies and refusal with incomplete
full-engine inputs, but it does not prove this target-specific full-engine
refusal because its Windows test reaches the missing-bridge check first.

## Reviewed behavior with no further product correction identified

The CLI helper is private and preserves Unix behavior exactly.  On Windows it
uses ASCII case folding and removes one terminal `.exe`, so copied `uncix.exe`
and `cixcat.exe` select the existing decoder modes.  It does not change option
parsing or public Rust APIs.  `runtime-alias-layout-v1` hashes the source bytes
and passes the extracted helper cases; it intentionally does not qualify the
whole CLI on a Windows target.

The runtime project’s `LANGUAGES NONE` avoids selecting a host C compiler for a
prebuilt-file installer.  The observed `GNUInstallDirs` developer warning is
non-fatal and does not affect the explicit `bin`, `lib/cix`, or documentation
destinations used here.

The PAQ changes preserve the existing GNU/Clang flags, retain MSVC’s explicit
`/O2 /fp:strict` and RTTI setting, and fail closed for other compilers.  The
Linux x86_64 branch is semantically the same as the portable GNU/Clang branch;
it is explanatory qualification provenance rather than a behavior split.

The spatial change keeps `NO_DEFAULT_PATH` and builds all header/library hints
only from caller-supplied immutable roots.  It permits separate target SDK
prefixes without falling back to host discovery; explicit selected library
paths continue to require absolute existing files.  Its compiler selection
matches the PAQ policy and preserves Linux `$ORIGIN` and macOS `@loader_path`
installation RPATH behavior.
