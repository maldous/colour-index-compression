# Production exact-byte candidate cache: scoped qualification

Source: `93d1c0fb1`, portable current-host all-feature `release-lto` build.
This implementation reuses inner encodings only for exact duplicate transformed
bytes within one mode-7 call. Candidate order, complete costs, strict tie
selection, reconstruction instructions and model history are unchanged.
The cache charges retained capacities against an explicit allowance; admission
failure preserves the original candidate search.

## Verified

- Locked/offline release build succeeded.
- Two focused library tests each ran once and passed. They check exact payload,
  description and candidate-table parity, actual cache hits, distinct-input
  misses, entry refusal and release of an unfunded payload capture.
- Actual M6 pipe: two 512-byte blocks, first 512 restored before producer EOF
  in 7.73 ms; final 1024 bytes restored exactly by frozen BD2 Rust decoder.
  Complete archive 27 bytes; aggregate cgroup peak 15,740,928 bytes.
- Actual G1 idle pipe: two 256-byte partial blocks with 50 ms flush interval;
  first 256 restored before producer EOF in 55.00 ms. Final 512 bytes restored
  exactly by the same old decoder. Complete archive 142 bytes; aggregate
  cgroup peak 15,958,016 bytes.
- Both pipelines ended with decoder exit zero after footer verification.
  Whole-stream integrity is confirmed only at that point.

These are single synthetic correctness/latency observations, not corpus
throughput comparisons. CLI fixtures do not establish mode-7 cache hits;
focused tests establish those. The separately qualified experimental search
eliminated two of eleven native calls with unchanged complete bytes; its
observed timing cannot be presented as a production speedup.

## Preserved failures and remaining gap

The original library filter selected zero tests. The corrected parity test
passed, but a runner read the old log and stopped. Neither was treated as
qualification. Correct test outputs and failed runner receipts are retained.
The original M6 idle check rejected `--flush-interval` before reading input:
that option was unsupported at this revision. M6 full-block streaming and G1
idle flushing were then declared separately and tested once. M6 idle flushing
is a separate source change under investigation, not qualified here.

This is not a full release suite, new Sonar scan, arbitrary-length memory
qualification, malformed-frame suite, held-out gate or multithread scaling
result. The corpus benchmark and Hutter work remain stopped. Old reference
rlib and decoder remain unchanged. No format change or Python dependency.

## Reproduction and binaries

`freeze.json` binds source/configuration/budgets and amendments. `raw/` retains
commands, actual child exits, GNU time and cgroup receipts. `schedule.py` is
archived as the final continuation script (completed build/tests deliberately
skipped); prior scripts are retained in raw. Replaying is a new measurement
identity, not overwriting these receipts. `stream_check.py` contains the actual
pipe protocol. `native-release.json` binds sealed current-host binaries under
`benchmark-work/chain-cache-93d1/final/`. Experimental archives/data stay outside
Git. Source branch: `research/silesia-competitive`.
