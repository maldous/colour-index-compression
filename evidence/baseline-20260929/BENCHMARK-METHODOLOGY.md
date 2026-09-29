# Frozen baseline methodology v1

Status: preparation; no controlled compression measurement has begun.
All limits and profiles below apply uniformly and are frozen before scheduling.

## Implementation and isolation

CIX commit `f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6`, standalone
`benchmarks.competitive_cli`, portfolio25, no candidate caches. Fresh offline
rebuild reproduced all seven native hashes exactly. CIX source is extracted
into a separate runtime and rechecked against SOURCE-MANIFEST before each run.
Frozen CIX source/configuration will not be changed in response to any dataset.
Format detection already present in the encoder is disclosed; this is not a
claim that its development was blind to Silesia. No filename/hash recognition,
saved streams, source lookup or external pretrained input-specific state is
allowed in the benchmark execution path.

The encoder's documented internal round-trip check is part of its normal
command. Compression wall time includes it, startup and normal source/output
I/O. Decompression is also measured independently. Downloads, source hashing,
preparation, builds, filesystem pre-reads and final SHA-256 verification are
outside those phase timers. No CPU-only estimate replaces end-to-end timing.

## High-compression profile

| Algorithm | Compression options | Decode options | Configured worker limit |
|---|---|---|---|
| gzip | `-9 -n -c` | `-d -c` | 1 |
| bzip2 | `-9 -c` | `-d -c` | 1 |
| Zstandard | `--ultra -22 --long=27 -T1 -c` | `-d -T1 -c` | 1 |
| XZ/LZMA2 | `-9e -T1 -c` | `-d -T1 -c` | 1 |
| Brotli | `-q 11 -w 24 -c` | `-d -c` | 1 |
| ZPAQ | `add archive.zpaq input.bin -method 5 -threads 1` | `extract archive.zpaq input.bin -to restored.bin -threads 1` | 1 |
| paq8px v215 | `-12L -simd AVX2` | `-d -simd AVX2` | 1 |
| CIX | `-m benchmarks.competitive_cli encode` | corresponding `decode` | 1 CPU affinity |

These are named high-compression settings, not a claim of equal algorithms or
equal memory. Zstd's window is 2^27 bytes; Brotli's window setting is 24;
XZ -9e uses the preset's dictionary. paq8px memory level12 and LSTM are explicit.
No PAQ `T` external dictionary pretraining or `E` executable pretraining option
is enabled. Exact versions, hashes and full argv appear in the manifests/logs.
Built-in standard decoder tables are part of the identified decompressor;
external dictionaries, models and sidecars would be separately counted. None
may be omitted from physical size. CIX's adaptive state is reconstructed by
the decoder, with each archive starting from the fixed initial state.

Both phases run in a Bubblewrap mount/PID/network namespace. The runtime,
qualified Python environment and reference tools are read-only. The decoder's
only data directory initially contains the compressed artifact; it has no
original input, encoder logs, selection files, corpus mount or network access.
Wrapper startup and namespace creation are included equally in each phase's
wall time. The complete wrapped argv is retained in raw timing records.

All processes inherit affinity to logical CPU2, a performance-core logical CPU
on this machine. BLAS/OpenMP thread variables are1; GPU visibility is empty.
Some tools have a main/I/O thread in addition to a worker. Affinity restricts
the entire process tree to the same one logical CPU. No local parallel
compression jobs or intentional heavy research workloads run during measurement.
Unrelated user services are not stopped; their measured background presence is
disclosed. The environment snapshot and each phase retain observed load.

## Limits and repetitions

- Wall limit: 36 hours **per compression or decompression phase**, every tool.
- Memory: 48 GiB per-process virtual address limit plus a sampled48GiB summed
  process-tree RSS guard. A limit/error is retained, never replaced by a smaller
  input or favourable earlier result.
- Disk preflight: room for a full-size archive plus5GiB reserve, then a separate
  check for the full restored file after actual archive size is known. Full-size
  normal files are used; sparse-source assumptions and a hash-only output sink
  do not replace real output writes. Space failures are explicit.
