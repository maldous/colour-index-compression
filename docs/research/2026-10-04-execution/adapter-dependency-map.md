# Adapter and binding dependency map

**Checkpoint: current adapter receipts through `host-adapters-v7`.** This is a scoped
source-and-receipt inventory, not a release claim. A passing consumer contract
covers only the recorded host, source snapshot, library and capability. It does
not establish a package matrix, platform portability, streaming/full-engine
coverage, process-RSS cap, registry acceptance, or general host compatibility.

The reusable base is the process-free native SDK: `include/cix.h`,
`cix_stream.h`, `cix_formats.h`, `cix_dictionary.h`, `cix.hpp`, and
`packaging/sdk/`, backed by the C buffer, CIXG1 stream, explicit-format and
Zstd-dictionary APIs. The ordinary CLI has a separate, bounded whole-input
full-engine path; language bindings intentionally expose the public SDK
surface, not full-engine routing, retained-history streaming, PAQ/JXL selection
or specialist selection.

This packaging work does not reopen compression research. The numeric
structural-composition branch remains closed and the predictive-mixture audit
remains a negative first decision gate; an adapter is not evidence of a new
compression mechanism.

## Recorded scoped evidence

| Surface | Current source / recorded evidence | What the receipt does **not** establish |
|---|---|---|
| C/C++ SDK and runtime package | `cli-bindings-v8` passed SDK configure/install, C/C++ consumers and relocated runtime command checks. `runtime-closure-v1` passed its Linux relocated-dependency receipt; `runtime-closure-v2` installed the new binary, and `relocated-providers-v4` passed actual JXL gray/planar plus all four PAQ level-1 exact cases. level-0 has a known upstream null bug and is guarded in the worker before DSO entry; all four negative guards passed. | A portable release package, all codecs/providers, all CLI modes, or any non-Linux loader. |
| Python core SDK | `bindings/python` is a stdlib `ctypes` consumer of an explicitly chosen installed library. `cli-bindings-v8` passed its Python contract; `language-consumers-v3` passed the Python core contract. | Wheel/interpreter/platform matrix or a Python dependency in the CIX executable. |
| Numcodecs / Zarr | Separate experimental Numcodecs/v2 and Zarr v3 bytes-to-bytes adapters exist. `language-consumers-v4` passed the recorded staged Python host integration. Metadata cannot select a library; the process must configure a trusted SDK path. | Stock registry/upstream support, partial chunks, dtype/shape semantics, or broad host-version compatibility. |
| Go | Optional cgo binding source exists; `cli-bindings-v8` passed the recorded installed-SDK Go consumer test. | Other Go/C toolchains, OS/architecture loader behavior, or full-engine streams. |
| Java/JNI | JNI shim and Java contract source exist; Node/Java substeps in `language-consumers-v2` passed before that job later failed while installing Python host dependencies. | A whole-job pass, JVM matrix, Android, automatic library discovery, or in-flight cancellation. |
| Node-API | N-API-8 addon and contract source exist; Node substeps in `language-consumers-v2` passed on the recorded Linux host. | Node/N-API version matrix, Electron, prebuilt binaries, or full-engine streams. |
| .NET | .NET 8 P/Invoke source and contract exist; `dotnet-consumer-v2` passed restore, build and contract against its staged SDK. | Installed system .NET, Windows/macOS support, NuGet publication, or a package matrix. |

Earlier failing/incomplete records remain evidence: `cli-bindings-v1`–`v6`,
`language-consumers-v1`–`v3` and `dotnet-consumer-v1` are not upgraded by later
passing substeps. Any post-receipt source fix requires a fresh qualification
rather than inheriting an old result. The current constraints suite has 46 passing tests; runtime finalisation is still not a release.

## External adapters and filesystem paths

