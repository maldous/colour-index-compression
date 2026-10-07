# RC43 platform runner inventory v1

Date: 2026-10-05
Scope: local runner/tool availability and existing first-party receipts only. No network, credential, download, or build activity was performed.

RC43 requires actual execution for Linux ARM64, macOS ARM64, macOS x86-64, and Windows x64. Cross-compilation alone is not execution evidence.

| Target | Native runner available locally | Current evidence | Blocker / required next step |
|---|---:|---|---|
| Linux x86-64 | Yes | Current host is Ubuntu x86-64. `rust/cix-native/README.md` identifies Linux x86-64 as the only currently qualified host. Existing execution job receipts are produced on this class of host. | Baseline runner exists; final release qualification still needs the selected final acceptance matrix. |
| Linux ARM64 | No | Host is x86-64. Installed Rust targets list only `x86_64-unknown-linux-gnu`; no AArch64 user-mode QEMU or AArch64 compiler was found. `qemu-system-aarch64` is installed. | No runnable ARM64 guest image/kernel/firmware/rootfs or AArch64 target toolchain is available. Provision those locally, then execute the ARM64 ELF in a booted ARM64 Linux guest under `qemu-system-aarch64`. Record this as **emulated Linux ARM64 execution**, not native ARM64 execution; RC43 acceptance must decide whether that supplementary evidence is sufficient. A native ARM64 Linux runner remains required for an unqualified native claim. |
| macOS ARM64 | No | Current host is Linux. `packaging/macos/README.md` is a source-build recipe and explicitly requires separate Apple Silicon testing. | Provide an Apple Silicon macOS runner with Apple command-line tools, Rust, and listed Homebrew dependencies; run the documented native CLI/archive round-trip, malformed-input, and dynamic-library checks. |
| macOS x86-64 | No | Current host is Linux. The macOS recipe explicitly requires separate Intel testing. | Provide an Intel macOS runner with the documented toolchain and run the same native checks. An ARM64 build or a cross-build does not constitute Intel macOS execution. |
| Windows x64 | No | `wine` is present, but Wine is not a native Windows runner and is excluded from this inventory as native evidence. No Windows Rust target, MinGW compiler, or vcpkg Windows dependency layout was found locally. | Provide an actual Windows x64 environment with Rust/C++ and `vcpkg` `x64-windows`, then collect native build/test and clean-machine CLI round-trip/malformed-input receipts. The SDK helper currently rejects the Windows DLL/import-library layout, so Windows SDK packaging is independently blocked. |

## Packaging constraints that affect runner qualification

- `rust/cix-native/packaging/runtime/CMakeLists.txt` stages the full-engine companion only on ELF/Linux. Its README records macOS and Windows full-engine loader identities, bundle mechanics, and target execution as open work. Thus a basic macOS or Windows source-build receipt would not establish full-engine runtime distribution closure.
- `rust/cix-native/packaging/sdk/CMakeLists.txt` rejects Windows DLL/import-library pairing, and `packaging/sdk/README.md` says that layout is not implemented or qualified.
- `rust/cix-native/packaging/macos/README.md` and `rust/cix-native/packaging/windows/README.md` describe source-build recipes rather than shipped-platform qualification.

## Receipt interpretation

The `windows-jobs-mixed-v*` execution jobs are named for CIXW1 *independent byte windows*. They are not Microsoft Windows receipts: the v4 raw result records an x86-64 Linux cgroup command. Likewise, WASM provision/portable jobs do not establish execution on any RC43 native target.

## Local inspection evidence

- `uname -m` reported `x86_64` on Ubuntu 24.04.4.
- Present commands: `qemu-system-aarch64`, Docker, Rust/Cargo, Clang, CMake, and Wine.
- Absent from the inspected command path: `qemu-aarch64`, `qemu-aarch64-static`, `qemu-x86_64`, `wine64`, AArch64 cross GCC, and MinGW GCC.
- `rustup target list --installed` reported only `x86_64-unknown-linux-gnu`.

This inventory records available evidence, not a release acceptance decision.

## Current-status addendum (after the point-in-time inventory)

The preceding inventory remains the record of its original local inspection. The
following source-level changes supersede only its stale *source-gap* statements;
they do not add a native platform execution receipt.

- The Windows SDK layout now accepts an explicitly selected `cix_native.dll`
  plus its matching `cix_native.lib` or `cix_native.dll.lib`, stages the DLL in
  `bin` and the import library in `lib`, and exposes both through the generated
  CMake target. The scoped receipt
  [`sdk-runtime-contract-v1/receipt.json`](../jobs/sdk-runtime-contract-v1/receipt.json)
  records the synthetic Windows-targeting CMake layout, `find_package`, and
  missing-pair negative cases. Its declared scope is layout-only; it is not a
  Windows compiler, PE-loader, ABI, or consumer execution receipt.
- The current source has a platform-specific explicit-path loader:
  Unix uses `dlopen` and Windows uses `LoadLibraryExW` with the selected DLL
  directory and System32 only. Installed discovery uses platform suffixes and
  generic aliases. This removes the former source claim that non-Linux loader
  implementations were only rejection stubs. It does not prove that a macOS or
  Windows bridge, its companions, or a full-engine route loads on those
  platforms.
- The CLI now permits blocking standard-input reads on non-Unix targets.
  Timed `--flush-interval` operation remains deliberately unavailable there
  because no equivalent readiness deadline is claimed. The former statement
  that Windows stdin streaming is entirely unavailable is therefore stale.
- Commit `f2d670c8b` adds the current source-completeness guard used by the
  relevant frozen work; this addendum is tied to the present source rather than
  treating the original inventory as a current source snapshot.

Linux ARM64, macOS ARM64, macOS x86-64, and Windows x64 still have **no native
execution evidence** in this review. A real runner must build and exercise the
selected target before any native-platform claim. Windows full-engine runtime
staging and platform-specific PAQ isolation remain separate unfinished
contracts; the corrected SDK layout and loader source do not close them.
