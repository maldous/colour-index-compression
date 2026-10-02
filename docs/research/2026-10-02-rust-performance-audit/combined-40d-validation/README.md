# Combined native validation: 40d3520

This tracked receipt binds the readonly checkpoint artifact outside Git at
`benchmark-work/combined-40d-validation/final/` to frozen source
`40d3520db63a7d54526cb22430b769e77cf601c9` (tree
`a886902690ac5cd3b386cbac3498195925503fef`). It is a checkpoint, not a final
release.

The direct Rust 1.98.1 / LLVM 22.1.8 command used `--locked`, profile
`release-lto`, `CARGO_BUILD_JOBS=2`, CPUs 10 and 11, cgroup v2
`memory.max=2147483648` and `memory.swap.max=0`. The all-feature suite ran
once, serial test threads, and completed with exit 0: 40 test executables
reported 598 test executions passed, 0 failed, 0 ignored. This is not a count
of unique tests because library tests are intentionally repeated through bins,
integration targets and examples. Its cgroup peak was 1,659,342,848
bytes. The separate harness-free Criterion `ppm_borrow_kernel -- --test`
smoke completed exit 0 with encode and decode success and 573,554,688-byte
peak.

`raw/` contains copied textual build, suite and Criterion logs, exit receipts,
and readonly artifact metadata. `manifest.json` records both the capture paths
and hashes of those copied files. Binaries and input data remain outside Git.

The earlier 9214 epoch is deliberately distinct: its debug suite stopped at
the declared 1200-second budget (exit 143), and its optimized suite exited 101
in `numeric_encode_fixture` because the fixture decoder was a stub. Those
outcomes are preserved as failed historical receipts, not included in the 40d
pass total.
