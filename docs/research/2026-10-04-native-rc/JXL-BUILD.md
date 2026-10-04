# Native JPEG XL build provenance and RC integration plan

## Decision

Use **libjxl v0.12.0** through a narrow CIX-owned C ABI, built from an
independently provisioned, immutable source closure. Do not link the system
libjxl 0.7 runtime and do not ship or load the private imagecodecs wheel.

A C ABI adapter is the grounded choice. libjxl publishes C headers
(`jxl/encode.h`, `jxl/decode.h`, and `jxl/thread_parallel_runner.h`); the
retained route currently reaches that API only through a CPython/NumPy binding.
A small C++ adapter can own libjxl objects, allocator/error cleanup, and
version-specific structures while Rust sees fixed-width image descriptors and
owned byte buffers. Recreating the C struct layout directly in Rust or using a
new unqualified Rust wrapper would add an ABI risk without restoring any
additional route semantics.

The adapter must be a library API: no image command-line tool, Python process,
NumPy ABI, environment lookup, or wheel-private RPATH may enter the product.

## Frozen-route evidence

The source uses `imagecodecs.jpegxl_encode` and `jpegxl_decode` in these
native-port targets:

| CIX frame/route | Exact binding-facing configuration | Decode constraint |
| --- | --- | --- |
| `CIXV1` volume | lossless, grayscale, effort 9, `numthreads=1`; transformed `uint8` or `uint16` volume | preallocated output is exactly paid region bytes |
| `CIXI2` multiscale volume | lossless, grayscale, effort 10, `numthreads=1`, planar when band dimensionality requires it | per-band preallocated output is bounded from frame shape |
| `CIXI1` spatial image | lossless, effort 7, `numthreads=1`, `uint8`/`uint16` gray pixels | historical frame lacks a shape field; retain existing CIX framing checks and use the worker memory bound |

Source anchors: `runtime/cix_runtime/legacy/volume_image_codec.py`,
`multiscale_volume.py`, and `spatial_image_codec.py`.

The staged imagecodecs closure contains `_jpegxl.abi3.so` and private
`libjxl-75330aa4.so.0.12.0`, `libjxl_threads-3d12e8e4.so.0.12.0`, and
`libjxl_cms-fccdddab.so.0.12.0`. It has an `$ORIGIN/../imagecodecs.libs` RPATH
and is therefore a host-pinned Python-wheel closure, not a CIX dependency.
Its local libjxl binary digest is
`c2260652b32ce1071e60ea0015a9eb26a735e5662ce1fc0fa97d3b511afbd3d9`; this is
an audit observation only and must not be used as an input artifact.

Imagecodecs 2026.8.16 specifically records that its JPEG XL encode path was
fixed to set `distance=0`, required by libjxl 0.12. The native adapter must set
that lossless parameter explicitly before a byte-for-byte route comparison;
`lossless=true` alone is not accepted as equivalence evidence.

## Provenance lock

