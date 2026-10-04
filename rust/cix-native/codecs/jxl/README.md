# CIX libjxl bridge

This is CIX-owned glue around a separately provisioned, unchanged **libjxl
0.12.0** build. It neither imports Python nor exposes libjxl structures to the
Rust ABI. `CIX_JXL_ROOT` is mandatory at configure time; CMake deliberately
refuses host-library discovery. The package recipe must ship the matching
libjxl runtime beside `cix_jxl_bridge` and verify `cix_jxl_library_version() ==
12000` before enabling this route.

The bridge currently supports exactly one gray 2-D pixel plane. It accepts
UINT8 only for 1–8 bit samples and UINT16 only for 9–16 bit samples; its CIX byte order is explicitly
little-endian. It passes one worker to `JxlThreadParallelRunner`, sets `JXL_BIT_DEPTH_FROM_CODESTREAM`,
`JxlEncoderSetFrameLossless(..., JXL_TRUE)`, and a frame distance of `0.0`.
Decode validates the advertised dimensions, unsigned sample depth, gray channel
count, absence of extra channels, preview and animation *before* installing its
caller-owned output buffer. It rejects unconsumed input after its single-image decode.

That is enough to implement and qualify the frozen CIXI1 2-D JXL branch once
its absent stored shape is resolved by the native frame reader. It does **not**
claim frozen CIXV1/CIXI2 parity yet: those routes pass 3-D arrays with
`planar=True` in selected cases. The frozen imagecodecs-to-libjxl planar mapping
must be captured with 3-D 8/16-bit fixtures before a CIX 3-D/planar descriptor
is introduced. Until then, a caller must report the route unsupported rather
than flatten or transpose a volume.

Required qualification after provisioning:

1. Compile against the frozen official v0.12.0 headers and shared libraries;
   verify the runtime version exactly equals `12000`.
2. Round-trip gray 2-D 8-bit and each 9–16-bit depth through this bridge,
   including a value near each depth's maximum; compare every original byte.
3. Cross-decode CIX-produced JXL with the pinned `djxl`, and decode
   imagecodecs-produced **2-D** frozen CIXI1 payloads with this bridge. Record
   semantic byte equality, not a claimed identical codestream.
4. Run malformed/truncated input and geometry/type mismatch cases under the
   CIX output and memory policy; prove no output allocation occurs before
   basic-info bounds are checked.
5. Only after an evidence-backed planar mapping exists, add CIXV1/CIXI2
   volume/planar encode and cross-decode coverage. No 3-D behavior is implied
   by this 2-D ABI.