| Requirement | Current state | Remaining prerequisite and gate |
|---|---|---|
| RC27 libarchive/tar | `host-adapters-v3` passed GNU tar and an actual C program filter using explicit `--cix` path. | Remains a narrow Linux receipt: libarchive lifecycle, wider tar interoperability, error matrix and package/platform qualification are open. |
| RC28 QuixDB Squash | SDK source is present/downloaded but uncompiled; existing libSquash 0.8 plugin candidate remains unqualified. | Build/load against the pinned SDK with splice/flush/bounds cases. It is not SquashFS. |
| RC29 7-Zip | Source-only and uncompiled; no host acceptance. | Pinned SDK build, experimental method identity, decoder distribution and host test. |
| RC30 HDF5/netCDF | `host-adapters-v6` passed HDF5 1.10.10/netCDF 4.9.2 reopen compression, raw-mask, corruption and limits with deployment caps of 64 MiB chunk/output, 512 MiB native memory and four workers; private filter ID 65001. `host-adapters-v7` passed h5py 3.10, HDF5 1.10.10 and NumPy 1.26.4 actual compressed mask-0 reopen exactness. | These remain bounded host receipts: h5py/HDF5/NumPy version and platform matrices plus registry/upstream acceptance remain open. |
| RC32 Blosc2 | Source-only and uncompiled; no host acceptance. | Pinned Blosc2 plugin ABI, identity and incompressible/bounds host tests. |
| RC33 RocksDB/WiredTiger | WiredTiger source-only and uncompiled; no host acceptance. | Pinned host interfaces and independent CompressionManager/WT_COMPRESSOR qualification. |
| RC34 Hadoop/seek | Hadoop source-only and uncompiled; sequential CIXG1 design makes no seek/splittable claim. | Pinned Hadoop API compile/runtime and separately proven archive-bound seek format. |
| RC37 WASM | No subset or receipt. | Target toolchain/runtime and a deliberately limited capability plus browser tests. |
| RC38 gRPC/HTTP | No service adapter. | Pinned protoc/gRPC/runtime, message limits, HTTP interop and explicit CIX negotiation. |
| RC39 GIO/GStreamer | `host-adapters-v4` passed four native-SDK GIO contract cases. Cancellation is an entry fence only, not hard preemption. | GStreamer/storage work, broader host/platform matrix and any hard-cancellation claim remain open. |
| RC40 SquashFS userspace | Source is present but uncompiled; existing libSquash plugin is unrelated. | Build against pinned userspace APIs and qualify data/metadata/fragments/xattrs independently. |
| RC41 restricted SquashFS/VM | No VM-mount receipt. | Chosen restricted profile, differential decoder cases and disposable VM/kernel runner. |
| RC42 proposals | No accepted implementation. | Per-format compatibility case, distinct development identity and feasible prototype. |
| RC43 platforms / RC54 registry | Linux x86-64 scoped receipts only; no registry allocation. | Actual Linux ARM64, macOS ARM64/x86-64 and Windows x64 build-and-run hosts; per-host SDK acceptance and collision-free development identities. |

## Explicit remaining host prerequisites

The next receipts require actual target hosts rather than cross-compilation:
Linux ARM64; macOS ARM64 and x86-64; Windows x64; and a disposable VM/kernel
runner for the restricted SquashFS claim. Language work additionally needs a
compatible C compiler/loader for cgo, a target JDK with JNI headers and JVM, a
Node host with N-API 8 headers/runtime, a .NET 8 SDK/runtime, and target CPython
interpreters. Numcodecs/Zarr needs the staged compatible host versions and an
explicit installed SDK path. External adapters need their named development
headers and real host/plugin APIs, not merely local sonames or command-line
tools. These prerequisites remain required even where a Linux source-level
consumer contract has passed.

The consolidated receipt is [HOST-ADAPTERS-CHECKPOINT.md](HOST-ADAPTERS-CHECKPOINT.md). The machine-readable statuses, paths, evidence boundaries and prerequisites are in [adapter-dependency-map.json](adapter-dependency-map.json).
