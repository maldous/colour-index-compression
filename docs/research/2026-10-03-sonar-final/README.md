# Final local Sonar and Clippy inventory — a628bda23

Frozen source: commit `a628bda23e09bb43cceefa2d9e29009fbcc1df67`, tree
`74c5b9c90d1e554b1f87089b6a5a1c758630073b`. The final run uses a clean local
full clone at that commit. It scans the unchanged full scope: `rust/cix-native/src`,
`examples`, `tests`, and `benches`. It indexed 82 files: five more than 45e because
this revision adds the bounded-reader source/tool and three focused test files; the
scope itself did not expand.

`raw/scanner-r7.log` is the valid final upload: CE `SUCCESS`, 82 indexed files and
matching SCM revision. Its local clean project has 33 current open issues: 7 native
`rust:S3776` and 26 accepted external Clippy findings. The quality gate is `OK`; it
does not mean zero warnings. All issue objects and rule totals are retained.

The direct all-targets/all-features Clippy run exited zero and retained 245 Clippy
warning messages. `clippy-compact.jsonl` contains 40 unique first-party diagnostic
records for importer transport, keyed by rule, primary repository-relative span(s),
and message; it removes repeated target builds only. The raw report remains the
complete inventory. The final importer rejected 14 compact records: 12 invalid
locations in `lib.rs`/`main.rs` and two unsupported rules
(`chunks_exact_to_as_chunks`, `manual_isolate_lowest_one`). Those are unresolved,
not clean findings.

The valid scanner ran at CPU 24–25, `memory.max=1 GiB`, `memory.swap.max=0` as its
own in-container readback. The dedicated local server’s own receipt records CPU
24–25, 4 GiB, and zero swap. No credential value is retained; the final temporary
project token revocation returned HTTP 204. The raw Clippy run was separately capped
to CPU 24–25, 1 GiB and zero swap. No performance claim follows from this scan.

Failed setup logs remain: r1 could not resolve linked-worktree Git metadata; r2/r3
indexed zero files; r4 imported the raw duplicate target diagnostics; r5/r6 are
intermediate compact/receipt checks. They are not used for final counts. No source,
suppression, workflow, or scanner exclusion changed.
