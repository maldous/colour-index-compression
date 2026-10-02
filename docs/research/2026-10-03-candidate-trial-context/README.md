# Candidate trial-context refactor review packet

## Scope

This packet reviews the bounded mechanical extraction from
`consider_cixg_candidates_parallel` and `encode_candidates`, with
`1d6471bc3` as the source base.
It adds typed trial policy/context/shared-state records and separates candidate
block input, route selection, and frame writing. Candidate route ordering,
whole-search and per-trial deadlines, resource admission, interruption
propagation, complete payload size comparisons, and first-index tie selection
remain in the original execution order.

`scoped-net.patch` contains the uncommitted net source change from `1d6471bc3`
for only the candidate-trial and candidate-encode regions. It is not a
candidate commit. No corpus input is retained in this packet.

## Exact bounded parity evidence

`run-parity.sh` was executed as the persistent root systemd unit
`cix-candidate-trial-context-20261003k` with `User=user`,
`AllowedCPUs=16`, `MemoryMax=1G`, and `MemorySwapMax=0`. The in-unit
readback in `raw-systemd.log` records:

- `memory.max=1073741824`
- `memory.swap.max=0`
- `cpuset.cpus.effective=16`

It uses the stable toolchain paths recorded in that log. Base binaries were
built at `1d6471bc3`; candidate binaries were built from this worktree.
`hashes.sha256` records source and binary hashes.

The matrix covers a 512-byte general fixture and 768-byte repetitive and
periodic fixtures framed as three 256-byte blocks. It includes CIXG1/CIXG2 ×
FAST/default/BEST at one worker; default CIXG1 and BEST CIXG2 at 1, 2, and 4
candidate workers; and materialized composition, predictor, and PPM route
controls. Every base/candidate archive compared byte-for-byte, and each trace
compared after replacing only per-candidate and aggregate timing values. Both
directions of fresh decoding restored the exact source bytes. The log contains
21 successful encoder cases, paired archive SHA-256 values, and the service
shell cgroup path before each encode/decode command. Descendant processes
inherit that service cgroup by systemd process-tree semantics; this packet does
not claim a direct binary-PID cgroup probe. Both decoders rejected a three-byte
bad-magic input. That is a malformed-magic check, not truncation or per-route
decoder coverage.

Commands executed by the unit are preserved verbatim in `run-parity.sh`.

## Focused checks

`focused-cixg-tests.log` retains the successful focused CIXG command, exit
status, and output. Its command is:

```
cargo test --manifest-path rust/cix-native/Cargo.toml --lib cixg_huffman_tests -- --nocapture
```

It runs both CIXG2 round-trip/CIXG1 rejection and forced-route raw-fallback
coverage. `full-lib-tests.log` is retained as an incomplete run: it passed the
recorded preceding tests, then the existing `encoder_fixtures_cross_decode_in_rust`
test remained active for more than five minutes and was interrupted
(`exit_status=130`). It is not claimed as a full-suite pass. `git diff --check`
passed.

`cargo clippy --lib -- -W clippy::too_many_arguments -W
clippy::cognitive_complexity` completed. It reports no `too_many_arguments`
finding for the extracted candidate trial functions. Clippy reports no Sonar
S3776 score; the locally installed `sonar-scanner` was not run because this
isolated worktree has no configured current analysis project or server receipt.
