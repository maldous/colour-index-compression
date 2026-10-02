# Corrected local Sonar/Clippy inventory — 45e7c68e7

Frozen source revision: `45e7c68e7`.

## Completed local work

The direct stable Rust 1.98.1 Clippy command completed locally with all
targets and features.  Its complete Cargo JSON stream has 762 lines, 582
compiler-message records, and 294 Clippy warnings.  A normalizer retained
Clippy warnings with first-party primary locations, normalized their paths to
repository-relative paths, and deduplicated by rule, primary location, and
message.  The resulting compact, one-object-per-line importer file contains
48 records.  Every line was parsed after writing; the normalizer recorded zero
JSON errors and zero unmappable records.  It did not suppress any diagnostic.

## Corrected Sonar upload

The reviewed local server is up at `127.0.0.1:9013`.  A project-scoped local
analysis token allowed a corrected host-network scan to upload the exact frozen
revision successfully; `ce-task.json` reports `SUCCESS` and
`quality-gate.json` reports `ERROR`.  No credential value is retained here.

The scanner indexed 77 files.  It imported 33 of the 48 compact Clippy
records.  Fifteen records were rejected by the current Sonar importer: twelve
for `src/lib.rs` or `src/main.rs` locations and three for rules the importer
does not support.  These are listed in `importer-drops.tsv` and retained in
the raw ledger.  They are not treated as clean findings.

The corrected query uses `resolved=false`.  It reports 42 current open issues:
9 native `rust:S3776` findings and 33 imported external-Clippy findings.  This
matches the 33 importer-accepted records exactly.  `native-s3776.tsv`,
`rule-counts.tsv`, and `open-issues.json` retain their exact locations and
counts.

An earlier unfiltered API query returned 559 historical issue records (80
native and 479 external).  That endpoint includes closed historical records;
it does not represent the current open inventory.  It is preserved separately
as `all-status-issue-history.json` with matching all-status tables so the
correction is auditable.  No historical finding was marked resolved manually.

The d52 and 45e scans have the same documented scope: source
`rust/cix-native/src,rust/cix-native/examples`, tests
`rust/cix-native/tests,rust/cix-native/benches`, and 77 indexed files.  The
current difference is source revision and the 45e raw Clippy ledger (48 unique
records, 33 imported, 15 rejected); it is not a source-scope expansion.

Two early scanner attempts are retained: a bridge-network timeout and a
temporary HTTP 401 before the scoped token was provisioned.  Two more uploads
used an obsolete property spelling and therefore did not import the ledger.
The final scan used the documented `sonar.rust.clippyReport.reportPaths`
property with automatic Clippy disabled.  The final importer still rejected
the 15 records above, which is an analyzer limitation documented by the log.

The initial server cgroup receipt found `memory.max=4 GiB` but
`memory.swap.max=max`: Docker's `MemorySwap=Memory` inspection value did not
prove zero swap on this host.  The dedicated CIX server was then explicitly
enforced to `memory.swap.max=0`; `server-cgroup-enforced.raw` retains its
container, cgroup path, limit, and current usage.  No other container was
touched.

The final clean-project scanner was read while live.  Its cgroup receipt
proves CPUs 24,25, `memory.max=1 GiB`, `memory.swap.max=0`, and zero current
swap.  Its temporary project token was revoked with HTTP 204 after analysis;
the receipt contains no token value.

## Clean-project control

To eliminate all retained-identity ambiguity, the final scan was repeated in
a new local project, `cix-native-rust-local-review-45e-clean`, with exactly the
same complete 77-file scope and the same compact report.  It produced the
same 42 current open findings: 9 native S3776 and 33 imported Clippy.  Its
compute-engine task is `SUCCESS` and its quality gate is `OK`.

This establishes that the current issue count is independent of the original
project's historical closed records.  The separate clean project remains local
as a reproducibility control; no historical findings were altered.

## Artifacts

- `clippy-raw.jsonl`: complete direct Cargo JSON output.
- `clippy-import.ndjson`: compact, repository-relative normalized input.
- `clippy-import-cargo-relative.ndjson`: cargo-relative retry input used by
  the final upload.
- `clippy-ledger.json`: raw, deduplicated, and drop accounting.
- `scanner-corrected.log`: successful upload with the documented external
  report property.
- `raw/scanner-*.log`: all failed and diagnostic upload attempts.
- `open-issues.json`, `native-s3776.tsv`, and `rule-counts.tsv`: complete
  current-open post-upload issue packet.
- `all-status-issue-history.json`: the retained unfiltered historical API
  response, explicitly separate from current open findings.
- `resources.raw`, `server-cgroup.raw`, and `server-cgroup-enforced.raw`:
  source, tool, image, server, and cgroup receipts.
- `scanner-cgroup-final.raw`, `scanner-clean-final.log`, and
  `clean-*.json`: live scanner resource receipt and clean-project control.

No Rust source, scanner exclusions, suppression, workflow, or GitHub Actions
configuration changed in this packet.
