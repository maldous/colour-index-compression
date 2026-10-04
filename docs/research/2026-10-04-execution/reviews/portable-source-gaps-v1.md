# RC43/RC44 portable source-gap audit v1

Date: 2026-10-05
Scope: read-only inspection of current CIX-owned Rust, CMake, and first-party packaging code. No cross-build or native build was attempted, so this records source-level facts and risks rather than observed compiler output.

## Classification

| Area | Platform effect | Classification | Evidence |
|---|---|---|---|
| PAQ worker | Linux ARM64, macOS, Windows cannot use any PAQ route | Unsupported full-engine worker capability | `src/paq_worker.rs:242-245` compiles a stub on every target except Linux x86-64; the supported implementation at `247-305` requires AVX2, Linux `dlopen`, and Linux rlimits. This is an intentional runtime refusal, not by itself a cross-target Rust compile failure. |
| PAQ worker private root | Windows cannot prepare the PAQ capability | Unsupported isolation/security implementation | `src/paq_supervisor.rs:570-635` only verifies ownership/mode and creates private directories on Unix; non-Unix returns an error. `src/cli_full_engine.rs:121-191` only creates and validates the default root on Unix. A Windows implementation needs equivalent ACL/reparse-point-safe semantics before enabling a worker. |
| Dynamic JXL and spatial providers | macOS and Windows full-engine JXL/spatial routes cannot load | Unsupported provider functionality | Both providers use a Linux-only `Library` at `full_engine/jxl_provider.rs:379-412` and `full_engine/spatial_provider.rs:378-411`; their non-Linux implementations return load/symbol errors. `installed.rs:87-100` chooses `.dylib`/`.dll` names, but discovery does not make loading work. |
| PAQ provider name/load | macOS and Windows PAQ route cannot load | Unsupported provider functionality | `src/paq_worker.rs:199` unconditionally constructs `lib<name>.so`; actual PAQ execution is already gated to Linux x86-64. The installed-layout discovery has platform suffixes, but the worker does not consume them. |
| Full-engine runtime installer | macOS and Windows full-engine packages are refused | Package qualification blocker | `packaging/runtime/CMakeLists.txt:78-125` explicitly errors for Apple and Windows, uses ELF `.so` identities and `readelf`/`$ORIGIN` checks, and creates ELF SONAME links at `132-145`. |
| SDK CMake installer | Windows SDK distribution is refused | Package qualification blocker | `packaging/sdk/CMakeLists.txt:19-29` accepts only `.so`, `.dylib`, or `.a`, explicitly rejecting DLL/import-library pairing. |
| Spatial bridge CMake | macOS and Windows bridge configuration lacks target-neutral dependency discovery; Windows has a likely compiler-option failure | Source build blocker/risk | `codecs/spatial/CMakeLists.txt:7-10` hard-codes a Linux `usr/lib/x86_64-linux-gnu` prefix; `:16-17` always sets `$ORIGIN` and GNU/Clang flags, including `-O3`, `-fno-fast-math`, and `-ffp-contract=off`. MSVC does not accept those flags. No target build was run, so this is a concrete configuration risk, not a claimed observed failure. |
| PAQ bridge CMake | Windows bridge configuration has likely compiler-option and install-layout failure | Source build blocker/risk | Each `codecs/paq/*/CMakeLists.txt` passes GNU-style flags unconditionally at `44-46`, then installs only the `LIBRARY` artifact at `58-60`. CMake's Windows DLL artifact is a `RUNTIME` artifact and its import library is an `ARCHIVE`; no destinations are specified. MSVC flag incompatibility is likewise untested here but source-visible. |
| JXL bridge CMake | Better prepared for Windows/macOS compilation, but does not close runtime distribution | Package/provider qualification gap | `codecs/jxl/CMakeLists.txt:38-43` has MSVC-specific flags and `:53-56` provides `LIBRARY` plus `RUNTIME` install destinations. It still needs pinned target-native libjxl/lzma inputs and a target-native provider loader/runtime installer before CIX can use the bridge on macOS/Windows. |
| CLI pipe behavior | Windows stdin streaming is unavailable | Unsupported functionality | `src/cli.rs:15-48` uses Unix file descriptors for stdin and returns "stdin streaming is not implemented" on non-Unix. `engine.rs:151-178` similarly makes timed pipe reads unsupported without Unix `poll`. This does not block named-file CLI operation. |
| Unix-gated code generally | macOS may compile its Unix branches; Windows avoids them with cfg | Not automatically a compile blocker | `std::os::unix` uses in CLI, supervisor, and worker code are guarded with `cfg(unix)`. They require functional review on macOS but should not be reported as unconditional Windows compilation errors. |

## ARM64 implications

