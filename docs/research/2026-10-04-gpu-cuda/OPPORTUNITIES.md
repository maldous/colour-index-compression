# GPU and CUDA opportunity audit

**2026-10-04 — research findings, not measured CIX gains.** The source review,
primary-source methodology search and local hardware preflight are complete.
No GPU kernels, codec experiments, dependency installations or benchmarks ran.
The broader release gate and stopped benchmark remain unchanged.

## Findings and disposition

There are credible additional opportunities. None establishes that CIX has
reached a compression or throughput limit, and none currently qualifies a GPU
feature for distribution. Separate three cases:

1. Accelerate an existing exact transform while preserving its archive bytes.
2. Use another encoder for an existing standard format; restored bytes must
   match, but compressed bytes and compression ratio may differ.
3. Add a predictive model or a new codec/format; this may change compression
   ratio and needs full model, metadata, decoder and resource qualification.

| Candidate | Potential value | Evidence and current disposition |
| --- | --- | --- |
| libbsc plus libcubwt | Faster existing BWT and inverse BWT | Strongest direct source connection. Pinned libbsc already has a conditional CUDA implementation. First focused acceleration candidate; parity and speed remain unmeasured. |
| nvCOMP LZ4, Snappy, Deflate/Gzip, Zstd | Standard-format throughput and optional device-buffer SDK | Consider as optional providers. Verify raw payload versus framed stream for each API; GPU native envelopes are not automatically standard files. No new CIX method ID is needed solely because the executing device changes if existing payload semantics truly match. |
| ndzip | Additional exact scientific-array codec, including CPU/GPU interoperation | Upstream reports identical CPU/CUDA/SYCL streams. Candidate for typed, shaped arrays with all shape/endian metadata paid; arbitrary IEEE bit-pattern preservation and current build support still need local evidence. |
| GDeflate, Cascaded, Bitcomp lossless, ANS/rANS, dietGPU, GFC/MPC | Parallel entropy coding, typed residuals, device-resident data and fast decode | Retain in methodology ledger. Distinct formats, CPU decoder availability, maintenance, redistribution and full memory/transfer costs decide applicability. Error-bounded modes are excluded. |
| NNCP / LibNC | An additional neural compression model with CUDA support | Genuine existing implementation, not dismissed by the closed CIX mixture experiment. Current documented GPU path exceeds this host's architecture/memory; source-only distribution and cross-device decoding remain unresolved. |
| Histograms, checksums, transforms and match search | Internal stage acceleration | Keep as component candidates only where profiling shows material CPU cost and sufficient independent work. They do not establish improved predictions or smaller archives. |

Primary method details and exclusions are in [METHODOLOGIES.md](METHODOLOGIES.md).
Product and packaging contracts are in [DISTRIBUTION.md](DISTRIBUTION.md) and
[source-requirements.json](source-requirements.json).

## Actual local capability

[host.json](host.json), produced by [probe_host.py](probe_host.py), records a
GTX 1650 (SM 7.5), 4 GiB VRAM, driver 580.173.02, and CUDA 12.1. NVCC exists at
`/usr/local/cuda/bin/nvcc` but is absent from PATH. The observation had roughly
3.7 GiB unused VRAM; this is not a reservation. Neither nvCOMP nor libcubwt was
listed in the dynamic linker cache. Private installations were not exhaustively
searched, and no kernel compatibility was tested.

This host meets nvCOMP's published architecture, driver and toolkit floors;
missing provider/build qualification is not evidence that the GPU is inherently
ineligible. Blackwell's hardware decompression engine is a different capability
and must not be attributed to this Turing device. [NVIDIA installation](https://docs.nvidia.com/cuda/nvcomp/installation.html),
[decompression engine](https://docs.nvidia.com/cuda/nvcomp/decompression_engine_faq.html).

libcubwt documents approximately 20.5 input bytes of device storage per source
byte. At 128 MiB this is about 2.56 GiB before additional buffers; 256 MiB would
exceed 4 GiB. Smaller bounded checks are plausible on this host once the actual
source/toolchain build is qualified. Ada is recommended upstream, but is not
stated as a hard minimum. Upstream timings used different hardware and excluded
initialization/allocation, so they are not CIX performance estimates.
[libcubwt source and methodology](https://github.com/IlyaGrebnov/libcubwt).

NNCP's current readme specifies Ampere/Ada/Hopper for CUDA, with its published
large-model example using 6.6 GB GPU memory. The GTX 1650 is not that documented
target. NNCP code is MIT; LibNC is supplied as a redistributable binary, and
its published cross-platform reproducibility promise is CPU-only. Treat those
as architecture, source-availability and decode-compatibility questions, not a
reason to claim neural compression has no opportunity.
[NNCP readme](https://bellard.org/nncp/readme.txt), [LibNC](https://bellard.org/libnc/).

## Existing-code connection and limits

Source identities are bound in host.json. In the retained libbsc `bwt.cpp`,
`LIBBSC_CUDA_SUPPORT` enables device execution; `LIBBSC_OPENMP` selects shared
locked storage, while non-OpenMP builds use per-call device storage. Both macros
are not required together. The wrapper has no input-size profitability threshold,
and a failed GPU BWT falls back to CPU. CIX's build disables CUDA/OpenMP and its
FFI never requests CUDA. The minimal vendor closure lacks the CUDA implementation;
its presence cannot be inferred from the retained header.

BWT acceleration cannot directly speed the sequential PAQ trials that dominated
some BEST runs. If BWT accounts for fraction f of end-to-end time, even infinitely
fast BWT limits overall acceleration to 1/(1-f). Measure f, startup, copies and
contention; do not substitute an isolated kernel rate for CLI throughput. Splitting
long-context models to create GPU batches is a changed compressor needing separate
compression-quality evidence. No transform or predictor branch is reopened here.

## Exactly one evidence-selected next action

The isolated optional [libbsc/libcubwt parity specification](PROBE-SPEC.md) is
prepared, with unchanged source identities, CPU-only decode and device admission.
The selected next action is to qualify that isolated provider for correctness
under the source/resource gate when root schedules it. No GPU job, benchmark
launch or RC promotion has occurred. This remains the smallest direct
existing-code opportunity; the native CPU release work retains priority.

The future correctness gate uses generated empty/tiny/repetitive/all-byte/random
inputs, then bounded 64 KiB/1 MiB/16 MiB/64 MiB/128 MiB cases admitted by actual
VRAM queries. Require byte-identical BSC payloads for this acceleration claim,
CPU restoration, repeated determinism, unavailable-device fallback and clean
allocation-failure behavior. Later performance work must separately report cold
and warm transfer-inclusive timings, kernel share, complete archive bytes, host
and device peaks, input/output copies and CPU costs under a frozen plan. No run
is authorized by a suggested repetition count in this document.