| Item | Required value |
| --- | --- |
| Upstream project | [libjxl/libjxl](https://github.com/libjxl/libjxl) |
| Release/tag | `v0.12.0`, signed release commit shown as `a7a9c78` |
| Source URL | `https://github.com/libjxl/libjxl/archive/refs/tags/v0.12.0.tar.gz` |
| Source SHA-256 | **Not published in the official release page; do not invent one.** Root must record the SHA-256 of the provisioned source closure before vendoring/build. |
| Required source form | Recursive checkout/bundle at `v0.12.0`, including all pinned submodules, or an equivalent internally materialized source bundle with a manifest of every file/submodule revision and SHA-256. |
| License | Upstream BSD-style `LICENSE`; retain it and every bundled-dependency notice in the distribution inventory. |

The official build instructions warn that the web-interface zip/tarball does
not contain required submodules and is not sufficient by itself. They require
CMake, pkg-config, and Brotli development headers for the core build. The
v0.12.0 release notes also recommend upgrading to v0.12 for security fixes and
state that its API can change, making the version lock essential.

The release page lists static Linux and Windows assets and platform `.deb`
artifacts, but those are not source dependencies for CIX. Build from the pinned
source closure so compiler, architecture, licenses, and CIX adapter identity
remain auditable.

Sources: [v0.12.0 release](https://github.com/libjxl/libjxl/releases/tag/v0.12.0),
[official build instructions](https://github.com/libjxl/libjxl/blob/main/BUILDING.md),
and [upstream repository](https://github.com/libjxl/libjxl).

## Build closure

The development host currently exposes only runtime `libjxl.so.0.7` and
`libjxl_threads.so.0.7`, with no libjxl headers. This is a normal missing build
dependency, not a blocker: root may provision unchanged v0.12 source and its
recorded submodules as a build dependency.

Configure an out-of-tree release build from that source closure with the CIX
resource scheduler. The initial narrow configuration should disable unrelated
tools, tests, examples, documentation, benchmarks, plugins, viewers, JNI,
SJPEG, OpenEXR, JPEG transcoding, and boxes only if the focused compatibility
fixtures confirm no retained frame requires them. Keep the core encoder,
decoder, CMS, threads, and Highway dispatch enabled. Use the upstream CMake
interface; do not copy a wheel library or use its headers.

The CIX build should link a private `cix_jxl_bridge` against the provisioned
v0.12 `libjxl`, `libjxl_threads`, `libjxl_cms`, and their declared Brotli/CMS/
Highway closure. Install either:

1. a CIX-owned shared bridge and its versioned dependency closure under the
   package-private library directory with a relative RPATH; or
2. a CIX-owned static bridge only after license, platform, and complete-link
   closure checks prove that the static result is portable for that package.

Never resolve `libjxl` by whichever host library appears first. Record source
manifest hash, compiler/CMake versions, CMake cache, bridge source hash,
resulting ELF/Mach-O/PE dependency graph, and license inventory in the RC
build receipt.

## Narrow bridge contract

The CIX-owned C++ bridge should expose only operations needed by retained
frames:

- encode an owned grayscale `uint8` or little-endian `uint16` plane/volume
  descriptor with dimensions, planar/interleaved layout, effort, lossless
  `distance=0`, and exactly one runner thread;
- decode an existing JXL payload into a caller-sized output buffer after the
  Rust framing layer has checked dimensions and byte count;
- return typed status/error text and library version; allocate/free bridge
  output through paired CIX functions or caller-owned callbacks.

The Rust layer remains responsible for CIX framing, varints, checksums,
region/dimension multiplication overflow checks, archive memory admission, and
mode-specific transforms. It must not accept a decoded allocation merely
because libjxl reports success. The bridge must reject unsupported sample
formats, non-gray channel layouts, unexpected animation/extra channels, and
output sizes that differ from the bounded frame-derived size.

`CIXI1` has no stored shape for its JXL payload. Its first native decoder must
therefore preserve the historical framing/CRC validation and add a focused
migration decision: either a bounded libjxl basic-info probe whose dimensions
are checked against the paid region byte count before pixel allocation, or a
new framed route for future encodes while retaining an explicit legacy decoder.
Do not claim that direct JXL alone solves this historical bound.

## Required focused qualification

No corpus campaign is implied. The scheduler should run only the following
before admitting the port:

1. verify the provisioned v0.12 source/submodule manifest and build receipt;
2. confirm bridge exports and dependency closure do not reference Python,
   imagecodecs, or host libjxl 0.7;
3. encode small fixed gray 8-bit and 16-bit fixtures for efforts 7, 9, and 10,
   comparing bytes where the frozen binding configuration is fully reproduced;
4. cross-decode frozen Python-generated CIXV1/CIXI1/CIXI2 payloads with native
   libjxl and native-generated payloads with the frozen decoder;
5. exercise malformed payload, dimensions, stride, sample-depth, output-cap,
   and cancellation/resource failures without allocation beyond the frame cap;
6. run route-level CIX frame restoration and checksums for every retained mode.

Byte equality is required only after the imagecodecs parameter mapping is
proved; otherwise preserve the exact archive decoder requirement and record a
new encoder identity rather than presenting a changed payload as historical
parity.
