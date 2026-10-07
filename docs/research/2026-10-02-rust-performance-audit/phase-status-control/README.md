# Direct process-status receipt for the performance audit

Four tiny local controls reproduced the transient supervisor defect: requested
exit codes `0,2,0,2` were all reported as zero. This is a harness issue; the
Rust CLI correctly exits nonzero for rejected options. No old failed record
is upgraded by the repair.

The audit now runs each requested phase through a small in-cgroup supervisor
which atomically writes the actual child command and exit status before exiting.
The phase requires a fresh matching receipt, includes its SHA-256 in evidence,
and preserves an outer resource failure even if the child exited normally.
The new helper is part of the audit's frozen implementation hashes. The shared
historical R&D supervisor was not changed; future runs need a new audit identity.

Actual cgroup controls passed for `0,2,0,2`, a missing executable (127), and a
signalled child (-15). Deterministic injection also rejects missing, mismatched
and stale receipts, and preserves an outer failure after child success.
`before.json`, `after.json` and `manifest.json` retain results and source hashes.
The supervisor uses inherited standard streams and no whole-output buffering.
Native GNU Time still measures the requested native command; outer phase wall
time includes the receipt supervisor equally for both compared releases.
