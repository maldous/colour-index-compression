# CIX hotspot audit runner preflight

This packet prepares the post-cleanup hotspot profiling runner. It does not
profile a release, dispatch a corpus job, or create a scheduler pool. The
cached CCA inputs and a qualified immutable release are unavailable in this
checkout, so no fabricated release/input binding is retained.

`benchmarks/cix_rust_hotspot_audit.py prepare` will bind one existing immutable
CCA plan row and its input SHA-256 to an immutable `native-release.json` and
both binary hashes. It writes only a preflight JSON. The planned P-core and
E-core runs use CPU 8 and CPU 16 separately. `taskset -c CPU` precedes `perf`
itself, so perf opens counters after affinity is applied rather than aggregating
hybrid-core samples.

Required `perf stat` events are cycles, instructions, cache misses, branch
misses, context switches, and CPU migrations. It also prepares `perf record`
with DWARF call chains. `perf lock` and `strace -c` I/O attribution are
conditional: unavailable tools, kernel permissions, or unsupported counters
become explicit receipts rather than zero metrics. DHAT and assembly inspection
remain unavailable until separately frozen audit artifacts and a demonstrated
hotspot exist.

The `run` operation requires all of: `--execute`, a freeze object with status
`QUALIFIED_RELEASE_FROZEN` exactly matching the release/binary binding, and an
existing active WaveScheduler claim and lease that exactly bind this preflight,
its release and task, CPUs 8/16, their current physical-core identities, all
requested phases, a 1 GiB per-profile limit, 12 GB aggregate limit, and zero
swap. It executes one CPU profile at a time beneath a read-back systemd cgroup (`CPUAffinity`, 1 GiB max memory, zero
swap); the wrapper captures its cgroup, resource values, child exit status,
command argv, and profiler logs. It intentionally does not manufacture a new
scheduler or bypass the aggregate budget.

## Dry-run validation

`raw/unit-test.raw` records two local tests: prepare validates fixture and
release identities and produces no raw profile output; run refuses without
`--execute`. `raw/host-preflight.raw` records the actual availability of CPUs
8/16 and profiler tools on this host. This metadata is not a profiling result.
