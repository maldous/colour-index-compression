# GPU/CUDA distribution and interoperability assessment

**Scope and status — 2026-10-04.** This is a design and packaging assessment only. No GPU workload, benchmark, driver change, dependency installation, or codec implementation was run. A GPU path is not a 0.1 release prerequisite: CIX must remain a useful CPU-only command-line utility on every supported platform.

## Evidence and opportunity

nvCOMP is a GPU library for lossless compression. Its standard formats include LZ4, Snappy, Deflate/Gzip and Zstandard; its Cascaded, Bitcomp and ANS formats are NVIDIA-specific. That distinction matters: standard-format output can use ordinary CPU decoders, while NVIDIA-specific formats require an explicitly qualified decoder; the presence of a standard algorithm name does not establish that a high-level nvCOMP envelope is a standard file. nvCOMP requires a Volta-or-newer GPU, supported driver and CUDA toolkit; its documented Linux support is broad but its current macOS path is absent. Windows support is documented, while RAPIDS documents Windows through WSL for its nvCOMP stack. These facts support **an optional accelerator**, not a universal archive dependency.

GPU throughput might help large independent blocks or a deployment that already keeps data resident on the device. It is not a size opportunity by itself, and host↔device transfers, setup, GPU memory pressure and final archive framing can erase gains for ordinary CLI inputs. No performance claim follows from this review.

## Product policy

The normal binary and every base package remain fully usable on CPU-only systems. It must build, install and decode without an NVIDIA driver, CUDA toolkit, GPU, GPU package, Python wheel or runtime probe failure. A separately packaged optional GPU feature may be considered only after a measured and reproducible benefit.

A `--gpu=auto|off|required` policy is the appropriate conceptual surface:

- `auto` probes a loaded optional provider, device availability, compute capability, driver/runtime compatibility, supported codec/version, input/block threshold and declared VRAM admission. It records a reasoned CPU fallback in `--explain`; it never changes an archive merely because a GPU is present unless the selected format is explicitly requested/admitted.
- `off` never loads GPU libraries or probes devices.
- `required` fails before encoding when the requested provider/device/budget is unavailable. Decode fails with a stable `unsupported GPU codec` error only for an archive that actually requires a GPU-only method; it must not silently reinterpret bytes.

Capability queries must have bounded, documented effects; GPU context creation and driver initialization are explicit resource operations. CPU-only/off operation must not initialize CUDA. Driver discovery is runtime capability detection, not a build prerequisite. Device selection must be explicit (`--gpu-device` or documented default), with no implicit multi-device scheduling.

## Archive and decoder interoperability

Each distinct wire format needs stable method/version identification, required options, bounded framing and integrity checks. A byte-compatible accelerator preserves the existing wire identifier; provider/build/device identity belongs in qualification and diagnostic records, not mandatory archive metadata when decoding does not depend on it. GPU payloads must be independently bounded before allocation or device dispatch. Archive selection charges format/version metadata, block boundaries and checksums.

Prefer standard LZ4, Deflate/Gzip or Zstandard payloads where they meet the actual use case: CPU decode remains available through existing CIX/library paths and ordinary tools where applicable. Do not label a GPU-produced proprietary format as a standard stream. A CIX-private GPU format requires a CIX CPU decoder or an explicit decoder distribution contract before public use; a GPU-only decoder is unsuitable for the default archival format.

A GPU provider API should receive explicit host/device buffers, maximum output, scratch/VRAM budget, stream/context ownership, cancellation token and deadline. It returns a typed result (completed, unavailable, unsupported, resource-omitted, cancelled, malformed input, backend failure). It must neither install a signal handler nor terminate/print from a library call. Contexts are per operation or explicitly pooled with device affinity; no global device reset. Cancellation is cooperative and must wait for or quarantine in-flight device work before reusable buffers are freed.

VRAM is not covered by the existing host cgroup memory limit. Admission must reserve input, output, scratch, staging/pinned memory and concurrently live buffers per device, then release the reservation only after stream completion. Use a separate per-device budget and account host staging against the existing host memory/temp policy. Host framing/length checks must precede GPU dispatch, but these checks alone do not validate an arbitrary compressed payload. nvCOMP documents several decompressors as accepting only valid input. General-purpose untrusted-archive decoding therefore needs a proven validator/safe decoder or an explicit trusted-data-only capability; a checksum from an untrusted archive is not such a proof. Device-reported errors must become ordinary failures.

## Distribution plan, if later justified

