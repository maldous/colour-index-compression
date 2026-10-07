# Corrected local Sonar scan: 40d3520db

Frozen source revision: `40d3520db`.

The scan used `sonarqube:latest` and `sonarsource/sonar-scanner-cli:latest`
locally at `127.0.0.1:9013`. The server was limited to CPUs 24,25 and 4 GiB;
the scanner was limited to the same CPUs and 1 GiB. Server `MemorySwap`
equalled `Memory`, so it had no additional swap allocation.

Rust `1.98.1` and Clippy `0.1.98` generated the raw JSON-lines ledger.
Diagnostics were deduplicated by rule, primary source location and message,
then written as compact one-object-per-line JSON for the scanner. No Clippy
parse error was emitted.

The quality gate failed: 87 open issues were returned. It reported 26 native
`rust:S3776` findings: 11 in
`main.rs`, 6 in `ppm.rs`, 3 in `chain.rs`, 2 in `bwt_legacy.rs`, and one each
in `parallel_pipeline.rs`, `sparse_runs.rs`, `portfolio_auto.rs`, and
`legacy_lz.rs`. Imported Clippy findings remain separately listed in
`open-issues.json`, including 11 argument-count, 8 multiple-of and 7
ceiling-division diagnostics.

| artifact | SHA-256 |
| --- | --- |
| clippy-raw.jsonl | b12d2a52dd2f68262290604200f54bb01c094d494efd3d451c895c5b239ebd7f |
| clippy-unique.ndjson | 549c1ac7c58f48c53b9b07ee85326c38d21bd130929f6c3c76a7498ed5db9e0e |
| open-issues.json | 85c2ff013d725c2c789f96ee23dfc2bfc4526f6478355e1dddeea07df34db7ed |
| scanner.log | 9a1fd067cbbb78266b495d843211088948de7e85619bf51e0384546791e64448 |

The raw ledger remains authoritative for diagnostics that the Sonar Clippy
importer cannot represent. The importer dropped 22 diagnostics: three
`chunks_exact_to_as_chunks` and six `manual_isolate_lowest_one` reports because
those rules are unknown; two `src/lib.rs`, ten `src/main.rs`, and one benchmark
report because the multi-target paths were not mappable to indexed files.
These omissions are recorded in `importer-drops.tsv`; they are not treated as
clean findings. `rule-counts.tsv` gives every issue returned by Sonar.

`manifest.json` records immutable source, image, tool, host, resource and
artifact provenance. It contains no credentials.
