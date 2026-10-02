# Shared pipeline test wait helper

The worker-failure test now shares its two identical deadline/Acquire-load/
yield/error loops. All original cancellation, sibling-liveness and join
assertions remain. This changes test structure only.

Seven pipeline integration tests passed under the directly invoked toolchain
and read-back 1 GiB/swap-disabled CPU8 cgroup. Raw script/log and source hashes
are retained. The recorded peak includes compilation and tests; it is not
production memory or throughput evidence. No algorithm, format, runtime
scheduler or resource default changed.