- **Base packages:** existing Debian/RPM/macOS/Windows source/binary packages contain no CUDA dependency and no driver installation. CPU-only CI is mandatory and must prove no dynamic GPU load in `--gpu=off`/default use.
- **Optional provider packages:** publish versioned, architecture-specific GPU add-ons such as `cix-gpu-cuda12` only after a provider ABI is frozen. Debian/RPM dependencies should name the matching NVIDIA runtime package range rather than bundle unreviewed driver files. Windows is a separate signed installer/MSVC runtime path; macOS has no current CUDA/nvCOMP support and therefore receives no CUDA add-on.
- **Build separation:** an optional Cargo feature/plugin boundary may dynamically load a narrow C ABI provider. Keep GPU code out of the default feature graph and emit method IDs from a registry, not compile-time guesses. Reproducible builds bind CUDA major/minor, nvCOMP release, GPU architectures/PTX/fatbin policy, host compiler, link mode and all redistributed library hashes.
- **CI:** CPU-only build/test/package lanes run without any NVIDIA libraries. Optional GPU lanes require pinned runner image, driver/runtime/device identity, GPU model/compute capability, VRAM, warm-up policy and separate performance evidence. Cross-compilation alone is not platform qualification.

NVIDIA’s Linux guidance recommends native DEB/RPM package-manager installation where possible. nvCOMP’s own packages distinguish runtime from development packages, and its metapackage installs system-directory symlinks; an add-on must not assume that a manually installed individual runtime package is discoverable. NVIDIA’s redistribution manifests and the exact package EULA/license must be reviewed for the chosen release and artifact before bundling or redistributing anything. The nvCOMP SDK license has NVIDIA-system and distribution/open-source interaction restrictions; it must be assessed separately from permissively licensed sample code and from each CIX codec license. No redistribution approval is inferred. [Actual nvCOMP license](https://docs.nvidia.com/cuda/nvcomp/license.html).

## Current CIX evidence and disposition

The present native source has CUDA headers excluded because CUDA/OpenMP are disabled in its frozen build (`docs/research/2026-10-04-sonar-cxx-repair/prepared-v1/plan.json`). The current RC baseline targets a native/no-Python runtime and requires real platform qualification; older packaging templates and the prior host-bound runtime are not a CUDA distribution proof. Therefore no GPU feature is added to the RC scope now.

| Class | Item | Disposition |
| --- | --- | --- |
| Must-have if GPU is implemented | CPU-only default; explicit probe/mode; pinned provider/method IDs; bounded host+VRAM admission; CPU decode or explicit CIX decoder distribution; malformed/cancel/concurrency tests; CPU-only and GPU CI; license/redistribution review | Required before a GPU archive route can ship |
| Research question | Whether CIX workloads contain sufficiently large independent blocks or device-resident data to overcome transfer/setup cost; whether standard GPU codecs improve end-to-end throughput under resource limits | Requires a separate frozen, measured experiment; no claim now |
| External dependency | NVIDIA driver/CUDA/nvCOMP packages and their support/redistribution terms; Windows runtime/toolchain; no macOS nvCOMP route; optional AMD hipCOMP is early-access | Never make base installation depend on these |

## Primary sources, retrieved 2026-10-04

- [NVIDIA nvCOMP overview](https://docs.nvidia.com/cuda/nvcomp/) — algorithms and standard versus NVIDIA-optimized formats.
- [NVIDIA nvCOMP installation](https://docs.nvidia.com/cuda/nvcomp/installation.html) — Volta+, OS/architecture, driver/toolkit, DEB/RPM/runtime-development package behaviour.
- [NVIDIA nvCOMP release notes](https://docs.nvidia.com/cuda/nvcomp/release_notes.html) — CUDA-13 stream caveat, Linux C++ compiler constraint and static-package change.
- [NVIDIA CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/latest/) — minor/forward compatibility boundary.
- [NVIDIA CUDA Linux installation guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/) — package-manager recommendation and DEB/RPM support.
- [NVIDIA nvCOMP redistribution index](https://developer.download.nvidia.com/compute/nvcomp/redist/) and [CUDA redistribution index](https://developer.download.nvidia.com/compute/cuda/redist/) — versioned redistribution manifests; inspect the selected manifest/license before release.
- [NVIDIA CUDA EULA, archive 12.9.2](https://docs.nvidia.com/cuda/archive/12.9.2/pdf/EULA.pdf) — historical example of component-specific redistribution terms; not a substitute for the selected release’s terms.
- [NVIDIA Windows CUDA installation guide](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/) — Windows host/toolchain requirements.
- [AMD hipCOMP repository](https://github.com/ROCm/hipCOMP-core/) — AMD alternative is described by its maintainers as early-access/technology preview, therefore not a release dependency.
