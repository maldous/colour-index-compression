# Optional GPU block-sort parity probe specification

Status: specified, **not run or integrated**. This is a bounded correctness
proposal for an existing transform, not permission to restart the stopped
benchmark or change the release candidate. Its purpose is to determine whether
an optional device provider can preserve current libbsc output and CPU decoding.

## Source and isolation

Use the full unchanged upstream libbsc tree at
`baffa62c70b6ebbecc9af14ce550e965ea247680` (3.3.12), including its bundled
libcubwt. Do not modify or enable CUDA against CIX's current minimal CPU vendor
closure: that closure deliberately excludes `st.cu` and the libcubwt body and
contains a CUDA header stub. Keep it as the CPU control.

The read-only Git tree API identifies these source objects at that commit:

| Path | Git object SHA-1 |
| --- | --- |
| `CMakeLists.txt` | `2b8e255f3ec3fd2546064ff1109b84377cd8eeb7` |
| `libbsc/st/st.cu` | `354ea01994020e5a119df250d14a3559d92c99c1` |
| `libbsc/st/st.cuh` | `a3dfdaceacff71442de6465fc18cdcccdca6fe96` |
| `libbsc/bwt/libcubwt/` tree | `6a31cef3f474a9a2e389e6d1c62d94b49098d603` |
| `libbsc/bwt/libcubwt/libcubwt.cu` | `084d2a4677049986dda6008396a75348ae7ec965` |
| `libbsc/bwt/libcubwt/libcubwt.cuh` | `5f308128bd54643c375ad1e06b8eca635c65e59a` |
| `libbsc/bwt/libcubwt/LICENSE` | `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64` |

These are Git identities, **not** downloaded-file SHA-256 checksums. A future
provisioning step must verify the complete checkout/tree and record SHA-256 per
file plus the dependency-closure manifest. Do not substitute a current libcubwt
main branch. Preserve Apache-2.0 notices and separately inventory CUDA runtime
redistribution terms. Source references: [pinned libbsc](https://github.com/IlyaGrebnov/libbsc/tree/baffa62c70b6ebbecc9af14ce550e965ea247680),
[libcubwt](https://github.com/IlyaGrebnov/libcubwt).

Use separate research output directories and CIX-owned glue. Do not mutate the
shipping build, codec source, block policy or archive format. Build CPU and GPU
variants with the same remaining settings. Pin compiler/CUDA/CMake versions,
flags, host architecture and device code target (`sm_75` for this host), library
exports and dependency identities. Verify actual GPU invocation so upstream
CPU fallback cannot be mistaken for a passing GPU test. OpenMP is not required
for the libbsc CUDA path; initially keep it disabled so worker ownership remains
explicit. An unavailable-device control must succeed through the documented CPU
fallback and report which provider ran.

## Resource and device admission

Root alone schedules any future focused job under the shared four-physical-core,
12,000,000,000-byte host RAM, 4,000,000,000-byte temporary and no-swap limits.
VRAM is a separate explicit device budget, never an exemption from host limits.
Only one device job is proposed on the local GTX 1650/4 GiB. Query free VRAM at
admission and after context setup; the earlier host snapshot is not a reservation.

libcubwt documents approximately `20.5 * n` device bytes; at 128 MiB source this
is 2.5625 GiB before additional allocations. A 256 MiB case is excluded on this
host. Calculate the checked workspace/staging requirement for the exact build,
include context/driver and input/output buffers, reserve 512 MiB device headroom,
and admit only if the total fits both the device budget and current free VRAM.
The estimate is an admission screen, not a guarantee against another application
allocating VRAM. Allocation failure must release resources and return a typed
failure/fallback. No retry with smaller blocks may be reported as the same test.

An explicitly disabled provider must not initialize CUDA. A runtime probe that
creates a device context must be disclosed and measured. Avoid changing host
power, cooling, clock or desktop GPU settings.

## Correctness cases and acceptance

Use generated fixtures only: empty, one-byte, repeated single symbol, all 256
symbols, periodic strings, and fixed-seed arbitrary bytes. Exercise boundary
sizes of the actual upstream API, then 64 KiB, 1 MiB, 16 MiB, 64 MiB and at most
128 MiB where admitted. This does not acquire or run evaluation corpora.

For each admitted case retain source identity, transform bytes/primary index,
complete BSC payload, actual provider, build identity and CPU-only inverse
result. Require:

- exact CPU/GPU transform and complete payload equality for the **byte-identical
  acceleration** classification; a valid alternative payload is a separate
  encoder qualification, not a pass for this narrower claim;
- independent CPU decode recovering every input byte without CUDA;
- a repeated correctness invocation with the same output (no speed average);
- unavailable-device, rejected-size and allocation-failure cleanup, using CIX
  glue fault injection where needed rather than intentionally exhausting VRAM;
- independent-context ownership and no unintended change to a caller's CUDA
  stream/device or process environment;
- bounded malformed-input rejection on the CPU decode boundary. This probe
  does not qualify GPU decoding of untrusted archives.

Do not infer throughput from correctness wall times. Preserve failures and
unsupported cases as results. Promotion requires separate native integration,
SDK/process semantics, licenses, installed CPU-only-host behavior and final
source quality evidence.

## Later performance question

Only a separately admitted frozen plan may time cold and warm execution,
allocation, host/device transfers, transform, entropy coding, complete CLI
encode and independent CPU decode. Record complete archive bytes, host/device
peaks, CPU seconds, wall time, selected/fallback provider and device contention.
Measure the existing BWT share of runtime before interpreting an isolated
kernel improvement; if that share is `f`, overall speedup cannot exceed
`1 / (1 - f)` even with infinitely fast BWT. PAQ-dominated selection may gain
little from a faster BWT candidate. No numerical CIX gain is predicted here.
