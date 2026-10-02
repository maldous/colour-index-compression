# CIXG1 default-effort scaling qualification

Generated from 120 retained native receipts.

Forty one-thread cells produced a physical archive, decoded through native `uncix`, and exactly restored the source byte count and SHA-256. The 80 requested two- and four-thread cells are retained as `FAILED`: their decoder emitted `--threads >1 applies to native CIXG1/CIXG2 block or candidate selection`, returned zero, and did not produce a restored file. They are not decoder scaling evidence.

This is a concurrent-host screen on CPUs 28–31. It measures default effort only: no `--fast`, `--best`, CIXM6 persistent-history, or 1..20 scaling result is asserted. CIXG1 routes rejected `--history`; its `--independent-blocks` flag is an idempotence control because CIXG1 framing is already independent.

`results.json` lists median encode/decode wall nanoseconds, native sampled decoder thread maxima, effective affinities, cgroup MemoryMax and MemorySwapMax, archive sizes, and verification by input/thread/control.
