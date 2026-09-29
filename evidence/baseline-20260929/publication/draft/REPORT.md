# CIX Compression Evidence Baseline — 2026-09-29 / review draft

**INCOMPLETE · NOT PUBLISHED · NOT A PERFORMANCE CLAIM**

Generated 2026-09-29T10:29:13.322594+00:00. Frozen CIX `f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6`; profile `high-compression-v1`.

## Executive summary

0 completed local comparison groups. NNLCB input qualification: 16/28 exact; full verified CIX coverage: 0/28. No subset aggregate replaces the required full universe.

Research portfolio scores are historical research evidence and do not replace these fresh frozen measurements.

## Methodology and measurement boundaries

[Frozen protocol](../../BENCHMARK-METHODOLOGY.md). Normal I/O and encoder internal verification are timed. Independent artifact-only decoding and source/restored SHA-256 equality are mandatory. CPU2 affinity, one configured worker, 48 GiB memory and 36-hour per-phase limits apply to every tool. Heavy R&D and preparation acquire the same exclusive compute lock. Normal inputs require three measured repetitions after a warm-up; inputs over 1 GiB initially use one full run. Reported normal timings are medians; every repetition and min/max/MAD remain in results.json. 1 GiB = 1,073,741,824 bytes; 1 MiB = 1,048,576 bytes.

## Hardware and environment

Environment snapshot: 2026-09-29T04:43:27.064517+00:00. Linux-6.8.0-138-generic-x86_64-with-glibc2.39. Intel NUC13RNGi9 / Core i9-13900K; 24 physical and 32 logical cores, approximately 62.3 GiB RAM; NVMe-backed filesystem. The benchmark is restricted to one logical performance-core CPU. The preparation snapshot is not a claim of an idle host during all later runs. Each phase records load, memory and disk state. Unrelated user services remain present. [Full environment manifest](../../manifests/environment-preparation.json).

## Compressor versions and settings

| Algorithm | Recorded version | Binary SHA-256 |
| --- | --- | --- |
| gzip | gzip 1.12 | afea077ce127d4fa9ad410d3066ba2b54dea19c0b44f04adf56c72d5f7b7a9bb |
| bzip2 | bzip2, a block-sorting file compressor.  Version 1.0.8, 13-Jul-2019. | 909769e6f36ab54e52f1099d59aec0e8d2f27b8c53f95c63429f5c571e027ada |
| zstd | *** Zstandard CLI (64-bit) v1.5.5, by Yann Collet *** | 7c5468b370f7c47eda07281e3437fafc568f95d10420051e3aa522709f9342c5 |
| xz | xz (XZ Utils) 5.4.5 | b5b163eb273291934556377ab883b4b2a5d4da50bd0dc0a91774ecc234ccd8d0 |
| brotli | brotli 1.2.0 | 06fd49887a76324b4bf7f9d2687ac1ad090ca43a7660c05a0c39289b123c071c |
| zpaq | zpaq v7.15 journaling archiver, compiled Sep 29 2026 | bf08e58895cd6cb9eb733cca767dbb66f8d051e2b764a9fc3a5df7bdd5b3f838 |
| paq8px | paq8px data compressor v215 (c) 2026, Matt Mahoney et al. | b982f1e8307d6c38e8febc6415901fafcc2e84a14d51e0af7c5cbbe6322778e7 |
| CIX | portfolio 25, commit f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6 | Seven native binaries and isolated Python environment; see manifests |

Exact options: gzip -9 -n; bzip2 -9; zstd --ultra -22 --long=27 -T1; xz -9e -T1; Brotli -q 11 -w 24; ZPAQ method 5 / threads 1; paq8px v215 -12L -simd AVX2; CIX default competitive_cli encode/decode. This report contains only the high-compression-v1 profile. [Binary manifest](../../manifests/compressor-binaries.json), [build manifest](../../manifests/cix-fresh-build.json).

## Silesia historical comparison

Canonical 12 files, independently compressed. Original total: 211,938,580 bytes. A complete total requires all 12 verified results. Summed per-file median times are explicitly aggregate times, not the median of a separate whole-corpus invocation. NNLCB D19 concatenation remains a separate issue.

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 12 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

## Entire English Wikipedia — 2026-09-01 pages/articles snapshot

Original XML: **117,231,826,047 bytes (109.180646 GiB)**. SHA-256 `a58e239df7dfb1589bbd96cb810a025bf7f6a63653f01ce1b62cbd935dc14842`. Wikimedia pages/articles content XML for English Wikipedia. Not full revision histories, media binaries or every administrative namespace. Every compressor receives the full identical decompressed XML stream. Source download bytes are not the benchmark input. [Acquisition and preparation](../../manifests/wikipedia-input.json).

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

No Wikipedia compression headline or improvement percentage exists until the corresponding verified measurements exist.

## CIX vs NNLCB — Independent Benchmark Compatibility

