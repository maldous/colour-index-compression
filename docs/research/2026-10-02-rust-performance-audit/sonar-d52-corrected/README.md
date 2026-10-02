# Corrected local Sonar scan: d52fa7f72

Frozen source revision: `d52fa7f72b3708b1ecaa5b1445b70ea2e28b0781`.

This local-only scan used the latest reviewed SonarQube and scanner images at
`127.0.0.1:9013`. The server was constrained to CPUs 24,25 with 4 GiB memory
and no additional swap; the scanner used the same CPUs, 1 GiB memory, and zero
swap. `resources.raw` records the actual cgroup readback. No credential or
token is stored in this packet.

The direct Rust 1.98.1 Clippy run produced 743 compiler messages. Its complete
raw stream is retained. Compiler diagnostics were rewritten only to normalize
Cargo's relative and `#[path]` locations into repository-relative locations,
then deduplicated by rule, primary location and message into 200 compact,
one-object-per-line JSON records. Every compact line parses as JSON. The scan
log contains no Clippy JSON parse failure.

The scanner indexed first-party Rust production sources, examples, tests, and
benchmarks. It completed upload for the exact source revision, then the quality
gate failed with 67 open issues: 17 native `rust:S3776` findings and 50 imported
Clippy findings. `native-s3776.tsv` and `rule-counts.tsv` provide the complete
open finding inventory. The raw ledger remains authoritative for unsupported
or unmappable Clippy records: the importer dropped 17 records, listed in
`importer-drops.tsv`; they are not represented as clean findings.

`scanner-preflight-mount-failure.log` is retained for provenance only. It was
the first scanner attempt, which failed before analysis because the container
did not have the detached worktree's shared `.git` metadata mounted. The
successful `scanner.log` mounted the source tree read-only and uploaded the
analysis. Neither attempt changed Rust source.

| artifact | SHA-256 |
| --- | --- |
| `clippy-raw.jsonl` | `1f7c4b9bb340c5029b342ae68a1566f6a6b95d199e6e3842769d0bf0b1b62bd3` |
| `clippy-normalized-unique.ndjson` | `143963743d8b3e67bca86950853718691cb4502a176112c92f1ee7581975ff4d` |
| `clippy.stderr` | `69e930709bcf0d283030ae50c5245c8216eca62526bd3a941dd473da4eed7aaa` |
| `open-issues.json` | `246a4646e3ef4c7114858fbd98992c7a9410901f53230fe254088961a8a5b2b8` |
| `resources.raw` | `752e087446729f86dbe8a27c4b6320d93f9ff61a203c484147e3d2ed1fa796a2` |
| `scanner.log` | `86582a30bb525e6bb8fbe173a7216658ee4c442b057f3cc429b0fe3951177785` |
