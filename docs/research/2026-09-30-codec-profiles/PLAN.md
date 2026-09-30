# Speed / size settings extension — predeclared screening

User requested two extreme settings axes, independent of ranking by size or
time. Existing frozen CIX and evidence are unchanged. No new datasets, full
corpus compression, workflow/Actions work or release of repository source.
Only the benchmark Site is authorized public.

| Method | Speed preset | Size preset | Existing/current |
|---|---|---|---|
| CIX | frozen fast | frozen maximum | balanced |
| gzip | 1 | 9 | 9 |
| bzip2 | 1 | 9 | 9 |
| XZ/LZMA2 | 0 | 9 + EXTREME | 6 |
| Brotli | 0 | 11 | 6 |
| Zstandard 1.5.5 | --fast=131072 | --ultra -22 | 3 |
| paq8px v216 | -1, AVX2 | -12L, five LSTM layers: RESOURCE_LIMIT | -8, AVX2 |

These are declared speed/size-oriented extremes, not a proof of the optimal
configuration for every input. Compression level 0 in gzip/PAQ (store-only)
is excluded from the speed compression comparison. No PAQ E/T pretraining or
external dictionaries/state are enabled. Normal reference content models and
Brotli's public built-in dictionary remain disclosed reference implementation
features; none is inserted into the generic CIX pipeline.

Six pre-existing immutable 16 KiB ranges, rehashed before execution. They were
already exposed by earlier measurements: their original `heldout` provenance
is preserved, but this is not a fresh holdout or a whole-dataset assessment.
Previously completed CIX fast/maximum records remain intact. New repetitions
measure all feasible settings on the same apparatus; no startup-only timings
are represented as steady-state throughput.

One warmup and three separately launched measured processes per encode and
decode. GNU time includes program startup, normal source/output I/O and every
CIX discarded candidate; median timing, min/max and MAD retained. The physical
primary is median archive size with ties by repeat index; all three streams
retained and independently decoded with original paths inaccessible. All
restorations must match SHA-256 and full original byte equality.

Existing shared WaveScheduler: at most four distinct physical cores, aggregate
12 GB memory, 4 GB temporary, no swapping; each cell reserves 2 GB (PAQ 3 GB),
100 MB temporary, 180 seconds. PAQ -12L's approximately 29 GB requirement
exceeds the whole research budget and is explicitly blocked, not substituted
with another preset. No unrelated process is stopped or system swap changed.
One verification/command/budget failure stops dispatch for inspection.

Preparation freezes immutable manifests/build hashes before work. Distinct
profile cells preserve backend attribution, all framing/model metadata and
source/binary/config identities. No input-specific tuning and no factorial
parameter sweep. Profile rankings must never mix settings groups silently.

Authoritative option references (retrieved 2026-09-30):
https://github.com/hxim/paq8px/tree/v216
https://github.com/facebook/zstd/tree/v1.5.5
https://tukaani.org/xz/man/xz.1.html
https://github.com/google/brotli/blob/master/c/include/brotli/encode.h
https://docs.python.org/3/library/gzip.html
https://docs.python.org/3/library/bz2.html

Local executable --help and version output govern pinned versions rather than
assuming current upstream master matches the older binary.
