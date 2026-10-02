# Host and counter protocol

Capture `lscpu --extended`, `lscpu --cache`, `numactl --hardware` when
available, current CPU affinity, `/sys/devices/system/cpu/cpu*/topology`,
kernel, rustc and Cargo before each immutable plan. The harness writes the
portable subset automatically in `environment.json` and chooses only distinct
physical cores for one single-file scaling experiment.

This host exposes hybrid CPU PMUs. Record the physical CPU set and core type
for every measurement. Do not combine core classes in a single scaling curve
unless the split is explicit. Run a clean, pinned single-file trial for perf;
concurrent dataset jobs are valid corpus throughput measurements but invalidate
microarchitectural attribution.

`perf` has been checked locally through `sudo -n perf stat` for cycles,
instructions, cache misses and branch misses. The normal unprivileged paranoid
setting is restrictive, so retain the exact command and privilege outcome in
the evidence. `cargo-flamegraph`, Valgrind and Heaptrack are not assumed to be
installed. `perf record` plus `perf report` is the baseline CPU attribution
method; DHAT is an audit-only instrumented build if allocation profiling is
needed.

CIX currently accepts at most 20 workers even when the host exposes 24 logical
CPUs. The generated environment records that implementation limit and the
visible CPU topology/capacity fields. A logical-core result above 20 is an
explicit implementation gap, not a missing benchmark point.
