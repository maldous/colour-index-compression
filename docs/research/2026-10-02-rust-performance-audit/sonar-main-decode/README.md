# Main decode Sonar refactor

The first bounded decode split moves CIXM6 integer varint/Rice decoding and record-lane reconstruction into private helpers. Byte framing, memory admission, cancellation polling, history, and error text remain in their existing owners.

## Independent review scope

Source helpers, Rice bounds and offline archive parity/restoration are reviewed.
The corrected `raw/m6-pipe-probe.py` snapshots output and process liveness
before closing the producer: 4096 bytes restored before EOF; final 8192 bytes
restored exactly. The prior post-EOF-length calculation is INVALID_MEASUREMENT
and is retained solely as a failed attempt. The header-only probe does not
establish incremental reconstruction. CIXG1 idle receipts are separate controls.

M6 probe resource settings are NOT QUALIFIED: CPU affinity was applied, but
child cgroup membership, memory.max and swap readbacks were not retained.
Any earlier 1 GiB/no-swap fields describe configured or asserted settings, not
verified per-child enforcement. No peak-memory, throughput, idle partial-flush
or general profile improvement is inferred from this correctness check.
