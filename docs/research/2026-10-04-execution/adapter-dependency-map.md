# Adapter and binding dependency map

This is a read-only implementation map for RC27–RC43 and RC54. A local tool,
shared object, or old shim is not a qualified adapter. Every listed feature
remains open until it has a pinned SDK/API, a CIX-owned boundary, a documented
development identity, and focused host execution evidence. No download, build,
test, or host change was performed for this map.

## Existing reusable native boundary

The current reusable base is the process-free CIX SDK:
`include/cix.h`, `cix_stream.h`, `cix_formats.h`, `cix_dictionary.h`, `cix.hpp`,
and `packaging/sdk/`, backed by `c_api.rs`, `c_stream_api.rs`,
`c_format_api.rs`, and `c_dictionary_api.rs`. It can be reused by adapters that
need bounded native buffer or independent-block stream operations. It is not a
full-engine worker, a registered host codec, or a substitute for any host SDK.

| Requirement | Existing source | Local host evidence | Missing CIX-owned boundary / gate |
|---|---|---|---|
| RC27 tar/libarchive | None | `/bin/tar`; `libarchive.so.13`, without inspected dev header/pkg-config contract | Tar filter and libarchive adapter; pipelines, `-I`, `-d`, stdin/stdout and failure qualification. |
| RC28 QuixDB Squash | `cix_squash_splice`; `packaging/squash/` libSquash 0.8 shim | No `squash-0.8` pkg-config/header | Pinned public Squash SDK load plus buffer/stream/splice/flush/bounds tests. This is separate from SquashFS. |
| RC29 7-Zip | None | `/bin/7z`, `/bin/7za`; no SDK | Coder source, experimental method/version identity and decoder distribution. |
| RC30 HDF5/netCDF | None | HDF5/netCDF sonames only; no inspected dev header/pkg-config contract | Native filters, parameters/capabilities/bounds and h5py/netCDF registration. |
| RC31 Numcodecs/Zarr | None | Python only; no package/API evidence | Separate Zarr v2 codec and v3 `BytesBytesCodec` bindings. |
| RC32 Blosc2 | None | No SDK evidence | Plugin ABI, bounded incompressible behavior and identity. |
| RC33 RocksDB/WiredTiger | None | No SDK evidence | Pinned CompressionManager and WT_COMPRESSOR adapters. |
| RC34 Hadoop/seek | CIXG1 stream API | Java/Javac only; no Hadoop SDK | Hadoop lifecycle wrappers and identity-bound seek index. |
| RC35 primary bindings | C/C++/Rust headers and SDK | Native SDK sources | Optional Python binding over the native ABI; standalone CIX remains Python-free. |
| RC36 additional bindings | None | Go, Java, Node available; .NET absent | Go/JNI/PInvoke/Node ownership, stream and cancellation bindings. |
| RC37 WASM | None | No WASM toolchain/runtime | Portable subset, capability declaration and browser stream tests. |
| RC38 gRPC/HTTP | Standard-format codec source | No protoc/gRPC tooling | Bounded gRPC negotiation and HTTP interop/controlled CIX negotiation. |
| RC39 GIO/GStreamer/storage | None | No SDK evidence | GIO/GStreamer flush/EOS/cancel adapters and storage examples. |
| RC40 SquashFS userspace | Old libSquash plugin only | `mksquashfs`/`unsquashfs`; no dev SDK | Separate mksquashfs, unsquashfs, libsquashfs and squashfuse adapters for data, metadata, fragments and xattrs. |
| RC41 restricted SquashFS/VM | None | No VM receipt | Restricted decoder, differential tests and disposable-VM mount qualification. |
| RC42 proposals | None | No source/SDK evidence | Per-format proposal and feasible CIX-owned prototype; no stock claim without upstream result. |
| RC43 platforms | Linux x86-64 source/tooling | No ARM64/macOS/Windows runners | Actual target build and binding execution on all required platforms. |
| RC54 registry/acceptance | SDK packaging only | No adapter identity or registry allocation | Per-adapter development identity plus real pinned SDK/runners; stock claims require actual acceptance. |

## Proposed disjoint implementation locations

The exact path list, current-source state, and blockers for every requirement
are in [adapter-dependency-map.json](adapter-dependency-map.json). The proposed
layout keeps host-specific code separate from the Rust core:

- `rust/cix-native/adapters/<host>/` for C/C++ host ABI boundaries;
- `rust/cix-native/bindings/<language>/` for optional consumer bindings;
- `rust/cix-native/adapters/seek/` and `adapters/squashfs/` for independent
  chunk and filesystem code;
- `docs/research/2026-10-04-execution/adapter-identities.json` for development
  identities and compatibility statements, once individual adapters exist.

## Implementation order

1. Freeze RC24/RC35 ABI, ownership, limits, and full-engine worker separation.
2. Obtain and bind required Squash/SquashFS SDKs before RC28/RC40/RC41 code.
3. Implement archive, database, data-format, Hadoop and language adapters
   against pinned host APIs, each with its own identity and focused fixture.
4. Add protocol/storage/WASM boundaries after their SDKs are real and pinned.
5. Prepare RC42 experimental proposals and RC54 identities without claiming
   registry or upstream acceptance.
6. Run RC43 only on actual target runners; cross-compilation is preparation,
   never platform qualification.
