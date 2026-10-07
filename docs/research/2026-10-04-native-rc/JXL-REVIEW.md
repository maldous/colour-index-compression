# JXL native bridge review — 2026-10-04

## Scope and evidence

This is a source-only review of the CIX-owned bridge in
`rust/cix-native/codecs/jxl/` against the pinned libjxl `v0.12.0` C headers
and the frozen wrappers:

- `runtime/cix_runtime/legacy/volume_image_codec.py`
- `runtime/cix_runtime/legacy/multiscale_volume.py`
- `runtime/cix_runtime/legacy/spatial_image_codec.py`

No dependency was downloaded, built, installed, or tested for this review.
The existing host has wheel-private libjxl 0.12 binaries but no matching public
headers; those wheel files are evidence only and must not be linked or shipped.
The system libjxl 0.7 is not an acceptable fallback.

Primary API sources: [libjxl v0.12 encode.h](https://raw.githubusercontent.com/libjxl/libjxl/v0.12.0/lib/include/jxl/encode.h), [decode.h](https://raw.githubusercontent.com/libjxl/libjxl/v0.12.0/lib/include/jxl/decode.h), [thread runner header](https://raw.githubusercontent.com/libjxl/libjxl/v0.12.0/lib/include/jxl/thread_parallel_runner.h), and [official build instructions](https://github.com/libjxl/libjxl/blob/main/BUILDING.md). Provenance constraints are in `JXL-BUILD.md` beside this note.

## Review result

### Confirmed API use

The bridge uses actual v0.12 functions and call ordering:

- `JxlEncoderInitBasicInfo`, `JxlEncoderSetBasicInfo`, a grayscale sRGB color
  encoding, frame settings, `JxlEncoderSetFrameBitDepth`,
  `JxlEncoderSetFrameLossless`, and `JxlEncoderSetFrameDistance(0.0f)` are
  valid encoder operations. The last setting is required by the frozen
  imagecodecs 2026.8.16 route note for libjxl 0.12.
- `JxlThreadParallelRunnerCreate(..., 1)` and the encoder/decoder parallel
  runner setters are valid and retain the frozen one-worker policy.
- Decoder basic-info validation occurs before `JxlDecoderSetImageOutBuffer`.
  `JxlDecoderSetImageOutBitDepth` is correctly set only after the output
  buffer, as specified by the v0.12 API.
- The raw bridge has a paired output allocation/free function; its Rust binding
  checks returned length before creating a slice.

### Confirmed limits

The implementation is deliberately a two-dimensional, single-gray-plane
adapter. That matches a future CIXI1 encoder only after the native framing
layer knows the image shape. It does **not** restore CIXV1/CIXI2 volume or
planar semantics:

- CIXV1 modes 0, 1, 2, 4, and 5 reshape transformed data to a 2-D plane, but
  mode 3 passes the native three-dimensional volume with `planar=True`.
- CIXI2 leaf bands pass a 3-D array with `planar=True` whenever the first
  dimension is greater than one.

The bridge must remain unavailable for those inputs. Flattening, transposing,
or treating depth as a grayscale channel would create an unqualified new
representation. A separate descriptor and fixture-derived imagecodecs mapping
are required before enabling either route.

## Required corrections or decisions before admission

| Priority | Finding | Evidence and consequence | Required resolution |
| --- | --- | --- | --- |
| P0 | CIXI1 legacy decode has no dimensions for this bridge. | The frozen CIXI1 frame stores only `original`, `offset`, `n`, metadata and JXL payload length. The bridge requires expected width, height, bit depth and type before it can install a bounded image buffer. | Retain an explicit legacy-decode path, or add a bounded CIX-owned basic-info probe which checks `width * height * sample_bytes == n` before any pixel buffer. Do not call the current 2-D decode API with inferred/unbounded dimensions. |
| P0 | Shared-library closure is not yet a package recipe. | `CMakeLists.txt` links the bridge to `jxl` and `jxl_threads`, but installs only `cix_jxl_bridge`. The observed v0.12 wheel core additionally needs `jxl_cms`, Brotli libraries and C++ runtime libraries. A bridge `$ORIGIN` RUNPATH does not itself prove transitive dependency lookup for every staged DSO. | Provision a shared v0.12 install prefix; stage `libjxl`, `libjxl_threads`, `libjxl_cms` and every dependency reported by the built target's ELF/Mach-O/PE graph. Give each staged DSO an appropriate relative loader path, then verify the staged bridge resolves only staged dependencies. Do not rely on host `libjxl.so.0.7` or wheel files. |
| P1 | CMake does not reject an accidentally static `libjxl` selection. | `find_library` accepts either archive or shared library. A static core requires its complete transitive link closure, which the current bridge recipe does not enumerate. | First qualification must explicitly provision and select shared v0.12 libraries. Treat a static configuration as a separate packaging decision requiring a complete target-export/link-closure receipt. |
| P1 | The C ABI bounds returned stream size but not libjxl working memory. | `max_output_bytes` stops the bridge's emitted vector; core encoding/decoding may still allocate internal workspace. | Invoke the bridge only inside the existing CIX memory/cancellation admission boundary. Add focused resource tests after dependency provisioning; do not present the output cap as a total-memory cap. |
| P1 | 16-bit byte order is now CIX-defined, but needs cross-platform evidence. | The bridge uses `JXL_LITTLE_ENDIAN` for UINT16. That follows frozen source bytes (`dtype='<u2'`) and avoids host-endian archive ambiguity. It changes nothing on the current little-endian host. | Qualify 9–16 bit fixtures, including values near each depth maximum, on every packaged architecture. Confirm frozen imagecodecs payload decode and native encode/decode preserve the byte sequence. |
| P2 | Decoder strictness is good for CIX-produced raw codestreams, but container compatibility remains unqualified. | It rejects preview, animation, extra channels and non-identity orientation, allows the decoder's normal container detection, and requires no remaining input at success. CIX's new encoder does not force a container. | Test both native output and retained frozen payloads. If a valid retained container leaves unprocessed bytes after final image decode, decide whether to reject it as outside CIX's stored payload contract or explicitly consume/validate its allowed boxes. Do not relax the check without fixture evidence. |
| P2 | The bridge can report status but not a bounded diagnostic message. | Header defines only status codes. This is sufficient for deterministic codec failure, but a release receipt needs the upstream error category and CIX context to distinguish malformed input, bounds rejection and allocation failure. | Keep status codes as the stable archive-facing contract; have the Rust/full-engine caller record bounded CIX context. Do not add exception text or host-dependent diagnostics to the archive format. |

## Exact provisioning plan

1. Materialize a recursive, immutable `libjxl v0.12.0` source closure at the
   signed tag recorded in `JXL-BUILD.md`; record the source/submodule manifest
   digest. Do not use the GitHub web tarball alone because upstream documents
   that it omits required submodules.
2. Build and install a **shared** core prefix with its upstream CMake project,
   retaining encoder, decoder, CMS and thread-runner components. Record CMake,
   compiler, cache and enabled dependency configuration. The focused CIX build
   needs installed headers `jxl/encode.h`, `jxl/decode.h` and
   `jxl/thread_parallel_runner.h`, and linkable `jxl`, `jxl_threads` and the
   core's emitted runtime closure.
3. Configure the CIX bridge only with `-DCIX_JXL_ROOT=<that-prefix>`. Its
   `NO_DEFAULT_PATH` lookups are the required guard against system 0.7.
4. Stage the bridge and all library dependencies in one package-private loader
   directory. Inspect the final dynamic dependency graph and loader paths from
   the staged artifact, not from the build tree. Require absence of Python,
   imagecodecs, and host libjxl paths.
5. Verify `cix_jxl_library_version() == 12000` through the staged library,
   then run only the focused 2-D semantic, malformed-input, cap and
   cross-decoding fixtures listed in `JXL-BUILD.md`. First address the CIXI1
   bounded basic-info decision and retain volume/planar exclusion until its
   own evidence exists.

## Admission statement

The present source is a viable narrow 2-D libjxl 0.12 ABI foundation. It is
not yet a qualified restored JXL route or a complete package dependency
closure. The two blocking actions are the bounded CIXI1 shape/probe decision
and a staged shared-library closure receipt; CIXV1/CIXI2 planar support is
intentionally outside this bridge's current claim.