[NNLCB](https://fahaihi.github.io/NNLCB/) evaluates 28 datasets using 19 metrics. Source: Sun et al., [DOI 10.1007/s11704-024-40300-5](https://doi.org/10.1007/s11704-024-40300-5); upstream commit 91eeea5094a49bd1e60fa9ee4bf3a8e50891da63; retrieved 2026-09-29. This is our compatibility investigation, not independent validation of CIX by the NNLCB authors.

### View 1 — Published NNLCB reference measurements

Values below are preserved as reported, on the NNLCB platform: four Xeon Silver 4310 CPUs, 48 reported CPU cores, four RTX 4090 GPUs, 128 GB RAM and Ubuntu 20.04.6. The later server-memory upgrade is separately recorded by the source. Do not compare these times or memory values directly with local CIX timings.

| Algorithm | WavgCR | AvgCR | WavgSSP | AvgSSP | CRP | TotalCT h | TotalDT h | AvgCPM reported GB | AvgDPM reported GB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NNCP | 4.183 | 2.521 | 47.713 | 68.476 | 13.084 | 942.928 | 926.049 | 0.111 | 0.111 |
| PAC | 4.327 | 2.638 | 45.912 | 67.019 | 12.72 | 74.398 | 116.868 | 6.102 | 6.295 |
| TRACE | 4.411 | 2.718 | 44.867 | 66.032 | 12.486 | 69.128 | 131.11 | 6.106 | 6.449 |
| DZip | 4.494 | 2.516 | 43.819 | 68.545 | 14.272 | 332.787 | 148.374 | 10.113 | 4.79 |
| DZip* | 4.562 | 3.802 | 42.971 | 52.476 | 11.158 | 332.787 | 148.374 | 10.113 | 4.79 |
| Lstm-compress | 5.395 | 2.786 | 32.563 | 65.168 | 14.543 | 492.869 | 474.498 | 0.009 | 0.009 |
| DeepZip* | 16.835 | 7.045 | -110.434 | 11.933 | 18.504 | 250.714 | 52.449 | 13.708 | 4.292 |
| DeepZip | 16.865 | 5.76 | -110.811 | 28.003 | 24.092 | 250.714 | 52.449 | 13.708 | 4.292 |
| BSC | 4.826 | 2.928 | 39.677 | 63.394 | 13.045 | 0.353 | 0.3 | 0.121 | 0.116 |
| Lzma2 | 4.912 | 3.122 | 38.59 | 60.967 | 12.289 | 0.584 | 0.03 | 1.264 | 0.427 |
| XZ | 4.923 | 3.118 | 38.463 | 61.021 | 12.365 | 0.879 | 0.04 | 1.612 | 0.504 |
| PPMD | 4.96 | 3.025 | 38.001 | 62.181 | 12.934 | 0.893 | 0.953 | 0.226 | 0.225 |
| PBzip2 | 5.052 | 3.275 | 36.845 | 59.062 | 11.798 | 0.024 | 0.016 | 0.115 | 0.084 |
| Gzip | 5.351 | 3.862 | 33.113 | 51.728 | 10.342 | 0.451 | 0.026 | 0.002 | 0.002 |
| LZ4-multi | 5.618 | 4.28 | 29.77 | 46.501 | 9.656 | 0.064 | 0.009 | 0.116 | 0.025 |
| SnZip | 5.981 | 5.1 | 25.235 | 36.244 | 7.473 | 0.031 | 0.021 | 0.003 | 0.003 |

CR uses bits per original byte. Weighted values use compressed-byte weights. Published CRP differs from the paper equation by an inferred factor of sqrt(28) for 15/16 algorithms; Lstm-compress has additional inconsistent aggregates. Both authoritative tables are retained unchanged. [Source reconciliation](../../NNLCB-COMPATIBILITY-NOTES.md).

### View 2 — Controlled local measurements

All local algorithms use the same machine, byte streams, process limits and harness. CIX NNLCB aggregates: **Unavailable — full 28-dataset verified coverage is incomplete.**

The following per-dataset sections keep published reference rows separate from local rows. Published CS and resource units retain their original labels; CS numerically reconciles with binary MiB. Rounded published CS values are not exact compressed byte counts.

### D1 xml

Published expected bytes: 5,345,280. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 5,345,280; SHA-256: `0e82e54e695c1938e4193448022543845b33020c8be6bf3bf3ead2224903e08c`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 0.233 | 0.365 | 114.017 | 102.917 | 18776.344 | 18776.891 |
| X3 | 0.579 | 0.909 | 3.4 | 2.133 | 22.453 | 22.176 |
| NNCP | 0.449 | 0.705 | 34.95 | 35.2 | 114.145 | 113.785 |
| Lstm-compress | 0.455 | 0.713 | 14.867 | 15.533 | 7.199 | 7.199 |
| DeepZip | 0.308 | 0.484 | 8.3 | 1.533 | 1952.535 | 1650.543 |
| DeepZip* | 2.836 | 4.45 | 8.3 | 1.533 | 1952.535 | 1650.543 |
| DZip | 0.284 | 0.446 | 14.767 | 5.85 | 2910.949 | 2503.453 |
| DZip* | 2.812 | 4.413 | 14.767 | 5.85 | 2910.949 | 2503.453 |
| TRACE | 0.5 | 0.785 | 3.233 | 4.733 | 2356.668 | 2386.598 |
| PAC | 0.522 | 0.819 | 3.983 | 5.417 | 2387.141 | 2397.559 |
| GZip | 0.632 | 0.991 | 0.017 | 0.017 | 1.953 | 1.688 |
| PBzip2 | 0.418 | 0.656 | 0.017 | 0.017 | 45.313 | 6.902 |
| XZ | 0.415 | 0.65 | 0.05 | 0.017 | 114.277 | 12.848 |
| BSC | 0.363 | 0.57 | 0.017 | 0.017 | 28.84 | 30.887 |
| SnZip | 1.24 | 1.945 | 0.017 | 0.017 | 3.141 | 2.949 |
| Lzma2 | 0.434 | 0.68 | 0.033 | 0.017 | 72.598 | 10.652 |
| PPMD | 0.343 | 0.538 | 0.017 | 0.017 | 134.531 | 133.602 |
| LZ4-multi | 0.726 | 1.14 | 0.017 | 0.017 | 8.109 | 7.445 |

### D2 ooffice

Published expected bytes: 6,152,192. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 6,152,192; SHA-256: `e7ee013880d34dd5208283d0d3d91b07f442e067454276095ded14f322a656eb`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 1.165 | 1.589 | 144.683 | 142.95 | 19457.617 | 19457.723 |
| X3 | 2.888 | 3.938 | 14.617 | 10.95 | 105.781 | 106.059 |
| NNCP | 1.959 | 2.671 | 40.283 | 40.733 | 114.004 | 113.73 |
| Lstm-compress | 1.964 | 2.677 | 22.967 | 24.817 | 10.145 | 10.082 |
| DeepZip | 1.56 | 2.127 | 9.717 | 2.2 | 2011.762 | 1675.109 |
| DeepZip* | 5.392 | 7.351 | 9.717 | 2.2 | 2011.762 | 1675.109 |
| DZip | 1.575 | 2.148 | 17.533 | 7.783 | 2954.473 | 2510.242 |
| DZip* | 5.407 | 7.372 | 17.533 | 7.783 | 2954.473 | 2510.242 |
| TRACE | 2.222 | 3.029 | 4.067 | 5.95 | 2358.086 | 2397.297 |
| PAC | 2.022 | 2.757 | 5.0 | 6.8 | 2374.75 | 2401.742 |
| GZip | 2.947 | 4.019 | 0.017 | 0.017 | 1.875 | 1.863 |
| PBzip2 | 2.726 | 3.716 | 0.017 | 0.017 | 51.441 | 29.777 |
| XZ | 2.315 | 3.156 | 0.05 | 0.017 | 128.152 | 16.129 |
| BSC | 2.435 | 3.319 | 0.033 | 0.033 | 37.074 | 40.234 |
| SnZip | 4.092 | 5.58 | 0.017 | 0.017 | 3.23 | 3.152 |
| Lzma2 | 2.313 | 3.154 | 0.033 | 0.017 | 79.758 | 13.43 |
| PPMD | 2.381 | 3.245 | 0.033 | 0.033 | 134.969 | 134.219 |
| LZ4-multi | 3.374 | 4.6 | 0.017 | 0.017 | 10.984 | 10.68 |

### D3 reymont

Published expected bytes: 6,627,202. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 6,627,202; SHA-256: `0eac0114a3dfe6e2ee1f345a0f79d653cb26c3bc9f0ed79238af4933422b7578`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 0.674 | 0.853 | 150.567 | 151.417 | 19389.68 | 19389.762 |
| X3 | 1.245 | 1.576 | 2.333 | 1.083 | 27.992 | 27.938 |
| NNCP | 0.865 | 1.094 | 43.467 | 46.717 | 114.137 | 113.73 |
| Lstm-compress | 0.956 | 1.21 | 24.55 | 24.1 | 10.082 | 10.172 |
| DeepZip | 0.639 | 0.808 | 10.383 | 2.217 | 1988.621 | 1664.0 |
| DeepZip* | 4.47 | 5.658 | 10.383 | 2.217 | 1988.621 | 1664.0 |
| DZip | 0.625 | 0.791 | 18.567 | 7.767 | 2965.566 | 2523.012 |
| DZip* | 4.456 | 5.64 | 18.567 | 7.767 | 2965.566 | 2523.012 |
| TRACE | 0.938 | 1.187 | 4.1 | 5.967 | 2384.641 | 2398.012 |
| PAC | 0.96 | 1.215 | 4.817 | 6.95 | 2407.387 | 2408.152 |
| GZip | 1.736 | 2.198 | 0.033 | 0.017 | 1.914 | 1.84 |
| PBzip2 | 1.188 | 1.504 | 0.017 | 0.017 | 55.328 | 33.676 |
| XZ | 1.255 | 1.588 | 0.067 | 0.017 | 129.168 | 16.117 |
| BSC | 0.935 | 1.183 | 0.017 | 0.017 | 39.902 | 43.121 |
| SnZip | 3.057 | 3.869 | 0.017 | 0.017 | 3.156 | 3.152 |
| Lzma2 | 1.257 | 1.591 | 0.05 | 0.017 | 83.848 | 12.637 |
| PPMD | 1.005 | 1.272 | 0.017 | 0.033 | 134.969 | 134.141 |
| LZ4-multi | 1.971 | 2.494 | 0.017 | 0.017 | 10.602 | 9.973 |

### D4 sao

Published expected bytes: 7,251,944. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 7,251,944; SHA-256: `c2d0ea2cc59d4c21b7fe43a71499342a00cbe530a1d5548770e91ecd6214adcc`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 3.554 | 4.11 | 167.483 | 172.65 | 19411.43 | 19411.461 |
| X3 | 5.0 | 5.784 | 5.467 | 2.767 | 100.742 | 100.871 |
| NNCP | 3.645 | 4.216 | 50.55 | 46.817 | 114.09 | 113.828 |
| Lstm-compress | 3.769 | 4.359 | 26.35 | 26.717 | 10.168 | 10.141 |
| DeepZip | 3.522 | 4.074 | 11.6 | 2.7 | 2020.703 | 1676.785 |
| DeepZip* | 7.353 | 8.506 | 11.6 | 2.7 | 2020.703 | 1676.785 |
| DZip | 3.519 | 4.071 | 21.117 | 9.267 | 3024.68 | 2515.348 |
| DZip* | 7.35 | 8.503 | 21.117 | 9.267 | 3024.68 | 2515.348 |
| TRACE | 3.692 | 4.271 | 4.9 | 7.233 | 2378.813 | 2399.328 |
| PAC | 3.686 | 4.264 | 5.983 | 7.9 | 2383.949 | 2426.754 |
| GZip | 5.08 | 5.877 | 0.017 | 0.017 | 1.941 | 1.656 |
| PBzip2 | 4.713 | 5.452 | 0.017 | 0.017 | 60.984 | 40.992 |
| XZ | 4.221 | 4.882 | 0.067 | 0.017 | 140.465 | 20.324 |
| BSC | 4.459 | 5.158 | 0.033 | 0.033 | 43.094 | 46.367 |
| SnZip | 6.14 | 7.102 | 0.017 | 0.017 | 3.078 | 3.266 |
| Lzma2 | 4.209 | 4.869 | 0.033 | 0.017 | 89.227 | 16.246 |
| PPMD | 4.562 | 5.277 | 0.05 | 0.05 | 102.859 | 101.992 |
| LZ4-multi | 5.408 | 6.256 | 0.017 | 0.017 | 13.508 | 16.223 |

### D5 x-ray

Published expected bytes: 8,474,240. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 8,474,240; SHA-256: `7de9fce1405dc44ae5e6813ed21cd5751e761bd4265655a005d39b9685d1c9ad`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 3.343 | 3.308 | 185.117 | 195.783 | 18827.934 | 18827.828 |
| X3 | 4.348 | 4.304 | 8.017 | 5.05 | 59.176 | 59.07 |
| NNCP | 3.401 | 3.366 | 54.95 | 54.3 | 113.926 | 113.789 |
| Lstm-compress | 3.407 | 3.372 | 31.467 | 34.083 | 10.07 | 10.227 |
| DeepZip | 3.377 | 3.343 | 13.5 | 3.083 | 2053.957 | 1698.375 |
| DeepZip* | 7.208 | 7.135 | 13.5 | 3.083 | 2053.957 | 1698.375 |
| DZip | 3.359 | 3.326 | 24.55 | 10.8 | 3077.281 | 2545.047 |
| DZip* | 7.191 | 7.118 | 24.55 | 10.8 | 3077.281 | 2545.047 |
| TRACE | 3.467 | 3.432 | 5.733 | 8.267 | 2384.316 | 2411.211 |
| PAC | 3.492 | 3.456 | 7.067 | 8.917 | 2380.254 | 2430.973 |
| GZip | 5.758 | 5.7 | 0.017 | 0.017 | 1.945 | 1.699 |
| PBzip2 | 3.864 | 3.824 | 0.017 | 0.017 | 69.965 | 43.566 |
| XZ | 4.283 | 4.239 | 0.05 | 0.017 | 152.355 | 22.586 |
| BSC | 3.579 | 3.542 | 0.033 | 0.033 | 48.883 | 52.141 |
| SnZip | 8.067 | 7.985 | 0.017 | 0.017 | 3.223 | 2.98 |
| Lzma2 | 4.272 | 4.229 | 0.033 | 0.017 | 115.832 | 17.355 |
| PPMD | 3.673 | 3.635 | 0.05 | 0.05 | 123.859 | 122.844 |
| LZ4-multi | 6.848 | 6.778 | 0.017 | 0.017 | 16.301 | 20.172 |

### D6 mr

Published expected bytes: 9,970,564. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 9,970,564; SHA-256: `68637ed52e3e4860174ed2dc0840ac77d5f1a60abbcb13770d5754e3774d53e6`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 1.747 | 1.469 | 205.983 | 207.283 | 18661.742 | 18661.816 |
| X3 | 2.359 | 1.984 | 4.917 | 2.85 | 53.207 | 53.195 |
| NNCP | 1.877 | 1.579 | 63.867 | 63.783 | 114.066 | 113.816 |
| Lstm-compress | 1.876 | 1.578 | 36.35 | 35.75 | 10.191 | 10.191 |
| DeepZip | 1.692 | 1.424 | 15.667 | 3.417 | 2089.121 | 1712.102 |
| DeepZip* | 5.524 | 4.647 | 15.667 | 3.417 | 2089.121 | 1712.102 |
| DZip | 1.678 | 1.411 | 27.767 | 11.8 | 3193.102 | 2537.941 |
| DZip* | 5.509 | 4.635 | 27.767 | 11.8 | 3193.102 | 2537.941 |
| TRACE | 2.0 | 1.682 | 6.383 | 9.017 | 2400.691 | 2411.973 |
| PAC | 2.129 | 1.791 | 7.75 | 9.833 | 2381.5 | 2431.48 |
| GZip | 3.504 | 2.948 | 0.033 | 0.017 | 1.859 | 1.844 |
| PBzip2 | 2.343 | 1.971 | 0.017 | 0.017 | 64.012 | 39.199 |
| XZ | 2.624 | 2.208 | 0.117 | 0.017 | 157.828 | 23.574 |
| BSC | 2.1 | 1.767 | 0.033 | 0.017 | 45.715 | 46.375 |
| SnZip | 5.15 | 4.333 | 0.017 | 0.017 | 3.316 | 2.941 |
| Lzma2 | 2.621 | 2.205 | 0.05 | 0.017 | 128.418 | 17.141 |
| PPMD | 2.213 | 1.862 | 0.033 | 0.033 | 140.684 | 140.055 |
| LZ4-multi | 3.998 | 3.364 | 0.033 | 0.017 | 14.094 | 15.234 |

### D7 osdb

Published expected bytes: 10,085,684. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 10,085,684; SHA-256: `60f027179302ca3ad87c58ac90b6be72ec23588aaa7a3b7fe8ecc0f11def3fa3`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 1.871 | 1.555 | 235.883 | 233.017 | 19511.012 | 19510.824 |
| X3 | 3.34 | 2.778 | 6.983 | 3.583 | 51.48 | 51.457 |
| NNCP | 2.08 | 1.73 | 64.967 | 64.767 | 114.129 | 113.816 |
| Lstm-compress | 2.111 | 1.755 | 40.467 | 36.967 | 10.137 | 10.07 |
| DeepZip | 1.946 | 1.619 | 15.783 | 3.533 | 2062.762 | 1698.344 |
| DeepZip* | 5.777 | 4.805 | 15.783 | 3.533 | 2062.762 | 1698.344 |
| DZip | 1.931 | 1.606 | 28.267 | 12.083 | 3192.98 | 2547.828 |
| DZip* | 5.762 | 4.792 | 28.267 | 12.083 | 3192.98 | 2547.828 |
| TRACE | 2.043 | 1.699 | 6.283 | 8.9 | 2371.844 | 2431.012 |
| PAC | 2.146 | 1.785 | 7.033 | 9.883 | 2389.156 | 2435.777 |
| GZip | 3.544 | 2.948 | 0.017 | 0.017 | 1.773 | 1.84 |
| PBzip2 | 2.674 | 2.224 | 0.017 | 0.017 | 82.059 | 51.309 |
| XZ | 2.713 | 2.256 | 0.083 | 0.017 | 166.02 | 24.145 |
| BSC | 2.107 | 1.752 | 0.033 | 0.017 | 56.637 | 59.883 |
| SnZip | 5.079 | 4.224 | 0.017 | 0.017 | 3.086 | 3.133 |
| Lzma2 | 2.72 | 2.262 | 0.05 | 0.017 | 129.332 | 17.586 |
| PPMD | 2.274 | 1.891 | 0.033 | 0.033 | 202.895 | 201.977 |
| LZ4-multi | 3.774 | 3.139 | 0.017 | 0.017 | 13.82 | 15.078 |

### D8 dickens

Published expected bytes: 10,192,446. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 10,192,446; SHA-256: `b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 1.767 | 1.453 | 213.05 | 203.083 | 18689.773 | 18689.563 |
| X3 | 2.658 | 2.188 | 6.05 | 3.35 | 42.598 | 42.656 |
| NNCP | 2.28 | 1.876 | 65.5 | 65.7 | 114.063 | 113.855 |
| Lstm-compress | 2.334 | 1.92 | 28.183 | 28.65 | 7.18 | 7.184 |
| DeepZip | 1.91 | 1.572 | 15.867 | 3.05 | 2069.387 | 1693.898 |
| DeepZip* | 4.42 | 3.637 | 15.867 | 3.05 | 2069.387 | 1693.898 |
| DZip | 1.894 | 1.559 | 28.883 | 11.317 | 3190.648 | 2550.816 |
| DZip* | 4.404 | 3.624 | 28.883 | 11.317 | 3190.648 | 2550.816 |
| TRACE | 2.432 | 2.002 | 6.467 | 9.1 | 2384.418 | 2426.105 |
| PAC | 2.363 | 1.945 | 6.967 | 10.083 | 2387.855 | 2452.203 |
| GZip | 3.673 | 3.023 | 0.033 | 0.017 | 2.031 | 1.77 |
| PBzip2 | 2.669 | 2.196 | 0.017 | 0.017 | 83.395 | 51.625 |
| XZ | 2.7 | 2.222 | 0.1 | 0.017 | 154.422 | 24.34 |
| BSC | 2.15 | 1.769 | 0.033 | 0.017 | 56.703 | 59.898 |
| SnZip | 5.96 | 4.906 | 0.017 | 0.017 | 3.152 | 2.965 |
| Lzma2 | 2.7 | 2.222 | 0.067 | 0.017 | 130.445 | 17.613 |
| PPMD | 2.175 | 1.789 | 0.05 | 0.05 | 246.914 | 245.766 |
| LZ4-multi | 4.182 | 3.442 | 0.017 | 0.017 | 14.332 | 14.613 |

### D9 samba

Published expected bytes: 21,606,400. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 21,606,400; SHA-256: `93ba07bc44d8267789c1d911992f40b089ffa2140b4a160fac11ccae9a40e7b2`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 2.392 | 0.928 | 495.65 | 484.983 | 20330.203 | 20335.969 |
| X3 | 5.195 | 2.017 | 89.2 | 57.417 | 163.855 | 163.898 |
| NNCP | 3.837 | 1.489 | 137.733 | 137.7 | 113.988 | 113.848 |
| Lstm-compress | 4.09 | 1.587 | 80.033 | 77.4 | 10.141 | 10.168 |
| DeepZip | 3.457 | 1.342 | 34.05 | 7.333 | 2329.758 | 1809.188 |
| DeepZip* | 7.289 | 2.83 | 34.05 | 7.333 | 2329.758 | 1809.188 |
| DZip | 3.254 | 1.264 | 59.733 | 26.333 | 3912.141 | 2657.793 |
| DZip* | 7.086 | 2.751 | 59.733 | 26.333 | 3912.141 | 2657.793 |
| TRACE | 4.539 | 1.762 | 13.417 | 18.883 | 2385.129 | 2513.098 |
| PAC | 3.969 | 1.541 | 14.467 | 21.167 | 2395.48 | 2537.496 |
| GZip | 5.158 | 2.002 | 0.033 | 0.017 | 1.871 | 1.762 |
| PBzip2 | 4.363 | 1.693 | 0.017 | 0.017 | 117.348 | 63.711 |
| XZ | 3.566 | 1.384 | 0.183 | 0.017 | 276.871 | 46.797 |
| BSC | 3.71 | 1.44 | 0.033 | 0.033 | 98.781 | 98.93 |
| SnZip | 7.645 | 2.968 | 0.017 | 0.017 | 3.219 | 3.109 |
| Lzma2 | 3.586 | 1.392 | 0.083 | 0.017 | 260.414 | 29.402 |
| PPMD | 3.639 | 1.412 | 0.05 | 0.067 | 263.074 | 262.262 |
| LZ4-multi | 5.825 | 2.262 | 0.033 | 0.017 | 27.215 | 20.438 |

### D10 nci

Published expected bytes: 33,553,445. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 33,553,445; SHA-256: `fc63a31770947b8c2062d3b19ca94c00485a232bb91b502021948fee983e1635`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 0.757 | 0.189 | 545.95 | 536.733 | 18470.406 | 18470.246 |
| X3 | 1.865 | 0.466 | 5.883 | 3.233 | 53.367 | 53.402 |
| NNCP | 1.142 | 0.285 | 214.133 | 215.333 | 114.082 | 113.82 |
| Lstm-compress | 1.46 | 0.364 | 88.517 | 88.4 | 6.59 | 6.633 |
| DeepZip | 1.077 | 0.269 | 51.633 | 8.533 | 2608.441 | 1949.051 |
| DeepZip* | 3.417 | 0.854 | 51.633 | 8.533 | 2608.441 | 1949.051 |
| DZip | 1.054 | 0.264 | 90.3 | 34.667 | 4655.477 | 2737.832 |
| DZip* | 3.394 | 0.849 | 90.3 | 34.667 | 4655.477 | 2737.832 |
| TRACE | 1.444 | 0.361 | 18.683 | 27.717 | 2373.801 | 2596.508 |
| PAC | 1.387 | 0.347 | 21.517 | 31.233 | 2379.309 | 2593.41 |
| GZip | 2.849 | 0.712 | 0.05 | 0.017 | 1.855 | 1.691 |
| PBzip2 | 1.766 | 0.441 | 0.017 | 0.017 | 130.473 | 78.91 |
| XZ | 1.382 | 0.345 | 0.367 | 0.017 | 342.055 | 67.684 |
| BSC | 1.191 | 0.297 | 0.033 | 0.017 | 121.48 | 121.688 |
| SnZip | 5.841 | 1.46 | 0.017 | 0.017 | 3.285 | 3.063 |
| Lzma2 | 1.661 | 0.415 | 0.133 | 0.017 | 362.805 | 38.707 |
| PPMD | 1.416 | 0.353 | 0.033 | 0.05 | 263.176 | 262.293 |
| LZ4-multi | 3.46 | 0.865 | 0.017 | 0.017 | 38.273 | 17.145 |

### D11 webster

Published expected bytes: 41,458,703. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 41,458,703; SHA-256: `6a68f69b26daf09f9dd84f7470368553194a0b294fcfa80f1604efb11143a383`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 4.108 | 0.831 | 818.417 | 826.367 | 19809.23 | 19809.277 |
| X3 | 8.092 | 1.637 | 143.267 | 98.583 | 177.207 | 176.703 |
| NNCP | 5.677 | 1.148 | 291.85 | 296.6 | 113.91 | 113.82 |
| Lstm-compress | 6.1 | 1.234 | 114.05 | 115.617 | 7.23 | 7.277 |
| DeepZip | 4.955 | 1.003 | 63.55 | 11.833 | 2798.066 | 2009.777 |
| DeepZip* | 7.456 | 1.509 | 63.55 | 11.833 | 2798.066 | 2009.777 |
| DZip | 4.799 | 0.971 | 112.133 | 44.75 | 5139.852 | 2864.516 |
| DZip* | 7.3 | 1.477 | 112.133 | 44.75 | 5139.852 | 2864.516 |
| TRACE | 6.573 | 1.33 | 24.667 | 35.767 | 2373.516 | 2671.699 |
| PAC | 5.908 | 1.195 | 28.533 | 39.767 | 2362.906 | 2659.699 |
| GZip | 11.503 | 2.327 | 0.067 | 0.017 | 1.754 | 1.898 |
| PBzip2 | 8.248 | 1.668 | 0.017 | 0.017 | 132.527 | 87.598 |
| XZ | 7.981 | 1.614 | 0.467 | 0.017 | 466.852 | 89.082 |
| BSC | 6.337 | 1.282 | 0.067 | 0.033 | 133.305 | 136.543 |
| SnZip | 19.062 | 3.857 | 0.017 | 0.017 | 3.309 | 3.117 |
| Lzma2 | 8.0 | 1.618 | 0.267 | 0.017 | 430.871 | 52.746 |
| PPMD | 6.621 | 1.339 | 0.117 | 0.133 | 262.93 | 262.141 |
| LZ4-multi | 13.209 | 2.673 | 0.017 | 0.017 | 52.863 | 28.012 |

### D12 mozilla

Published expected bytes: 51,220,480. Compatibility: **EXACT**. Named unmodified member of the canonical Silesia zip linked by NNLCB; extracted bytes reverified against preserved source zip and original canonical manifest.

Exact local input bytes: 51,220,480; SHA-256: `657fc3764b0c75ac9de9623125705831ebbfbe08fed248df73bc2dc66e2a963b`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 8.394 | 1.374 | 1188.833 | 1219.567 | 21832.168 | 21832.012 |
| X3 | 18.264 | 2.991 | 1315.317 | 1135.65 | 697.516 | 707.898 |
| NNCP | 10.6 | 1.735 | 361.067 | 339.567 | 114.039 | 113.793 |
| Lstm-compress | 12.416 | 2.033 | 183.783 | 180.867 | 10.168 | 10.191 |
| DeepZip | 10.092 | 1.653 | 80.217 | 17.867 | 3029.996 | 2121.691 |
| DeepZip* | 13.923 | 2.28 | 80.217 | 17.867 | 3029.996 | 2121.691 |
| DZip | 10.271 | 1.682 | 142.533 | 61.15 | 5725.219 | 2971.93 |
| DZip* | 14.102 | 2.31 | 142.533 | 61.15 | 5725.219 | 2971.93 |
| TRACE | 12.292 | 2.013 | 32.367 | 47.017 | 2402.551 | 2711.332 |
| PAC | 11.156 | 1.827 | 36.617 | 50.483 | 2395.727 | 2732.488 |
| GZip | 18.114 | 2.967 | 0.167 | 0.017 | 1.828 | 1.664 |
| PBzip2 | 17.066 | 2.794 | 0.017 | 0.017 | 132.715 | 89.582 |
| XZ | 12.757 | 2.089 | 0.4 | 0.033 | 568.453 | 112.77 |
| BSC | 15.219 | 2.492 | 0.083 | 0.083 | 152.141 | 131.668 |
| SnZip | 25.342 | 4.15 | 0.017 | 0.017 | 3.113 | 2.984 |
| Lzma2 | 12.726 | 2.084 | 0.2 | 0.017 | 514.559 | 66.824 |
| PPMD | 15.175 | 2.485 | 0.15 | 0.167 | 263.105 | 262.336 |
| LZ4-multi | 21.015 | 3.442 | 0.05 | 0.017 | 66.531 | 31.414 |

### D13 enwik8

Published expected bytes: 100,000,000. Compatibility: **EXACT**. Unmodified named canonical ZIP member from the exact NNLCB URL.

Exact local input bytes: 100,000,000; SHA-256: `2b49720ec4d78c3c9fabaee6e4179a5e997302b3a70029f30f2d582218c024a8`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 14.644 | 1.228 | 2026.433 | 2021.233 | 22081.254 | 22081.25 |
| X3 | 25.654 | 2.152 | 2260.9 | 1562.167 | 575.801 | 575.262 |
| NNCP | 19.909 | 1.67 | 564.583 | 558.9 | 113.977 | 113.758 |
| Lstm-compress | 22.097 | 1.854 | 344.95 | 326.8 | 9.238 | 9.168 |
| DeepZip | 19.686 | 1.651 | 155.767 | 33.633 | 4112.68 | 2582.793 |
| DeepZip* | 23.264 | 1.952 | 155.767 | 33.633 | 4112.68 | 2582.793 |
| DZip | 18.774 | 1.575 | 210.3 | 84.467 | 4114.426 | 2830.438 |
| DZip* | 22.353 | 1.875 | 210.3 | 84.467 | 4114.426 | 2830.438 |
| TRACE | 22.292 | 1.87 | 41.217 | 89.783 | 1981.125 | 2522.043 |
| PAC | 20.21 | 1.695 | 51.567 | 89.45 | 1970.391 | 2495.047 |
| GZip | 34.757 | 2.916 | 0.133 | 0.017 | 1.863 | 1.66 |
| PBzip2 | 27.671 | 2.321 | 0.017 | 0.017 | 138.285 | 95.387 |
| XZ | 23.681 | 1.986 | 1.3 | 0.033 | 793.68 | 185.293 |
| BSC | 21.257 | 1.783 | 0.15 | 0.117 | 164.598 | 157.68 |
| SnZip | 53.351 | 4.475 | 0.033 | 0.033 | 3.086 | 3.133 |
| Lzma2 | 23.711 | 1.988 | 0.85 | 0.017 | 682.023 | 124.434 |
| PPMD | 22.099 | 1.853 | 0.35 | 0.367 | 263.18 | 262.348 |
| LZ4-multi | 40.043 | 3.359 | 0.033 | 0.017 | 97.676 | 31.473 |

### D14 text8

Published expected bytes: 100,000,000. Compatibility: **EXACT**. Unmodified named canonical ZIP member from the exact NNLCB URL.

Exact local input bytes: 100,000,000; SHA-256: `6e890197040d37d85beb962ae1f041ff1d9a9ca8d20c7d99c85027eebf51dca7`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 15.597 | 1.308 | 1705.917 | 1701.033 | 20580.504 | 20580.387 |
| NNCP | 19.734 | 1.655 | 885.683 | 819.917 | 113.988 | 113.594 |
| Lstm-compress | 20.936 | 1.756 | 237.233 | 235.067 | 5.867 | 6.023 |
| DeepZip | 19.349 | 1.623 | 286.967 | 22.983 | 7167.992 | 1701.27 |
| DeepZip* | 21.532 | 1.806 | 286.967 | 22.983 | 7167.992 | 1701.27 |
| DZip | 18.763 | 1.574 | 344.75 | 91.6 | 7136.996 | 1994.465 |
| DZip* | 20.947 | 1.757 | 344.75 | 91.6 | 7136.996 | 1994.465 |
| TRACE | 21.239 | 1.782 | 40.183 | 73.167 | 1967.715 | 2554.129 |
| PAC | 19.379 | 1.626 | 50.717 | 85.633 | 1970.352 | 2495.0 |
| GZip | 31.517 | 2.644 | 0.167 | 0.017 | 1.758 | 1.656 |
| PBzip2 | 25.178 | 2.112 | 0.033 | 0.017 | 137.379 | 106.25 |
| XZ | 22.145 | 1.858 | 1.85 | 0.033 | 748.543 | 183.594 |
| BSC | 19.868 | 1.667 | 0.217 | 0.15 | 165.719 | 158.387 |
| SnZip | 51.297 | 4.303 | 0.033 | 0.033 | 3.102 | 2.961 |
| Lzma2 | 22.149 | 1.858 | 1.583 | 0.033 | 682.176 | 123.07 |
| PPMD | 20.42 | 1.713 | 0.467 | 0.483 | 263.395 | 262.375 |
| LZ4-multi | 37.157 | 3.117 | 0.033 | 0.017 | 95.27 | 31.055 |

### D15 MNIST

Published expected bytes: 54,880,032. Compatibility: **NOT EXACTLY REPRODUCED**. Canonical MNIST train/test image streams acquired via CVDF mirror after original URLs returned404. Combined header-inclusive length matches54880032, but NNLCB does not specify concatenation order.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| Cmix | 5.361 | 0.819 | 1000.65 | 999.967 | 20360.113 | 20360.168 |
| X3 | 8.946 | 1.367 | 189.333 | 125.183 | 309.422 | 310.305 |
| NNCP | 5.625 | 0.859 | 376.5 | 372.483 | 114.035 | 113.801 |
| Lstm-compress | 7.17 | 1.096 | 198.8 | 210.667 | 10.176 | 10.125 |
| DeepZip | 5.086 | 0.777 | 149.3 | 17.783 | 4380.559 | 1268.566 |
| DeepZip* | 8.917 | 1.363 | 149.3 | 17.783 | 4380.559 | 1268.566 |
| DZip | 5.075 | 0.776 | 217.8 | 90.583 | 4368.668 | 1562.145 |
| DZip* | 8.906 | 1.361 | 217.8 | 90.583 | 4368.668 | 1562.145 |
| TRACE | 6.251 | 0.955 | 33.733 | 52.183 | 1350.297 | 1824.648 |
| PAC | 7.239 | 1.106 | 26.033 | 44.3 | 1275.289 | 1747.582 |
| GZip | 10.811 | 1.652 | 0.333 | 0.017 | 1.895 | 1.867 |
| PBzip2 | 9.58 | 1.464 | 0.017 | 0.017 | 68.574 | 55.383 |
| XZ | 8.658 | 1.323 | 1.083 | 0.017 | 599.273 | 115.633 |
| BSC | 7.959 | 1.217 | 0.067 | 0.067 | 127.477 | 111.199 |
| SnZip | 15.626 | 2.388 | 0.017 | 0.017 | 3.07 | 3.164 |
| Lzma2 | 8.785 | 1.343 | 0.333 | 0.017 | 545.938 | 66.285 |
| PPMD | 8.563 | 1.309 | 0.2 | 0.2 | 263.203 | 262.367 |
| LZ4-multi | 11.989 | 1.832 | 0.2 | 0.017 | 68.129 | 26.84 |

### D16 CIFAR-10

Published expected bytes: 186,213,868. Compatibility: **NOT EXACTLY REPRODUCED**. Official Python archive acquired and hashed. Its six data/test pickle batches total186213868 bytes (matching NNLCB); readme and batches.meta add246 bytes. Physical archive order differs from lexical/numeric batch order, and NNLCB does not specify concatenation.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| X3 | 134.085 | 6.04 | 2228.7 | 1467.433 | 1237.391 | 1237.711 |
| NNCP | 105.12 | 4.735 | 1231.917 | 1186.133 | 114.125 | 113.629 |
| Lstm-compress | 123.055 | 5.543 | 708.683 | 728.567 | 9.969 | 10.164 |
| DeepZip | 442.122 | 19.917 | 585.683 | 98.183 | 12398.508 | 2522.895 |
| DeepZip* | 445.953 | 20.089 | 585.683 | 98.183 | 12398.508 | 2522.895 |
| DZip | 112.007 | 5.046 | 847.7 | 328.767 | 12400.902 | 2816.492 |
| DZip* | 115.838 | 5.218 | 847.7 | 328.767 | 12400.902 | 2816.492 |
| TRACE | 114.929 | 5.177 | 124.533 | 191.35 | 3365.84 | 3950.434 |
| PAC | 99.209 | 4.469 | 103.117 | 167.433 | 3366.324 | 3887.234 |
| GZip | 162.547 | 7.322 | 0.167 | 0.033 | 1.852 | 1.773 |
| PBzip2 | 140.276 | 6.319 | 0.033 | 0.033 | 152.461 | 115.441 |
| XZ | 133.348 | 6.007 | 2.417 | 0.233 | 986.711 | 377.348 |
| BSC | 127.966 | 5.765 | 0.783 | 0.817 | 164.313 | 157.621 |
| SnZip | 176.024 | 7.93 | 0.017 | 0.017 | 3.172 | 2.984 |
| Lzma2 | 133.627 | 6.02 | 1.15 | 0.117 | 685.051 | 318.336 |
| PPMD | 131.2 | 5.91 | 1.7 | 1.833 | 263.199 | 262.371 |
| LZ4-multi | 168.49 | 7.59 | 0.033 | 0.017 | 173.766 | 33.363 |

### D17 ImageNet

Published expected bytes: 745,823,247. Compatibility: **NOT EXACTLY REPRODUCED**. Official task3 archive acquired. It contains120 nested class TARs; NNLCB does not give nested-member concatenation order or an exact prepared-file hash.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 600.826 | 6.757 | 4210.15 | 4197.933 | 113.992 | 113.848 |
| Lstm-compress | 616.534 | 6.934 | 2877.867 | 2790.967 | 10.141 | 10.297 |
| DeepZip | 2044.115 | 22.991 | 1413.417 | 412.217 | 18915.352 | 8742.391 |
| DeepZip* | 2047.946 | 23.034 | 1413.417 | 412.217 | 18915.352 | 8742.391 |
| DZip | 672.153 | 7.56 | 1709.917 | 852.617 | 18912.719 | 8974.816 |
| DZip* | 675.984 | 7.603 | 1709.917 | 852.617 | 18912.719 | 8974.816 |
| TRACE | 640.493 | 7.204 | 344.767 | 713.317 | 12451.441 | 12995.129 |
| PAC | 618.911 | 6.961 | 441.067 | 671.167 | 12441.035 | 12958.43 |
| GZip | 702.067 | 7.896 | 0.55 | 0.117 | 1.945 | 1.844 |
| PBzip2 | 696.059 | 7.828 | 0.117 | 0.083 | 161.84 | 120.848 |
| XZ | 695.042 | 7.817 | 2.183 | 0.283 | 4100.766 | 1511.156 |
| BSC | 672.743 | 7.566 | 2.583 | 2.617 | 163.863 | 159.633 |
| SnZip | 711.19 | 7.999 | 0.017 | 0.017 | 3.172 | 3.105 |
| Lzma2 | 694.413 | 7.81 | 0.667 | 0.167 | 3154.934 | 1422.199 |
| PPMD | 682.264 | 7.673 | 8.083 | 8.167 | 263.41 | 262.41 |
| LZ4-multi | 701.494 | 7.89 | 0.067 | 0.017 | 257.613 | 33.832 |

### D18 ImageTest

Published expected bytes: 470,611,702. Compatibility: **NOT EXACTLY REPRODUCED**. Official rgb8bit archive acquired:14 PPM files total470611702 bytes (matching expected), plus2038 bytes documentation. Concatenation order and boundaries are unspecified.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 183.402 | 3.269 | 3724.267 | 3214.55 | 113.992 | 113.625 |
| Lstm-compress | 405.339 | 7.225 | 2007.267 | 1867.217 | 10.066 | 9.977 |
| DeepZip | 1133.47 | 20.204 | 815.367 | 216.483 | 30179.367 | 5235.492 |
| DeepZip* | 1137.302 | 20.272 | 815.367 | 216.483 | 30179.367 | 5235.492 |
| DZip | 197.831 | 3.526 | 1012.05 | 475.867 | 8871.203 | 5527.633 |
| DZip* | 201.663 | 3.595 | 1012.05 | 475.867 | 8871.203 | 5527.633 |
| TRACE | 196.117 | 3.496 | 201.0 | 363.017 | 7970.629 | 8564.5 |
| PAC | 188.614 | 3.362 | 224.75 | 373.55 | 7970.477 | 8493.777 |
| GZip | 330.164 | 5.885 | 0.5 | 0.1 | 1.809 | 1.867 |
| PBzip2 | 260.493 | 4.643 | 0.083 | 0.05 | 152.891 | 138.977 |
| XZ | 268.436 | 4.785 | 3.067 | 0.2 | 2707.406 | 874.066 |
| BSC | 228.71 | 4.077 | 1.567 | 1.45 | 167.207 | 158.43 |
| SnZip | 410.976 | 7.326 | 0.05 | 0.033 | 3.113 | 3.109 |
| Lzma2 | 268.524 | 4.786 | 1.95 | 0.183 | 1884.727 | 727.109 |
| PPMD | 248.956 | 4.438 | 3.333 | 3.6 | 263.426 | 262.195 |
| LZ4-multi | 373.514 | 6.658 | 0.117 | 0.017 | 460.441 | 33.605 |

### D19 Silesia

Published expected bytes: 211,938,580. Compatibility: **NOT EXACTLY REPRODUCED**. All12 canonical members verified individually. Their summed length matches211938580, but NNLCB D19 container/concatenation order is unspecified.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 38.79 | 1.535 | 1325.033 | 1233.3 | 114.098 | 113.793 |
| Lstm-compress | 44.862 | 1.776 | 912.033 | 773.6 | 10.141 | 10.199 |
| DeepZip | 43.409 | 1.718 | 336.583 | 73.95 | 6691.273 | 3644.801 |
| DeepZip* | 47.24 | 1.87 | 336.583 | 73.95 | 6691.273 | 3644.801 |
| DZip | 39.529 | 1.565 | 472.85 | 228.783 | 6680.633 | 3869.578 |
| DZip* | 43.36 | 1.716 | 472.85 | 228.783 | 6680.633 | 3869.578 |
| TRACE | 44.749 | 1.771 | 83.317 | 172.833 | 3796.121 | 4336.215 |
| PAC | 40.525 | 1.604 | 108.917 | 190.683 | 3785.918 | 4301.777 |
| GZip | 64.517 | 2.554 | 0.4 | 0.033 | 1.957 | 1.875 |
| PBzip2 | 52.12 | 2.063 | 0.05 | 0.017 | 142.414 | 120.184 |
| XZ | 46.174 | 1.828 | 2.5 | 0.083 | 1079.629 | 320.328 |
| BSC | 45.155 | 1.787 | 0.4 | 0.317 | 165.656 | 157.305 |
| SnZip | 96.736 | 3.829 | 0.05 | 0.033 | 3.223 | 3.164 |
| Lzma2 | 46.455 | 1.839 | 1.217 | 0.05 | 684.805 | 254.59 |
| PPMD | 45.882 | 1.816 | 0.75 | 0.85 | 263.434 | 262.297 |
| LZ4-multi | 73.797 | 2.921 | 0.067 | 0.017 | 115.992 | 33.125 |

### D20 Backup

Published expected bytes: 1,000,000,000. Compatibility: **EXACT**. Unmodified named backup_1GB member already prepared in the exact TRACE archive linked by NNLCB. Its1000000000 bytes match the definition; no new random extraction or concatenation was performed.

Exact local input bytes: 1,000,000,000; SHA-256: `ca3c53465568b36c6b160fe9adfea51cc72f7f81b0c8d38a1961e579175dab63`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 474.456 | 3.98 | 5675.417 | 6593.967 | 113.965 | 113.785 |
| Lstm-compress | 533.427 | 4.475 | 3728.55 | 3807.933 | 10.027 | 10.074 |
| DeepZip | 513.489 | 4.307 | 1621.7 | 390.233 | 24736.355 | 11139.488 |
| DeepZip* | 517.32 | 4.34 | 1621.7 | 390.233 | 24736.355 | 11139.488 |
| DZip | 501.159 | 4.204 | 2236.983 | 1171.433 | 24709.68 | 11394.277 |
| DZip* | 504.99 | 4.236 | 2236.983 | 1171.433 | 24709.68 | 11394.277 |
| TRACE | 542.016 | 4.547 | 455.667 | 1108.517 | 16573.621 | 16829.383 |
| PAC | 500.732 | 4.2 | 546.6 | 863.167 | 16561.676 | 17079.383 |
| GZip | 743.469 | 6.237 | 0.983 | 0.183 | 1.965 | 1.73 |
| PBzip2 | 712.635 | 5.978 | 0.133 | 0.083 | 167.5 | 142.363 |
| XZ | 605.515 | 5.079 | 2.533 | 0.25 | 4927.27 | 1683.922 |
| BSC | 642.982 | 5.393 | 2.983 | 2.75 | 165.586 | 161.633 |
| SnZip | 846.365 | 7.1 | 0.1 | 0.05 | 3.277 | 2.98 |
| Lzma2 | 606.015 | 5.083 | 1.133 | 0.167 | 3890.695 | 1575.25 |
| PPMD | 680.304 | 5.706 | 6.867 | 6.15 | 263.168 | 262.273 |
| LZ4-multi | 793.085 | 6.653 | 0.117 | 0.033 | 280.258 | 37.563 |

### D21 enwik9

Published expected bytes: 1,000,000,000. Compatibility: **EXACT**. Unmodified named canonical ZIP member from the exact NNLCB URL.

Exact local input bytes: 1,000,000,000; SHA-256: `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 156.585 | 1.313 | 6135.417 | 6135.75 | 113.949 | 113.859 |
| Lstm-compress | 187.254 | 1.571 | 3630.217 | 3577.133 | 9.211 | 9.063 |
| DeepZip | 2145.443 | 17.997 | 1738.067 | 494.533 | 24729.777 | 11157.547 |
| DeepZip* | 2149.027 | 18.027 | 1738.067 | 494.533 | 24729.777 | 11157.547 |
| DZip | 179.926 | 1.509 | 2108.517 | 963.683 | 24722.07 | 11396.805 |
| DZip* | 183.51 | 1.539 | 2108.517 | 963.683 | 24722.07 | 11396.805 |
| TRACE | 185.476 | 1.556 | 634.783 | 1039.2 | 16570.969 | 17112.047 |
| PAC | 164.17 | 1.377 | 444.583 | 782.433 | 16561.211 | 17084.098 |
| GZip | 307.648 | 2.581 | 1.05 | 0.15 | 1.805 | 1.871 |
| PBzip2 | 242.298 | 2.032 | 0.117 | 0.067 | 141.875 | 106.531 |
| XZ | 204.234 | 1.713 | 3.933 | 0.083 | 4525.984 | 1412.191 |
| BSC | 184.895 | 1.551 | 1.467 | 1.017 | 164.766 | 157.652 |
| SnZip | 479.171 | 4.02 | 0.3 | 0.15 | 3.129 | 3.211 |
| Lzma2 | 204.84 | 1.718 | 2.867 | 0.067 | 3489.426 | 1167.371 |
| PPMD | 191.069 | 1.602 | 3.633 | 4.1 | 263.297 | 262.418 |
| LZ4-multi | 355.19 | 2.98 | 0.167 | 0.033 | 182.148 | 31.461 |

### D22 Book

Published expected bytes: 1,000,000,000. Compatibility: **NOT EXACTLY REPRODUCED**. Official BookCorpus archive has two text members totalling4613316478 bytes, in archive order books_large_p2 then books_large_p1. Which concatenation/prefix produced NNLCB first1000000000 bytes is unspecified.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 179.739 | 1.507 | 6001.867 | 5890.1 | 114.047 | 113.719 |
| Lstm-compress | 203.182 | 1.704 | 3583.2 | 3551.483 | 9.113 | 9.008 |
| DeepZip | 196.844 | 1.651 | 1605.15 | 343.817 | 24721.637 | 11140.012 |
| DeepZip* | 200.407 | 1.681 | 1605.15 | 343.817 | 24721.637 | 11140.012 |
| DZip | 186.101 | 1.561 | 2152.317 | 1073.75 | 24713.102 | 11390.449 |
| DZip* | 189.665 | 1.591 | 2152.317 | 1073.75 | 24713.102 | 11390.449 |
| TRACE | 212.338 | 1.781 | 422.15 | 889.383 | 16572.598 | 17118.887 |
| PAC | 189.54 | 1.59 | 491.05 | 787.517 | 16562.176 | 17075.449 |
| GZip | 342.778 | 2.875 | 1.683 | 0.15 | 1.863 | 1.902 |
| PBzip2 | 255.441 | 2.142 | 0.117 | 0.067 | 141.996 | 105.223 |
| XZ | 242.129 | 2.031 | 4.867 | 0.067 | 4563.594 | 1456.449 |
| BSC | 208.133 | 1.745 | 1.567 | 1.117 | 166.797 | 158.359 |
| SnZip | 557.717 | 4.678 | 0.333 | 0.183 | 3.203 | 3.09 |
| Lzma2 | 241.677 | 2.027 | 3.717 | 0.067 | 3525.965 | 1205.047 |
| PPMD | 214.733 | 1.801 | 5.15 | 6.483 | 263.109 | 262.383 |
| LZ4-multi | 388.988 | 3.263 | 0.217 | 0.033 | 173.086 | 31.516 |

### D23 ESC

Published expected bytes: 220,522,000. Compatibility: **NOT EXACTLY REPRODUCED**. Official pinned ESC50 source acquired. Any500 WAV files have the listed total220522000 bytes; NNLCB does not specify which ordering selects the first500.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| X3 | 145.056 | 5.518 | 1430.383 | 674.7 | 1237.141 | 1237.035 |
| NNCP | 95.072 | 3.616 | 1410.017 | 1459.417 | 114.051 | 113.828 |
| Lstm-compress | 100.502 | 3.823 | 826.6 | 789.633 | 10.332 | 10.363 |
| DeepZip | 89.544 | 3.406 | 356.483 | 79.533 | 6867.934 | 3697.969 |
| DeepZip* | 93.375 | 3.552 | 356.483 | 79.533 | 6867.934 | 3697.969 |
| DZip | 89.188 | 3.393 | 634.2 | 294.6 | 6879.902 | 3954.262 |
| DZip* | 93.02 | 3.538 | 634.2 | 294.6 | 6879.902 | 3954.262 |
| TRACE | 103.291 | 3.929 | 93.933 | 197.567 | 3935.559 | 4476.988 |
| PAC | 110.43 | 4.201 | 112.15 | 0.05 | 3924.051 | 372.973 |
| GZip | 156.003 | 5.934 | 0.217 | 0.05 | 1.746 | 1.773 |
| PBzip2 | 133.081 | 5.062 | 0.05 | 0.033 | 150.148 | 134.223 |
| XZ | 135.54 | 5.155 | 1.883 | 0.15 | 1250.883 | 418.043 |
| BSC | 125.951 | 4.791 | 0.583 | 0.533 | 160.953 | 152.785 |
| SnZip | 185.278 | 7.048 | 0.017 | 0.017 | 3.113 | 3.211 |
| Lzma2 | 135.099 | 5.139 | 0.833 | 0.117 | 685.141 | 352.543 |
| PPMD | 130.039 | 4.946 | 1.4 | 1.45 | 263.156 | 262.223 |
| LZ4-multi | 174.37 | 6.633 | 0.033 | 0.017 | 183.23 | 33.41 |

### D24 Command

Published expected bytes: 327,759,206. Compatibility: **NOT EXACTLY REPRODUCED**. Official archive acquired. First10000 WAVs in archive order total328499914 bytes; lexical order totals327554434. Neither equals published327759206. Selection/order cannot be inferred from size alone.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 136.246 | 3.487 | 2495.9 | 2499.517 | 114.051 | 113.547 |
| Lstm-compress | 141.577 | 3.623 | 1224.533 | 1208.2 | 9.961 | 9.992 |
| DeepZip | 558.719 | 14.3 | 1002.417 | 149.517 | 21055.316 | 3873.039 |
| DeepZip* | 562.55 | 14.398 | 1002.417 | 149.517 | 21055.316 | 3873.039 |
| DZip | 144.838 | 3.707 | 1109.917 | 391.367 | 21093.313 | 4167.078 |
| DZip* | 148.669 | 3.805 | 1109.917 | 391.367 | 21093.313 | 4167.078 |
| TRACE | 143.144 | 3.664 | 143.683 | 270.15 | 5661.016 | 6248.0 |
| PAC | 151.165 | 3.869 | 150.333 | 246.45 | 5650.383 | 6183.984 |
| GZip | 225.45 | 5.77 | 0.483 | 0.067 | 1.883 | 1.773 |
| PBzip2 | 185.766 | 4.754 | 0.067 | 0.033 | 148.301 | 118.242 |
| XZ | 184.56 | 4.724 | 3.1 | 0.2 | 1845.93 | 558.055 |
| BSC | 167.556 | 4.288 | 1.15 | 1.017 | 165.645 | 158.215 |
| SnZip | 288.635 | 7.387 | 0.033 | 0.017 | 3.23 | 3.203 |
| Lzma2 | 184.31 | 4.717 | 2.65 | 0.15 | 1605.215 | 505.125 |
| PPMD | 174.001 | 4.453 | 2.483 | 2.85 | 263.211 | 262.227 |
| LZ4-multi | 254.529 | 6.514 | 0.067 | 0.017 | 212.379 | 33.82 |

### D25 LibriSpeech

Published expected bytes: 359,034,309. Compatibility: **NOT EXACTLY REPRODUCED**. Official dev-clean archive acquired. Its2703 FLAC files total359034309 bytes, matching expected, but NNLCB concatenation order and file-boundary handling are unspecified.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| X3 | 338.466 | 7.908 | 762.233 | 364.483 | 1134.715 | 1134.82 |
| NNCP | 318.479 | 7.441 | 2895.517 | 2242.367 | 113.988 | 113.715 |
| Lstm-compress | 319.552 | 7.466 | 1420.183 | 1316.067 | 10.195 | 10.176 |
| DeepZip | 317.534 | 7.419 | 594.25 | 120.517 | 22975.688 | 4171.676 |
| DeepZip* | 321.365 | 7.508 | 594.25 | 120.517 | 22975.688 | 4171.676 |
| DZip | 317.523 | 7.419 | 803.6 | 386.367 | 22979.719 | 4471.723 |
| DZip* | 321.354 | 7.508 | 803.6 | 386.367 | 22979.719 | 4471.723 |
| TRACE | 319.317 | 7.461 | 170.767 | 289.333 | 6167.133 | 6746.48 |
| PAC | 318.355 | 7.438 | 195.567 | 306.167 | 6161.402 | 6699.219 |
| GZip | 321.477 | 7.511 | 0.233 | 0.05 | 1.824 | 1.781 |
| PBzip2 | 322.556 | 7.536 | 0.083 | 0.05 | 156.027 | 120.512 |
| XZ | 322.676 | 7.539 | 2.0 | 0.15 | 2013.664 | 753.809 |
| BSC | 320.907 | 7.498 | 1.7 | 1.667 | 159.426 | 156.297 |
| SnZip | 325.677 | 7.609 | 0.017 | 0.017 | 3.113 | 3.109 |
| Lzma2 | 322.307 | 7.53 | 0.95 | 0.083 | 1832.605 | 675.258 |
| PPMD | 327.188 | 7.645 | 4.45 | 4.933 | 263.441 | 262.246 |
| LZ4-multi | 322.461 | 7.534 | 0.033 | 0.017 | 211.27 | 33.488 |

### D26 LJSpeech

Published expected bytes: 293,847,664. Compatibility: **NOT EXACTLY REPRODUCED**. Official LJ Speech1.1 acquired. First10000 WAVs total2899573344 bytes in archive order or2880776288 lexically, approximately10x the published293847664. Neither first1000 ordering matches either. Authoritative preparation is unresolved.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| X3 | 206.139 | 5.885 | 889.767 | 487.117 | 1014.281 | 1014.379 |
| NNCP | 148.944 | 4.251 | 2419.333 | 2258.217 | 113.902 | 113.512 |
| Lstm-compress | 156.206 | 4.459 | 1362.583 | 1118.167 | 10.008 | 9.988 |
| DeepZip | 725.921 | 20.723 | 522.667 | 138.333 | 19270.68 | 3549.082 |
| DeepZip* | 729.752 | 20.833 | 522.667 | 138.333 | 19270.68 | 3549.082 |
| DZip | 168.531 | 4.811 | 651.35 | 310.7 | 5667.371 | 3847.301 |
| DZip* | 172.363 | 4.921 | 651.35 | 310.7 | 5667.371 | 3847.301 |
| TRACE | 157.156 | 4.486 | 170.133 | 238.45 | 5104.77 | 5696.98 |
| PAC | 167.597 | 4.784 | 196.117 | 247.233 | 5104.531 | 5623.844 |
| GZip | 240.003 | 6.851 | 0.283 | 0.067 | 1.895 | 1.898 |
| PBzip2 | 205.676 | 5.872 | 0.067 | 0.033 | 151.281 | 120.789 |
| XZ | 205.467 | 5.866 | 2.533 | 0.233 | 1826.195 | 551.094 |
| BSC | 188.324 | 5.376 | 1.183 | 1.067 | 165.559 | 153.766 |
| SnZip | 279.587 | 7.982 | 0.017 | 0.017 | 3.23 | 3.043 |
| Lzma2 | 204.908 | 5.85 | 1.85 | 0.183 | 1334.871 | 493.852 |
| PPMD | 195.713 | 5.587 | 2.833 | 3.133 | 263.383 | 262.359 |
| LZ4-multi | 270.723 | 7.728 | 0.033 | 0.017 | 209.367 | 33.434 |

### D27 DNACorpus

Published expected bytes: 685,597,124. Compatibility: **NOT EXACTLY REPRODUCED**. Official DNACorpus archive acquired. Its17 file lengths sum to685597124, matching expected, but no authoritative concatenation order or prepared-stream hash is published.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 144.658 | 1.769 | 4443.283 | 4274.617 | 113.965 | 113.727 |
| Lstm-compress | 621.516 | 7.605 | 1398.383 | 1438.817 | 5.668 | 5.598 |
| DeepZip | 152.098 | 1.861 | 455.383 | 95.317 | 17525.047 | 8152.754 |
| DeepZip* | 152.225 | 1.863 | 455.383 | 95.317 | 17525.047 | 8152.754 |
| DZip | 146.872 | 1.797 | 787.133 | 515.433 | 17510.566 | 8402.57 |
| DZip* | 146.999 | 1.799 | 787.133 | 515.433 | 17510.566 | 8402.57 |
| TRACE | 152.83 | 1.87 | 290.083 | 572.033 | 11475.219 | 12016.211 |
| PAC | 147.308 | 1.802 | 300.583 | 500.25 | 11464.469 | 12009.027 |
| GZip | 177.455 | 2.171 | 9.9 | 0.1 | 1.816 | 1.902 |
| PBzip2 | 171.842 | 2.102 | 0.083 | 0.067 | 141.438 | 96.395 |
| XZ | 147.148 | 1.8 | 6.05 | 0.067 | 3221.172 | 994.086 |
| BSC | 150.064 | 1.836 | 1.15 | 0.817 | 164.438 | 158.465 |
| SnZip | 300.928 | 3.682 | 0.217 | 0.133 | 3.195 | 3.078 |
| Lzma2 | 147.151 | 1.8 | 6.7 | 0.067 | 2550.41 | 809.141 |
| PPMD | 158.915 | 1.944 | 3.817 | 4.133 | 262.926 | 262.406 |
| LZ4-multi | 223.475 | 2.734 | 1.133 | 0.033 | 152.094 | 31.066 |

### D28 ERR7091247

Published expected bytes: 1,926,041,160. Compatibility: **NOT EXACTLY REPRODUCED**. Four authoritative representations investigated. Default fastq-dump 3.4.1 of the pinned full-quality normalized SRA produces1926041160 bytes and32 distinct byte values, matching the published length and alphabet; SHA256 d2b1baa824dc387a306de2b7d3b5ed0cf48e5a4e060b233ec70057c3f3099f2a. This is a stronger source candidate, but NNLCB does not publish a prepared-file hash or export command, so historical byte equivalence is not yet certified. The current NCBI browser export has the same length but simplified qualities and31 byte values; ENA and original-submitted FASTQ lengths differ. No candidate is silently substituted.

Exact local input bytes: Unavailable; SHA-256: `None`.

**Controlled local comparison — high-compression-v1**

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

**Published NNLCB platform — not local timing**

| Algorithm | CS reported MegaBytes | CR bits/byte | CT min | DT min | CPM reported MegaBytes | DPM reported MegaBytes |
| --- | --- | --- | --- | --- | --- | --- |
| NNCP | 197.778 | 0.861 | 11357.467 | 11218.567 | 114.031 | 113.77 |
| Lstm-compress | 214.544 | 0.934 | 4473.067 | 4505.5 | 5.75 | 5.898 |
| DeepZip | 231.633 | 1.009 | 3073.35 | 392.583 | 120284.188 | 19114.172 |
| DeepZip* | 233.84 | 1.018 | 3073.35 | 392.583 | 120284.188 | 19114.172 |
| DZip | 206.217 | 0.898 | 4081.667 | 1398.883 | 35242.859 | 19259.707 |
| DZip* | 208.423 | 0.908 | 4081.667 | 1398.883 | 35242.859 | 19259.707 |
| TRACE | 226.757 | 0.988 | 767.4 | 1417.767 | 31565.016 | 32155.965 |
| PAC | 194.969 | 0.849 | 870.967 | 1448.133 | 31566.375 | 32079.23 |
| GZip | 370.926 | 1.616 | 9.483 | 0.233 | 1.871 | 1.777 |
| PBzip2 | 303.885 | 1.324 | 0.2 | 0.083 | 123.426 | 98.289 |
| XZ | 266.885 | 1.162 | 9.467 | 0.1 | 8231.441 | 2581.18 |
| BSC | 247.923 | 1.08 | 3.167 | 2.117 | 167.516 | 140.301 |
| SnZip | 614.493 | 2.676 | 0.417 | 0.267 | 3.293 | 3.121 |
| Lzma2 | 275.081 | 1.198 | 5.533 | 0.117 | 6614.945 | 2123.047 |
| PPMD | 277.78 | 1.21 | 7.433 | 7.733 | 263.387 | 262.246 |
| LZ4-multi | 453.821 | 1.977 | 1.2 | 0.05 | 167.094 | 31.004 |

## Full 28 × 19 qualification matrix

| Status | Cells |
| --- | --- |
| NOT APPLICABLE | 28 |
| NOT REPRODUCIBLE | 420 |
| UNSUPPORTED | 84 |

All 532 statuses and explanations: [CSV](../../tables/nnlcb-qualification.csv) / [JSON](../../tables/nnlcb-qualification.json). No blank cells. GPU memory is N/A because CIX is CPU-only. Params/FLOPs/MIL are unsupported instrumentation, not zero: the implementation contains adaptive PAQ mixers and sometimes an LSTM. The vocabulary is: CR, SSP, CRP, AvgCR, WavgCR, AvgSSP, WavgSSP, CT, DT, CPM, DPM, GPM, AvgCPM, AvgDPM, TotalCT, TotalDT, Params, FLOPs, MIL.

## Synthetic scaling — separate from real-world corpus evidence

Thirteen deterministic classes, each scheduled at 10 MiB, 100 MiB, 1 GiB and 10 GiB. Generators use a fixed seed and SHAKE256; the heterogeneous composite mixes classes. Public generator state is not supplied to any compressor. [Generator](../../scripts/generate_synthetic.py). Missing 10 GiB measurements are never extrapolated.

### Synthetic high_entropy, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sequential_bytes, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic incrementing_u64, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic periodic, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic low_entropy_ascii, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic grammar_ascii, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic csv_records, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic json_logs, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mutated_records, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sparse_binary, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic delta_timeseries, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mixed_entropy, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic heterogeneous, 10485760 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic high_entropy, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sequential_bytes, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic incrementing_u64, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic periodic, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic low_entropy_ascii, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic grammar_ascii, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic csv_records, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic json_logs, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mutated_records, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sparse_binary, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic delta_timeseries, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mixed_entropy, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic heterogeneous, 104857600 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic high_entropy, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sequential_bytes, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic incrementing_u64, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic periodic, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic low_entropy_ascii, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic grammar_ascii, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic csv_records, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic json_logs, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mutated_records, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sparse_binary, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic delta_timeseries, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mixed_entropy, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic heterogeneous, 1073741824 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic high_entropy, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sequential_bytes, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic incrementing_u64, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic periodic, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic low_entropy_ascii, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic grammar_ascii, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic csv_records, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic json_logs, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mutated_records, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic sparse_binary, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic delta_timeseries, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic mixed_entropy, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

### Synthetic heterogeneous, 10737418240 bytes

| Algorithm | Status | Compressed bytes | Ratio (original/compressed) | Compression s | Decompression s | Compression MiB/s | Decompression MiB/s | Measured n per input |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gzip | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| bzip2 | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zstd | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| xz | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| brotli | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| zpaq | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| paq8px | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| CIX | NOT MEASURED: 1 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

## Compression time, decompression time and memory

The local comparison tables show both wall times and throughput. Peak memory is largest-process kernel RSS; sampled summed process-tree RSS is retained separately and may double-count shared pages or miss brief peaks. No cross-hardware speed ranking is implied. Input-size/resource scaling conclusions require completed size-series observations.

| Dataset | Algorithm | Compression peak RSS bytes | Decompression peak RSS bytes |
| --- | --- | --- | --- |

## Reproduction and raw evidence

[CSV results](../../results.csv) · [JSON results](../../results.json) · [Frozen schedule](../../raw/controlled-v1-schedule.json) · [NNLCB dataset manifest](../../manifests/nnlcb-datasets.json) · [Reference rows](../../tables/nnlcb-published-per-dataset.json) · [Qualification/recomputation](../../scripts/reproduce_nnlcb_metrics.py). Run the documented serial harness from the evidence repository. Exact wrapped commands, versions, hashes and raw-result paths accompany every completed result. Public-source acquisitions are pinned by hash. The final downloadable invocation archive and immutable release reference remain pending.

## Limitations, failures and completion blockers

- 552 scheduled dataset/algorithm summaries have no completed measured group
- Full exact, verified D1–D28 NNLCB qualification and aggregates are unavailable
- Final adversarial review and raw invocation archive have not been release-certified
- Immutable evidence release tag, archive and separate evidence Site are pending

| Dataset | Algorithm | Status | Reason |
| --- | --- | --- | --- |

The interrupted D1 CIX warm-up is preserved separately and was repeated only after its process was confirmed absent. No timing or size was inferred. Warm-ups and smoke tests are excluded from primary comparisons. [Execution record](../../EXECUTION-STATUS.md). A preparation tag is not an evidence release; this draft does not satisfy the publication gate.
