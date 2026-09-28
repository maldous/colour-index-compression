# Experimental competitive portfolio reproduction

The current standalone entry point is `benchmarks.competitive_cli`. It uses the
portfolio-10 encoder from source bytes. It does not look up corpus hashes, fetch
saved streams, read original data during decoding, or call GitHub/CI/network
services. Format detection and the bounded PAQ compute policy are part of the
encoder. The physical frame identifies the corresponding standalone decoder.

From this repository root, with its qualified local dependencies:

```sh
.venv/bin/python -m benchmarks.competitive_cli encode input.bin output.cix
.venv/bin/python -m benchmarks.competitive_cli decode output.cix restored.bin
cmp input.bin restored.bin
```

The encoder tries the complete fixed candidate portfolio, then independently
decodes its smallest physical result before writing it. Both commands refuse to
overwrite an existing destination. JSON output records physical sizes, hashes,
timing, process/child peak memory and candidate costs. Large inputs may take
hours; no cache is used by this interface. There is no claimed speed ranking.

The qualified environment uses Python 3.12, NumPy 2.5.3, imagecodecs 2026.8.16,
Brotli 1.2.0 and zstandard 0.25.0. Four local native libraries are required:

| Library under `results/leaderboard/` | Source under `benchmarks/` |
| --- | --- |
| native_ppm.so | native_ppm.cpp |
| native_mixer_rounding.so | native_mixer_rounding.cpp |
| native_ppm_decode.so | native_ppm_decode.cpp |
| native_legacy_mixer.so | native_legacy_mixer.cpp |

PAQ8px v215 and v216 binaries live under
`benchmark-work/references/paq8px-v215/build-local/paq8px` and the corresponding
v216 path. The exact source provenance and build fix are recorded in the
`v215-source.json`, `v216-source.json`, and `v216-build-fix.json` reference files.
The PAQ SIMD selection is AVX2. Preserve PAQ's upstream notices and licensing.
Published milestone reports record the qualified library and backend hashes;
different rebuilds require independent qualification before sharing a claim.

Benchmark acceleration is separate: the `competitive_*` cohort runners can
reuse completed physical artifacts only with their full source/input/backend
identity and independent restoration evidence. Their cache is not required by
the compressor or decoder. Each of the twelve Silesia members is an independent
stream, with all framing, checksum and selection costs included in its size.

This is an experimental local checkout, not yet a self-contained public source
release. A release must include the relevant Python/C++ sources, dependency
provenance, build instructions, upstream notices and a fresh rebuild check.
The numerical Silesia position is not an official listing.
