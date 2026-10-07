# CIXG1 default-effort raw scaling screen — provenance incomplete

Generated from 120 retained native receipts.

Independent review found that the exact Python harness source executed during
these trials was not retained or hash-attested. The committed runner at
`4023fd656` could not generate the retained manifest state values or wrapper
exit behavior. `112c889148` repairs a post-trial source version for future
identities; it is not the source that ran these trials. Therefore this packet
is a raw-command/archive screen, **not reproducible harness qualification**.
Immutable codec/input hashes, actual command lines, native metric files and
archive hashes support the observations below but do not cure this limitation.
All timing rows are explicitly unqualified; failed decoder durations are
omitted from the summary. Do not use this packet for release recommendations.

Forty one-thread cells produced a physical archive, decoded through native `uncix`, and exactly restored the source byte count and SHA-256. The 80 requested two- and four-thread cells are retained as `FAILED`: their raw native decoder metric records exit 2 and stderr `--threads >1 applies to native CIXG1/CIXG2 block or candidate selection`; no restored file exists. `execute_phase` recorded wrapper exit 0, so native metric exit codes are authoritative. They are not decoder scaling evidence.

Raw retained encode command lines confirm `--independent-blocks` was supplied for every independent control. A post-trial runner defect would omit that flag if it consumed a later descriptive state string; it does not alter the frozen trial commands. The corrected runner uses the frozen machine-readable `mode`, and any future run requires a new identity.

This is a concurrent-host screen on CPUs 28–31. It measures default effort only: no `--fast`, `--best`, CIXM6 persistent-history, or 1..20 scaling result is asserted. CIXG1 routes rejected `--history`; its `--independent-blocks` flag is an idempotence control because CIXG1 framing is already independent.

`results.json` lists median encode/decode wall nanoseconds, native sampled decoder thread maxima, effective affinities, cgroup MemoryMax and MemorySwapMax, archive sizes, and verification by input/thread/control.
