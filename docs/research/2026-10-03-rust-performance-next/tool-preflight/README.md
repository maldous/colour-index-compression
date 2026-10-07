# Local tooling preflight

This is infrastructure validation only, not a CIX benchmark. `perf_event_paranoid`
is 4; privileged local perf nevertheless collected cycles, instructions, cache
misses and branch misses for `/usr/bin/true` pinned separately to P CPU8 and E
CPU16. Raw commands/results are retained. Nonselected hybrid PMU entries are
not counted; profiling must use the selected core type rather than combining
those entries as missing counters. No system setting was changed.

`perf` is version 6.8.12. The stable Rust toolchain supplies llvm-profdata at
`/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/bin/llvm-profdata`.
No cargo-flamegraph executable was found in PATH; perf recording/reporting
remains available. Actual CIX profiling awaits the qualified release and a
scheduler lease, and no throughput/cache conclusion follows from this check.
