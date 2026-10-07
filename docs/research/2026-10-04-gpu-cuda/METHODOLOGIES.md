# GPU/CUDA compression methodologies — bounded RC review

**Reviewed:** 2026-10-04. This is a source/prior-art review, not a GPU test,
throughput claim, package decision, or benchmark result. CIX currently has no
CUDA runtime, GPU scheduler, or GPU codec provider in its native dependency
set; its retained BWT vendor deliberately excludes CUDA-only sources. See
[`rust/cix-native/vendor/libbsc/UPSTREAM.md`](../../../rust/cix-native/vendor/libbsc/UPSTREAM.md).

## Decision frame

GPU execution is useful only when the input is already device-resident or a
batch is sufficiently large to repay host/device transfer, allocations,
synchronization, device workspace and output-copy costs. GPU throughput claims
from A100/Blackwell or HPC interconnect workloads do not transfer to CIX's
ordinary CLI, arbitrary file sizes, CPU decode requirement, portable package,
or complete-archive objective.

“Lossless” below is separated into three meanings:

* **Byte exact:** restoration preserves every input byte, including IEEE NaN
  payloads and signed zero when the input is a byte stream.
* **Numerically lossless:** values compare equal under a numerical model but
  IEEE byte patterns may not be preserved. This is insufficient for CIX unless
  a codec proves byte-exact restoration for its declared input representation.
* **Lossy/error-bounded:** excluded from CIX lossless routes.

## Methodology ledger

