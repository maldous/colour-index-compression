# JXL completion handoff

## Implemented CIX-owned boundaries

- `cix_jxl_probe_gray_2d` reads only libjxl basic information and validates a
  CIX-paid pixel count before an image output buffer is supplied. It rejects
  non-gray, animated, preview, extra-channel, non-identity-orientation,
  floating-point and dimensional mismatch payloads.
- `JxlBridge::probe_gray_2d` exposes that bounded operation to Rust. The full
  engine loader must resolve it from the same pinned bridge DSO using
  `JxlBridge::from_symbols_with_probe`.
- `JxlBridge::{encode,decode}_cix_u16_gray_2d` converts between CIX canonical
  little-endian u16 samples and frozen imagecodecs-style UINT8/UINT16 JXL
  transport. UINT8 decode expands to little-endian u16 exactly; UINT16 stays
  little-endian.
- `full_engine::volume_lifting::{encode_spatial,decode_spatial}` implements
  retained CIXI1 mode 1 (JXL). `decode_spatial` parses/checks all paid CIX
  framing, asks `ImageBackend::jpegxl_probe(payload, length / 2, memory)`,
  verifies a single 2-D pixel count, and only then calls the bounded decoder.
  Modes 2/3 remain explicitly unsupported by this JXL-only route.

`cix_jxl_{encode,probe,decode}_planar` implements the frozen imagecodecs
Z/H/W mapping: plane 0 is gray and planes 1..Z−1 are `JXL_CHANNEL_OPTIONAL`
extra channels in index order. The probe receives paid depth and total pixel
count, validates every extra channel's type, depth and no-subsampling contract
before an output buffer is installed, and the decoder writes contiguous
little-endian planes. CIXV1 mode 3 and CIXI2 planar bands use this descriptor;
they are not flattened or shape-reinterpreted.

## Required root integration

The full-engine native image provider must implement the extended
`ImageBackend::jpegxl_probe` contract and return **canonical little-endian u16
bytes** from `jpegxl_decode`, regardless of whether the JXL payload carried
UINT8 or UINT16. A provider using `JxlBridge` should:

1. call `probe_gray_2d(payload, expected_pixels)`;
2. map its 2-D geometry to `JpegxlImageInfo { depth: 1, height, width }`;
3. call `decode_cix_u16_gray_2d` and return its canonical bytes;
4. route `depth == 1` to the gray descriptor and `depth >= 2` with
   `planar == true` to the planar descriptor; reject inconsistent layout flags.

`full_engine::jxl_provider::JxlProvider` is the concrete implementation.  It
accepts only an absolute path to the package-staged `libcix_jxl_bridge` DSO,
uses `dlopen` with that exact path, holds the resulting handle for the lifetime
of all resolved functions, and requires bridge version `12000` before any
codec call.  It does not select a host library or inspect an environment
variable.  `CIX_TEST_JXL_BRIDGE` is used solely by the opt-in integration test:
when unset the test returns without exercising a real library; when set, a
missing, wrong-version, or unloadable absolute bridge is a test failure.

The provider's metadata codec is exposed by the same CIX-owned bridge through
`cix_lzma_compress_preset9` and `cix_lzma_decompress_exact`. These use the
public `<lzma.h>` buffer APIs, rather than a Rust mirror of `lzma_stream`.
They emit an XZ stream with Python-compatible
`lzma.compress(..., preset=9)` settings (CRC64), bound allocation with
`lzma_stream_buffer_bound`, reserve the Rust result copy before the C++ decode
allocation, and require exact source consumption and exact paid output length
on restore. The normal native package already declares liblzma as a required
system dependency.

The C++ exported symbols are now:

- `cix_jxl_encode_gray_2d`
- `cix_jxl_probe_gray_2d`
- `cix_jxl_decode_gray_2d`
- `cix_jxl_free_buffer`
- `cix_jxl_library_version`
- `cix_jxl_bridge_version`
- `cix_lzma_compress_preset9`
- `cix_lzma_decompress_exact`

## Focused qualification after root provisions libjxl

These are not performed by the mock Rust tests:

1. Configure `rust/cix-native/codecs/jxl` with the immutable shared libjxl
   0.12 prefix: `cmake -S rust/cix-native/codecs/jxl -B <bridge-build>
   -DCIX_JXL_ROOT=<jxl-prefix> -DCMAKE_BUILD_TYPE=Release`.
2. Build/install the bridge and inspect its exported symbols plus the staged
   dynamic dependency graph. Verify `cix_jxl_library_version() == 12000` and
   no Python, imagecodecs or host libjxl 0.7 dependency.
3. Run bridge fixtures for 2-D 8-bit plus every 9–16-bit depth, including
   low/high sample values. Validate native encode/decode semantic equality and
   frozen imagecodecs CIXI1 payload decode.
4. Run malformed, truncated, over-cap and wrong-paid-pixel-count probes. The
   probe must reject before any decoder image output buffer allocation.
5. Run CIXI1, CIXV1 mode 3 and CIXI2 restore/checksum fixtures. Generate the
   frozen imagecodecs Z/H/W 8/16-bit oracle with `planar_fixture.py`; the
   native harness must prove semantic equality in both directions.

The opt-in Rust integration test is
`full_engine::jxl_provider::tests::packaged_bridge_roundtrips_canonical_frames`.
With `CIX_TEST_JXL_BRIDGE` set to the staged absolute bridge path, it validates
8-bit and 16-bit canonical CIX u16 conversion, rejects a deliberately wrong
paid pixel count before decode, and round-trips CIXI1 plus the supported
flattened CIXV1 mode 1 frame, CIXV1 mode 3 planar frame, and a CIXI2 planar
band frame. It does not replace the external imagecodecs fixture qualification.

Mock `jxl_bridge.rs` tests prove only Rust ABI/version/error/buffer ownership
control flow. They do not prove libjxl linkage, bit-depth semantics, C ABI
layout, cross-decoding or physical-resource behavior.
