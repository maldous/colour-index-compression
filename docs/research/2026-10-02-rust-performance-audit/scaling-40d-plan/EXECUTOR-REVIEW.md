# Scaling executor review packet

Status: `FROZEN_NOT_DISPATCHED`. This packet describes code only; it contains
no corpus measurement and no cleanup gate.

The executor accepts only a plan created by
`benchmarks/cix_rust_scaling_audit.py`, then verifies all of these before it
can create a results directory:

- a root-created JSON gate has `authorize_dispatch: true` and hashes the exact
  plan bytes;
- the harness, existing phase executor, child-status supervisor, and shared
  scheduler hashes still match the frozen plan;
- the release metadata, source revision, executable hashes, and host-resolved
  runtime DSO hashes are unchanged;
- the aggregate policy remains one job, 12,000,000,000 bytes RAM,
  4,000,000,000 bytes temporary space, and swap maximum zero.

It takes the existing `WaveScheduler` global lock, leases the required
physical cores for each serial cell, and invokes the existing
`cix_rust_perf_audit.execute_phase` wrapper for encode and decode. That wrapper
uses `cix_phase_receipt.py` to preserve the real child exit status. The phase
command records the cgroup cpuset, memory maximum, and swap maximum inside the
child. The native restoration uses exactly `--threads 1`; all requested
encoder thread counts retain that decode setting.

The only executable containers are CIXG1 and CIXG2 with explicit
`--history 0`, `--parallelism blocks`, and `--independent-blocks`. CIXM6 has no
cell because a concrete persistent-history route and window remain unproved.
The first failed or unqualified cell is written as a receipt and stops the
run. It is never converted into another mode or retried by this executor.

Local checks:

```text
python3 -m unittest tests.test_cix_rust_scaling_audit
python3 -m py_compile benchmarks/cix_rust_scaling_audit.py
```

`executor-tests.log` and `executor-test-receipt.json` retain the actual local
unit/mock command, zero exit, and hashes of the harness, test file, and log.
They cover recursive cell-directory creation and retained `UNQUALIFIED`
receipts when the phase runner raises. They do not execute a codec benchmark.