There is no architecture-generic full-engine PAQ path: `paq_worker.rs:242-252` limits it to Linux x86-64 and AVX2. Thus Linux ARM64 source can at most offer core/native-only functionality and provider-free decoding until an ARM64 provider and isolation contract are implemented and tested. The current CMake spatial prefix also hard-codes `x86_64-linux-gnu`, preventing normal ARM64 discovery even on Linux.

The Rust core and C API have platform conditionals rather than an evident global `target_arch = "x86_64"` build gate. That is not evidence of a successful ARM64 build; the missing runner/toolchain inventory remains in [platform-runners-v1.md](platform-runners-v1.md).

## Smallest concrete ownership chunks

1. **Provider loader abstraction — root/source owner:** add CIX-owned loader implementations for Unix (`dlopen` on Linux and macOS) and Windows (`LoadLibraryW`/`GetProcAddress`/`FreeLibrary`) behind one interface in `src/full_engine/jxl_provider.rs` and `src/full_engine/spatial_provider.rs`. Keep absolute-path and pinned-symbol/version checks. Extend `installed.rs` tests for suffix and package layout. This enables loading only after target-native bridge artifacts exist.
2. **Worker capability contract — root/source owner:** refactor `src/paq_worker.rs`, `src/paq_supervisor.rs`, and `src/cli_full_engine.rs` behind explicit platform capability implementations. Preserve the existing Linux x86-64 semantics. For macOS, define loader, resource-limit, and private-directory behavior; for Windows, define ACL/reparse-point-safe private storage and a bounded child termination/resource model. Do not expose PAQ routes on a platform until its isolation contract is implemented and qualified.
3. **CIX bridge build portability — root/source owner:** make the CIX-owned `codecs/paq/*/CMakeLists.txt` compiler options compiler-specific, install Windows `RUNTIME` and `ARCHIVE` artifacts, and make `codecs/spatial/CMakeLists.txt` accept a target-neutral dependency prefix/architecture layout with Apple and Windows loader settings. This does not alter upstream PAQ/codec source.
4. **SDK/runtime package closure — release-distribution owner:** implement Windows DLL-plus-import-library handling in `packaging/sdk`, and distinct macOS/Windows full-engine runtime installers with native bundle identities/loader inspection in `packaging/runtime`. This audit does not modify those files because they belong to the release-distribution workstream.
5. **Target-native qualification — runner owner after source work:** run build/install and full-engine provider/PAQ route checks on Linux ARM64, macOS ARM64/x86-64, and Windows x64. Cross-compilation and Wine do not close RC43.

## Consequence for current claims

The source can honestly offer source-build/native-only coverage on the documented non-Linux targets if their dependencies build. It cannot currently claim complete full-engine specialist coverage, PAQ isolation, JXL/spatial provider loading, Windows stdin streaming, or full-engine package installation there. This is separate from whether a target runner is currently available.

## Current-status addendum (after the point-in-time audit)

The table above preserves the audit's original source snapshot. The following
items are current-source corrections, bounded by the receipts named below.
They do not change the audit into macOS, Windows, or ARM64 execution evidence.

| Original gap | Current source status | Evidence boundary |
|---|---|---|
| Non-Linux JXL/spatial loader stubs | Superseded. `src/full_engine/dynamic_library.rs` supplies explicit-path Unix `dlopen` and Windows `LoadLibraryExW`/`GetProcAddress`/`FreeLibrary`; installed discovery retains platform suffixes and generic aliases. | This is source coverage only. No native macOS or Windows bridge/provider load receipt exists. |
| Windows SDK DLL/import-library layout rejected | Superseded at the SDK layout layer. `packaging/sdk/CMakeLists.txt` requires the DLL and matching import library, stages them separately, and `CIXConfig.cmake.in` publishes both locations. | [`sdk-runtime-contract-v1/receipt.json`](../jobs/sdk-runtime-contract-v1/receipt.json) passes a synthetic Windows-targeting CMake layout, `find_package`, and missing-pair negative case. It explicitly does not validate a real DLL, PE loading, ABI, or Windows consumer. |
| Windows stdin streaming unavailable | Superseded for blocking reads. The non-Unix CLI adapter directly reads stdin in bounded blocks. | Timed `--flush-interval` waits still refuse without Unix poll/readiness support; no Windows execution occurred. |

The source-completeness guard added in `f2d670c8b` binds these corrections to
the current frozen source. The existing PAQ worker/isolation restrictions,
full-engine runtime staging restrictions, bridge build/dependency work, and all
native-runner requirements remain open unless separately evidenced. In
particular, no native Linux ARM64, macOS ARM64, macOS x86-64, or Windows x64
build or runtime claim follows from this addendum.
