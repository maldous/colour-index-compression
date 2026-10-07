# Squash Compression Benchmark import

Pinned import of the public results published by the Squash Compression Benchmark. This is a data import, not a local CIX or codec rerun. The nine upstream per-machine CSVs preserve 59,220 published result rows across 28 datasets; all CSVs are committed unchanged alongside their hashes.

## Provenance

- Site: https://quixdb.github.io/squash-benchmark/
- Data repository: https://github.com/quixdb/squash-benchmark-web
- Pinned Git commit: [`fed6ea3374155184672b71928d2b805463d156f0](https://github.com/quixdb/squash-benchmark-web/commit/fed6ea3374155184672b71928d2b805463d156f0)
- Retrieved: 2026-09-30T22:47:59.213133+00:00
- Data licence: CC0-1.0 for benchmark data as stated by the benchmark site; attribution retained.
- Machine CSV blob IDs were checked against the pinned Git tree; local SHA-256 values are recorded in `manifest.json` and `SHA256SUMS`.

## Metrics

Squash reports compressed bytes, compression/decompression CPU seconds, and corresponding rates. The benchmark FAQ explicitly says the displayed time is CPU time (wall time is captured but not displayed). Ratio is input bytes divided by compressed bytes; the table derives MiB/s using 1,048,576 bytes per MiB. The source does not report memory. See the `metrics` and `comparability_note` fields in `manifest.json`.

## Files

- `manifest.json`: pinned source, dataset and machine metadata, row/file counts, publisher Git blob IDs and local SHA-256s.
- `raw/<machine>.csv`: original upstream published result CSVs, unmodified.
- `SHA256SUMS`: SHA-256 for the manifest and each raw CSV.

## Reproduce / verify

From the repository root, use `python benchmarks/import_squash_benchmark.py --output docs/research/2026-10-01-squash-benchmark` to fetch the pinned files and verify Git blob IDs, CSV schema, machine/dataset coverage and row counts. The importer prints its verification summary.

These historical measurements are shown in a separate Site tab. They use the upstream hardware and settings and are not merged into the local Silesia ranking or presented as same-machine results.
