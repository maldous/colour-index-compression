# Execution dependency evidence note — 2026-10-04

This is a local, read-only inventory for planning. It does not accept a release
criterion, qualify a platform, prove a build, or lift the benchmark HOLD.
`dependency-blockers.json` is the 55-item plus RC50-GPU crosswalk;
`candidate-dispositions.json` is the 26-group plus R27 consideration schedule.
Every item has one disposition value so a closed research result cannot be
mistaken for a waived product requirement.

## Governing evidence

- The 55-item ledger, its statuses, its pre-benchmark prerequisite lists and its
  RC51 rule are in
  [`requirements.json`](../2026-10-04-rc-reconciliation/requirements.json).
  Its rule requires accepted current-RC evidence for every listed prerequisite
  and external obligation before RC51; RC52 is after that gate.
- [RESEARCH-CLOSURE.txt](../2026-10-04-rc-reconciliation/RESEARCH-CLOSURE.txt)
  preserves finite negative research results without waiving useful native,
  SDK, compatibility, quality or distribution work.
- [PROGRESS.md](../2026-10-04-native-rc/PROGRESS.md) records useful PAQ bridge
  and worker primitives, but also says the full engine/CLI integration,
  native route parity, clean CXX JXL integration and all 55 RC requirements
  remain unqualified.
- [candidates.json](../2026-10-04-global-methodology-review/candidates.json)
  says all 26 external families remain unqualified as new CIX routes. The
  last-chance and constraint-lifting reports delimit rather than erase open
  coverage gaps.

## Local dependency observations

Observed on the sole local Linux x86-64 host: Rust 1.98.1, Cargo 1.98.1,
CMake 3.28.3, Clang 18.1.3, GCC 13.3.0, a separately observed CUDA 12.1 toolkit (`nvcc` and `version.json`), GTX 1650
(4096 MiB), libzstd 1.5.5, and Brotli pkg-config entries. These are inventories
only. `nvidia-smi` displays “CUDA Version: 13.0” as driver API compatibility; it is not toolkit proof. The separate `nvcc` observation is the toolkit evidence. These observations do not qualify a clean build, a release package, GPU performance,
other architectures, macOS, Windows, a host SDK, or an external registry.

The native JXL bridge explicitly requires a provisioned libjxl 0.12 prefix
([`codecs/jxl/CMakeLists.txt`](../../../rust/cix-native/codecs/jxl/CMakeLists.txt));
no standard JXL include/library location or pkg-config record was found.
PAQ bridge CMake files explicitly require packaged `CIX_PAQ_SOURCE_ROOT`
([`codecs/paq/v216/CMakeLists.txt`](../../../rust/cix-native/codecs/paq/v216/CMakeLists.txt)).
A local research reference containing `DmcModel.cpp` is evidence of reference
source only, not a shipping dependency closure. `libbsc` and `libzpaq715` have
local upstream/provenance records under [`rust/cix-native/vendor`](../../../rust/cix-native/vendor).

The native code directly invokes `ZSTD_compress`
([`src/external.rs`](../../../rust/cix-native/src/external.rs)), so retained
libzstd internally supplies FSE/tANS capabilities. This does not establish a
separate CIX rANS/FSE stream, and it does not satisfy RC25 interoperability.

No macOS/Windows runner evidence, external registry identity, upstream
acceptance, or Squash 0.8 SDK qualification was found in this bounded local
inspection. They remain missing/external in the JSON crosswalk rather than
being inferred from source artifacts.
