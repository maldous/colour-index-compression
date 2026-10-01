# Native Rust CIX Silesia benchmark

This wave uses the merged Rust `cix` and `uncix` release binaries for future
CIX rows. It covers only the existing 12 verified Silesia files. The earlier
Silesia and Python measurements remain immutable historical controls.

It measures CIXG1, the generic stream format used by the Squash plugin, and
CIXM6, the native legacy-mode portfolio. Both formats are tested at three
bounded profiles:

| Profile | Rust effort | Block size | Codec memory |
|---|---:|---:|---:|
| fast | 1 | 32 KiB | 256 MiB |
| current | 6 | 32 KiB | 384 MiB |
| size | 9 | 64 KiB | 512 MiB |

The native bounded selector has different timing and route choices from the
Python reference; profile labels identify the comparison budget, not identical
candidate searches. CIXG1 and CIXM6 results are reported separately. Archives
include all framing and integrity bytes, and each is decoded from the archive
without using the source path. Complete output hash and length must match the
frozen Silesia identity.

## Run

The matrices and build hashes were frozen before execution in `cells.json`,
`manifests/`, and `environment.json`. To reproduce them from the repository
root:

```sh
python3 benchmarks/silesia_rust_native_matrix.py run --trial
python3 benchmarks/silesia_rust_native_matrix.py run
python3 benchmarks/silesia_rust_native_matrix.py collect
```

The first command runs the six predeclared Dickens trial cells. The full wave
uses the existing `WaveScheduler` limits: four physical cores, 12 GB aggregate
memory, 4 GB aggregate temporary space, 2 GB per cell, 100 MB per-cell working
space, 300 seconds per phase, and swap disabled. Do not rerun or replace a
claimed cell; failures remain recorded and require a new experiment identity.

All rows use Silesia only. These are exposed measurements, not holdout results
or claims about other data classes. No acquisition, Actions, or publication is
part of this wave.

## Dickens screening trial

The six predeclared Dickens cells were run locally. Four completed: all three
CIXG1 profiles and CIXM6 fast. Each Rust archive restored the exact 10,192,446
source bytes, passed the bounded Rust decoder, and was independently decoded
by Python with the same source SHA-256. The CIXM6 current and size profiles
reached their predeclared 300-second encode-phase limit and remain failures;
they were not retried. The remaining 66 cells were not launched. These are
screening results on one Silesia member, not a completed matrix.

| Format/profile | Archive bytes | Encode MiB/s | Decode MiB/s | Peak RSS (KiB) |
|---|---:|---:|---:|---:|
| CIXG1 fast | 4,777,286 | 0.775 | 29.46 | 19,712 |
| CIXG1 current | 4,256,837 | 0.755 | 37.39 | 19,712 |
| CIXG1 size | 4,071,223 | 0.717 | 40.50 | 19,712 |
| CIXM6 fast | 3,846,946 | 0.040 | 4.63 | 19,712 |

The measured throughput uses the 10,192,446-byte input. Peak RSS is the
runner's sampled process peak. Cell results and scheduler receipts are recorded
in `results.json` and `trial-evidence/`; archives and restored copies are kept
out of Git.
