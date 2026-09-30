# Track C — bounded experimental loop

`benchmarks/hutter_bounded_runner.py` is the small-screening execution boundary.
It accepts a declarative JSON manifest before the command is run.  Required fields
are hypothesis, matched control, input range plus SHA-256, configuration, mechanism,
budget, promotion criteria, separate encode/decode commands, artifacts and immutable
build paths.  The runner materializes the exact input range for encoding; the decode
phase receives only the archive/restored paths and runs with both original and
materialized input paths inaccessible.

An experiment identity hashes the complete manifest, source-range identity, declared
configuration/initial state and the SHA-256 of every declared build path.  A completed
receipt may only be reused when this whole identity matches and its independent
restored-byte hash verifies.  A cancellation tombstone is deliberately not reusable.

The initial policy uses CPUs 2, 4 and 6 as explicit, non-overlapping leases (one
runner process per CPU).  A nonblocking OS file lock rejects a conflicting lease.
Each child runs in its own systemd cgroup with `MemoryMax`, `MemorySwapMax=0`,
`KillMode=control-group`, affinity and single-thread numerical-library environment.
The runner samples cgroup memory and its dedicated temporary directory.  Each run
records 30-second JSONL progress records; uninstrumented `processed_bytes` is
explicitly `null`.

The runner refuses full 1,000,000,000-byte input and caps screening trials at five
minutes.  It snapshots and executes every directly invoked declared build file,
records final physical archive bytes and SHA-256, exact restored range hash, CPU,
sampled RSS/temp peaks, elapsed time and all failure reasons.  A result is only
`VERIFIED_SCREENING`: this is not promotion-ready.  It does run a separate decoder
from the physical archive, but larger staged validation remains required.  It never
stops from temporary output size.  Its output is research evidence, never a Hutter
score or qualification claim.

Track A and B commands should accept the placeholders `{workdir}`, `{source}`,
`{offset}`, `{length}` and `{receipt}`.  They must produce an archive and restored
range paths declared in `artifacts`; the runner, rather than the candidate, decides
whether the receipt is verified.