| Method | Format / compatibility | Data and concurrency assumptions | Evidence, availability and caveat | CIX disposition |
| --- | --- | --- | --- | --- |
| nvCOMP LZ4, Snappy, Deflate/Gzip, Zstd | Standard LZ4/Snappy/Deflate/Gzip/Zstd options are the only GPU family here with plausible conventional-format interoperability; exact bitstream compatibility still needs per-codec/version test. | Batched equal-sized chunks, GPU workspace and CUDA stream; chunk metadata and alignment are caller duties. CPU fallback must encode/decode identical declared format. | NVIDIA documents these algorithms and batched C API requirements ([docs](https://docs.nvidia.com/cuda/nvcomp/), [low-level API](https://docs.nvidia.com/cuda/nvcomp/samples/lowlevel_c_quickstart.html)); nvCOMP SDK license, not an open-source dependency ([license](https://docs.nvidia.com/cuda/nvcomp/license.html)). | **Consider later as optional accelerator.** Only after native CPU codec route, pinned CUDA/provider ABI, GPU/CPU compatibility fixtures, resource accounting, and a measured transfer-inclusive workload. Never required for default decode. |
| GDeflate | Custom GDeflate stream, not ordinary DEFLATE: bit-swizzled for parallelism. | GPU-oriented chunks and padding; 32-way decode structure. | NVIDIA calls it a new format that only closely matches DEFLATE ([format docs](https://docs.nvidia.com/cuda/nvcomp/gdeflate.html)). | **Defer.** A CIX container could carry it as a distinct optional backend, but it is not a transparent Deflate replacement and adds decoder/distribution work. |
| nvCOMP Cascaded | GPU-native typed/structured-data format, not a general CPU interchange format. | Typed columns; delta/RLE/bitpack-style staged transform and GPU batches. | nvCOMP describes it as high-throughput analytical/structured compression ([algorithm list](https://docs.nvidia.com/cuda/nvcomp/)); proprietary SDK license applies. | **Research only.** It overlaps CIX's paid numeric/grid transforms; no novelty or byte-saving evidence on CIX frames. |
| nvCOMP Bitcomp | Native nvCOMP format; Bitcomp product material includes both lossless and error-bounded modes. | Scientific/typed data; GPU memory/workspace. | NVIDIA documents Bitcomp as proprietary; sample material explicitly includes error-bounded floating-point use ([samples](https://github.com/NVIDIA/CUDALibrarySamples/blob/main/nvCOMP/examples/README.md)). | **Reject lossy modes; defer byte-exact mode.** A byte-exact proof, stream specification, CPU fallback and license review are required. |
| nvCOMP ANS/gANS | Native entropy stream, not CIX's current range/Huffman stream. | Many independent chunks and precomputed histograms; GPU parallelism comes from block independence. | nvCOMP lists ANS as proprietary ([docs](https://docs.nvidia.com/cuda/nvcomp/)). | **Defer.** ANS is established prior art and would need table/framing/termination and CPU decoder compatibility, not a GPU-only claim. |
| dietGPU generalized rANS / float codec | Custom CUDA device-pointer API; no CIX/CPU wire compatibility established. | Large GPU-resident ML/HPC tensors; batch/warp parallelism. | MIT repository but archived 2026-06-14; README labels it early alpha and reports A100-only measurements ([repository](https://github.com/facebookresearch/dietgpu)). | **Research only.** Useful design reference for parallel entropy coding, not an RC dependency or portable CLI backend. |
| Parallel histogram, entropy and match search kernels | Implementation techniques, not a compression format. | Independent blocks; global histograms/matches require synchronization and can change tie/order semantics. | nvCOMP's batch API documents chunk splitting, workspace and load balancing ([API](https://docs.nvidia.com/cuda/nvcomp/samples/lowlevel_c_quickstart.html)). | **Consider as internal acceleration only.** Preserve CIX's exact deterministic candidate order, full framing and CPU fallback; first measure CPU bottleneck and transfer-inclusive benefit. |
| ndzip | Lossless IEEE scientific-grid compressor with its own stream; claims CPU/GPU bit-identical streams. | Single-precision/double-precision multidimensional grids; CUDA >=11, NVIDIA CC >=6.1; HPC use case. | Open-source MIT repository, but research project and Linux/HPC prerequisites ([repository](https://github.com/celerity/ndzip)). | **Consider optional scientific specialist after native grid parity.** Require byte-level fixtures for NaNs/signed zero, pinned dependency/platform support and complete CIX envelope accounting. |
| FPC | CPU float64 predictor stream, distinct from GPU proposals and CIX framing. | Aligned streams of IEEE-754 binary64 words; predictor history is sequential. | Original FPC work is distinct from Falcon; a maintained MIT implementation documents an 8-byte input multiple and float64 scope ([implementation](https://github.com/spenczar/fpc)). | **Consider as CPU scientific baseline, not a GPU route.** Require raw IEEE bit-pattern tests. |
| GFC | CUDA float64 compressor with its own stream. | Little-endian binary IEEE doubles, multiple-of-8 input, CUDA warp/block tuning and transfer overhead. | The original author page provides CUDA source and warns that standalone use is slow due to PCI transfers ([GFC v2.2](https://userweb.cs.txstate.edu/~burtscher/research/GFC/)); source has an embedded license. | **Conditional shortlist.** Pin and review source/license; prove raw IEEE bits, including NaNs and signed zero. |
| MPC v1.2 | CUDA binary IEEE float32/float64 streams, little-endian only. | Input lengths divisible by 4/8; dimensions and device transfer costs matter. | The [original author page](https://userweb.cs.txstate.edu/~burtscher/research/MPC/) supplies source, embedded license and the 2015 Cluster paper; it explicitly warns that standalone PCI transfers are slow. | **Conditional scientific candidate.** Source/license inspection, raw IEEE edge cases, CPU decode and framing remain unqualified. |
| FZ-GPU / cuSZ family | Error-bounded lossy scientific compression pipeline. | CUDA scientific arrays and a selected error bound. | FZ-GPU describes itself as lossy and requires an error bound ([repository](https://github.com/szcompressor/FZ-GPU), [paper](https://arxiv.org/abs/2304.12557)). | **Reject for CIX lossless compression.** A lossless entropy stage after quantization does not restore original bytes. |
| GPU BWT/bzip2 | BWT is a transform; bzip2 compatibility exists only when exact bzip2 framing is emitted. | Large blocks; suffix sorting, MTF/RLE and entropy stages have synchronization/memory costs. | CIX libbsc excludes CUDA sources. The primary CUDA library is [libcubwt](https://github.com/IlyaGrebnov/libcubwt); source/license/API stability need a pinned review. | **Conditional shortlist for transform speed.** Preserve existing CIX/BWT framing and CPU decode, or use an explicit optional backend. |
| NNCP v3.3 + LibNC | Real C neural lossless compressor with CUDA support, model/program payload and its own format; it is not implied by CPI1's small gate. | Text/model inference; model state, CUDA runtime and deterministic floating-point behavior matter. | Bellard publishes C/LibNC NNCP v3.3 Linux/Windows CUDA artifacts ([NNCP](https://bellard.org/nncp/)). The [readme](https://bellard.org/nncp/readme.txt) identifies MIT NNCP sources and binary LibNC; cross-device decode and source-only packaging remain unqualified. | **Conditional research shortlist, not RC default.** Require complete model-byte accounting, reproducible inference and CPU fallback or explicit GPU-only route. |
| Other neural sequential compressors / learned gates | Custom model/container plus model weights and sequential probability assignment. | Accelerator inference does not remove causal coding, model transfer/storage or decoder determinism. | CPI1 rejects only its named small CIX causal gate, not NNCP or all neural codecs. | **Defer individually.** Require named codec, license, wire format, model accounting and exact decode proof. |

## Additional open-source and cross-vendor candidates

The [LC framework](https://github.com/burtscher/LC-framework) is a particularly
relevant methodology reference: lossless CPU/CUDA/HIP components, deterministic
cross-device streams and standalone code generation under BSD-3-Clause. It uses
independent 16 KiB component chunks; whole-input preprocessors have separate
capabilities. Its post-March-2025 format changed and it is little-endian-only.
Consider a pinned, bounded subset and exact CPU/GPU interoperability before any
search. Preserve CIX's closed composition result: this is a distinct parallel
implementation reference, not permission to restart a broad transform tournament.
Lossy preprocessors and always-pass verifiers are ineligible.

[GPULZ](https://github.com/hpdps-group/ICS23-GPULZ) is a separate multibyte LZSS
research candidate. A lossless stage on an already quantized scientific field
does not prove exact compression of the original pre-quantization data. Source,
license, framing, CPU decoder and special IEEE-value coverage must be qualified.
[ALP](https://github.com/cwida/ALP) is an additional exact floating-point CPU/control
reference; this review has not established an upstream production GPU provider,
so no GPU capability is assigned to it. These mechanisms extend the evidence
queue; they do not establish a CIX record or exhaust every possible method.

## Existing CIX overlap and non-novelty

CIX already has CPU-side exact transforms for numeric/grid/volume data, range
and Huffman-style entropy coding, BWT research routes, LZ matching and
candidate selection. GPU delta/RLE/bitpack, histogramming, ANS and parallel
match search are established techniques, not a new compression theory or a
reason to reopen the closed numeric-composition/predictive-mixture branches.
Any future provider must compare complete CIX archive bytes, metadata,
termination, host/device copies, CPU fallback, encode/decode time and peak
host/device memory against the same CPU route.

## Conditional candidate shortlist

This finite shortlist is not an RC mandate or a claim that a GPU route wins:

1. Conventional nvCOMP acceleration for already-supported LZ4, Snappy,
   Deflate/Gzip or Zstd where data is device-resident or sufficiently batched
   and CPU format compatibility is proved.
2. libcubwt acceleration of existing BWT work while preserving an exact current
   CIX/BWT frame and CPU decoder.
3. ndzip or GFC-class byte-exact scientific routes after original source,
   license and adversarial IEEE raw-bit fixtures are qualified.
4. NNCP v3.3 as a separately bounded text candidate after its LibNC runtime,
   license, model bytes and deterministic CPU/CUDA decode contract are known.

## RC recommendation

Do not add a CUDA dependency or GPU-required route to the current RC. Record a
future optional-provider design only after the native CPU full engine has a
stable codec/backend interface: GPU capability discovery; explicit `--gpu`
policy that never silently changes format; pinned provider/driver/runtime;
bounded device workspace; deterministic chunk policy; CPU-compatible decoder
or explicitly stored GPU-only CIX backend ID; and transfer-inclusive focused
qualification. The consolidated first candidate is libcubwt acceleration of existing BWT,
with an isolated parity specification in PROBE-SPEC.md. Conventional-format
providers remain secondary candidates after their CPU format contracts are proved. No result here establishes that it will improve CIX compression
ratio or ordinary CLI throughput.

## Host-specific neural qualification boundary

The current [NNCP readme](https://bellard.org/nncp/readme.txt) names
Ampere/Ada/Hopper for CUDA and gives a 6.6 GB device-memory example. That path is
not qualified on this GTX 1650/4 GiB host. [LibNC](https://bellard.org/libnc/)
explicitly limits its cross-platform reproducibility statement to CPU execution.
A repeatable GPU run does not establish CPU/GPU or cross-GPU archive replay.
NNCP's MIT sources use a binary-distributed LibNC dependency, which requires a
separate source-only-package and platform disposition. Inspect generic model
options and account any model/training state; corpus-named reference presets
must not become CIX filename- or corpus-dependent runtime selection.
