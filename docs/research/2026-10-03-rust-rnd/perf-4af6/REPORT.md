# Current Rust DEFAULT CPU profile

Immutable source4af606b54, portable all-feature release-lto; Kennedy input
1,029,744 bytes SHA9af47239ca29dfe20e633f80bbbb9a4cc9783d0803d7b2b5626f42e4c3790420.
One current encode was profiled; no historical baseline encoding was restarted.

Complete archive: **82,984 bytes**, SHA
3d934dfd0cdc5621516cc0c3edbb0688ff5ec006b140206562e12fd79b609358,
identical to the retained earlier DEFAULT control. Fresh Rust decoding restored
all source bytes and SHA exactly.

`perf stat` wrapped `perf record` and the native CLI in one encode. It collected
227 cpu_core/cycles samples, zero lost samples. The instrumented native encode
was2.26s wall,2.23s user,.01s system,9,334,784B process peak RSS; decoder.01s,
6,029,312B RSS (GNU-time precision limits meaningful decoder speed claims).
Two physical CPUs8/10,200% quota, two requested encoder workers,512MiB CLI
working-memory admission; parent2GiB/no-swap,128MiB temporary bound. This does
not establish that all phases utilised both CPUs. Profiling overhead is included;
do not rank these times against historical uninstrumented or Squash timings.

| Sample share | Hotspot |
|---|---|
|33.63%|BigUint div_rem_cow; major call paths encode_type_class and choose/cardinality|
|14.52%|PPM observe_from|
|4.98%|BWT unstable sort|

Nested stat counters include profiler/launcher work:12,499,446,953cycles,
33,401,321,757instructions,3,587,301cache misses,57,626,177branch misses,
2376context switches,3CPU migrations. These locate work rather than prove a
cache, allocation or scheduling cause. The low sample count limits attribution.

A narrowly scoped optimization is queued from this evidence: remove unused
multinomial cardinality for existing range-mode type classes, and share the
already computed arbitrary-precision cardinality for rank mode. Byte parity,
thresholds, fresh decoding and same instrumented configuration must qualify
it. Exact ranks must remain arbitrary precision. No algorithm, selector,
history, model or block-boundary change is authorised by this profile.

The raw perf data remains outsideGit at benchmark-work/perf-4af6/perf.data;
report, counter CSV, full commands, GNU time, source/binary/configuration hashes
and actual child/cgroup receipts are sealed here. No claim about unsafe indexing,
SIMD, allocator replacement, LTO/PGO gains or universal throughput follows.
