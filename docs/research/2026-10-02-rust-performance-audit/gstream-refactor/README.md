# `gstream.rs` bounded refactor

This evidence records a control-flow-only refactor of the native independent-frame streaming encoder. `StreamState` owns bounded reader state; helpers drain ordered completions and wait for pipeline capacity. The worker selection closure, output frame writes, cancellation, flush deadline calculation, format choice, and resource values are unchanged.

The isolated `run_probe.py` imports the frozen probe implementation and changes only the audit binary paths and CPU affinity. It does not modify the canonical benchmark runner.