- Inputs at or below1GiB: one warm-up and three measured repetitions, scheduled
  by a fixed randomized/interleaved order. Failed warm-ups do not vanish.
- Larger inputs, including full Wikipedia and10GiB synthetic assets: one full
  measured repetition initially, explicit n=1 and no claimed dispersion.
  A timeout/resource failure is not retried three times merely to waste resources.
- Fresh compressor process per phase; source/archive is sequentially pre-read
  immediately before that phase for every algorithm. No global cache flushing.
  Inputs larger than available RAM are labelled cache-capacity-limited.
- Retain each repetition, including failures. The primary timing is the median
  of the prescribed verified repetitions; publish min/max/MAD and sample count.
  Incomplete repetition schedules remain incomplete, not a successful3-run set.

## Bytes, verification and memory

All compressors receive identical bytes through a neutral `input.bin` hardlink.
No input edits occur. Every output archive is new and self-contained. All file
framing, checksums, indexes and selection metadata count. Bytes are file logical
length, not allocated disk blocks. Archive sizes and SHA-256 are retained.
After independent decompression, both exact length and SHA-256 must match.
The verified disposable restored file and neutral hardlink are removed.
For inputs over100,000,000 bytes, the verified archive is also removed after
its size/hash and full round-trip proof are recorded, to bound local disk use.
Smaller physical archives remain preserved. Deletion happens outside phase
timing. Every raw measurement and reproduction command remains available.

GNU/Linux `wait4` records user/system CPU, largest-process peakRSS, I/O blocks
and context switches. GNU time runs inside the namespace because the outer
supervisor's wait4 accounting omits the actual workload on this kernel; outer
supervisor data is preserved separately. Wall time uses a monotonic high-resolution clock through
process termination, not a polling interval. A50ms sampler additionally records
simultaneous summed RSS over the process tree. Summed RSS may double-count
shared pages and miss sub-sample peaks; it is not described as exact cgroup/USS
memory. Both measurements remain available. CPU utilisation=(user+system)/wall.

## Units and calculations

GiB=2^30 bytes, MiB=2^20 bytes; decimal GB=10^9 bytes is separately labelled.
The raw counts are authoritative.

```
ratio = original_bytes / compressed_bytes
compressed_percent = 100 * compressed_bytes / original_bytes
saving_percent = 100 * (1 - compressed_bytes / original_bytes)
bits_per_input_byte = 8 * compressed_bytes / original_bytes
compression_MiB_s = original_bytes / 1048576 / compression_wall_seconds
decompression_MiB_s = original_bytes / 1048576 / decompression_wall_seconds
```

NNLCB has different naming and compressed-size weighting. See
NNLCB-COMPATIBILITY-NOTES.md and `scripts/reproduce_nnlcb_metrics.py`.
Published NNLCB timing/resource values never share a ranking with local timing.

## Data and scaling

Silesia: all12 canonical members independently, with totals clearly identified.
NNLCB D19's unspecified concatenation order is a separate qualification issue.
Wikipedia:20260901 pages-articles-multistream XML, all bzip2 members decompressed
in order, no filtering, no sampling, no content transformation. Input byte size
and SHA-256 are determined by actual preparation, not estimates.

Synthetic v1 uses13 explicitly labelled classes, a fixed public seed and
SHAKE256-based deterministic pseudo-random blocks. Prefixes:10MiB,100MiB,1GiB,
10GiB. Generator code/hash/seed are published but never supplied to compressors.
The high-entropy random stream must show plausible overhead, not magical gain.
CSV/JSON/text are synthetic style generators, not actual records/documents.
Scaling exponents will be estimated only from completed observations, retaining
per-size measurements and censored DNFs. No extrapolation is a10GiB result.

## Publication gate

Freeze source, preserve all raw results, verify every reported round trip,
independently recompute arithmetic, expose all28×19 qualification statuses and
all failed/incomplete runs, commit/tag/archive evidence, then publish to a new
Sites URL. A missing Wikipedia headline or incompatible NNLCB aggregate is
visible. A preparation page is not completion. The research Site stays separate.
