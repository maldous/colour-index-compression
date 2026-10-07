# Scaling audit harness plan

`benchmarks/cix_rust_scaling_audit.py` freezes a plan by default. Dispatch
requires a root-created JSON cleanup gate whose `plan_sha256` exactly matches
the immutable plan and whose `authorize_dispatch` is true. The executor uses
the existing global `WaveScheduler` lock and physical-core leases, then the
existing `cix_rust_perf_audit.execute_phase` direct-child receipt wrapper; it
does not create another pool or raw subprocess path. The plan fixes native artifact, inputs, DSOs, profiles
FAST/DEFAULT/BEST, requested encoder threads 1/2/4/8/12/16/20, block/history/
memory controls, and complete archive plus fresh native restoration checks.

Decode is deliberately invoked with one thread. Current CLI rejection of
higher decoder thread settings is retained as a rejection result; this plan
makes no parallel-decode performance claim. CIXG1 and CIXG2 cells are explicit
history-zero independent containers. CIXM6 is recorded as container-capable
but `UNSUPPORTED_UNPROVEN`: no selected persistent-history route/window has
been established, so it has no scaling cell. Aggregate caps are 12 GB RAM,
4 GB temporary storage and no swap. The executor stops and retains the first
unqualified cell rather than substituting a mode or retrying a measurement.
