# Native foundation implementation checkpoint — 5 October 2026

The first implementation wave has passing component evidence. **The complete
0.1 release plan is not complete; the final benchmark and publication remain
held.** No compression record or throughput improvement is claimed here.

## Implemented

- Extracted the reusable native codec engine from CLI file/process handling.
- Added the versioned whole-buffer C context API, C++ ownership wrapper,
  shared/static libraries, CMake and relocatable pkg-config installation.
- Added caller-driven Rust incremental encoding/decoding with consumed/produced
  counts, backpressure, partial-block flush, checked termination, cancellation,
  whole-stream deadlines and reset. This is explicitly the independent CIXG1
  profile with blocks up to 64 KiB; C streaming/chunk APIs and full-engine
  retained-history streaming remain open.
- Added the same-executable PAQ parent supervisor with bounded diagnostics,
  private temporary output, direct-child cancellation/deadline cleanup and
  explicit installed-library paths.
- Completed the native JPEG XL gray/planar bridge and provider for the retained
  image/volume frames. The pinned upstream source was not modified. Known CIX
  buffer coexistence is accounted; libjxl internal memory is not a hard RSS cap.
- Ported the retained hydrogen, record/grid and executable relation mechanisms,
  including section pointers, symbol loads and procedure-address parents.
  Exact supported modes are in the source and coverage inventory.
- Added the historical raw/PAQ outer containers, CIXH1 mixed carrier and bounded
  input-derived region discovery. The carrier and recognizers are library
  primitives; they do not yet establish automatic mixed-content selection.

## Evidence and limits

| Evidence | Result |
| --- | --- |
| Foundation v8 native core command | 110 tests passed; the enclosing job later failed specialist tests, preserved in full |
| Foundation v12 | Build/check passed; 53/54 specialist tests passed, plus all selected bridge, actual PAQ worker, C ABI, incremental and existing integration checks |
| Foundation v13 | Corrected malformed-input test and complete address module passed; relocated shared **and static** SDKs compiled and ran from independent C/pkg-config and C++/CMake consumers |
| Remaining v1 | CLI portfolio and PAQ protocol unit tests passed on the identical v13 snapshot |
| JXL bridge v3 | Six gray and 18 planar generated cases restored exactly in both reference/native directions |
| Address fixture v4 | Nonzero pointer/load/procedure events and the ambiguous-symbol control matched native raw bytes and exact inverses |

The previously failing malformed-input test modified a length byte to its
existing value. Its replacement mutates the actual mode and separately corrupts
the paid length. Earlier tests also found real double-residual, missing-length,
and deterministic arithmetic-termination porting bugs; those fixes now pass.
All attempts and failures are retained. Opt-in real-provider tests were enabled
with the actual pinned DSOs; an absent-provider no-op is not counted as proof.

For JPEG XL, exact cross-decoding is established on these generated cases.
Earlier 8-bit gray outputs were byte-identical to the reference; 16-bit gray
outputs had equal sizes with differing bytes. This is not a general encoder
bitstream-parity or corpus-size claim.

[The machine evidence](foundation-evidence.json) binds job receipts and source
manifests. v12-to-v13 changes are the address test correction and SDK metadata;
other passing v12 source is unchanged. The native engine/primitives exercised
by v8 remain unchanged, with the new incremental module checked separately.
No single enclosing failed job is labelled a total pass.

All heavy work used the root scheduler and the existing four-core/no-swap
policy. For illustration, the focused v13 build/install check took 13.20 seconds
wall and 21.52 CPU seconds, with sampled cgroup memory 1,296,470,016 bytes and
tracked temporary footprint 3,717,715,686 bytes. Sampled memory is a lower bound,
not a true peak. These are validation costs, not compression throughput figures.

## Remaining release work

The native specialist catalogue, ordinary CLI admission and historical decoder
routing are still missing. Library functions do not satisfy those requirements.
Other retained ports, full-engine streaming and job protocol, C incremental and
chunk interfaces, formats/dictionaries, application and filesystem adapters,
actual platform execution, dependency export closure, final Sonar/dead-code
work and RC51 readiness remain open in the authoritative coordinator ledger.
The current SDK is a native buffer package, not a complete full-engine release.

Exactly one next action: **implement and qualify the native specialist
catalogue and archive decoder dispatch using the tested providers and
transforms.** The remaining programme then follows the approved dependency order.
