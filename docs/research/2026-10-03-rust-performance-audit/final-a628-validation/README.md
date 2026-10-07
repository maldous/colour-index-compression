# Interim combined native checkpoint: a628bda23

Immutable source revision `a628bda23e09bb43cceefa2d9e29009fbcc1df67`, tree `74c5b9c90d1e554b1f87089b6a5a1c758630073b`. This exact source freeze was tested successfully. It is an **interim** host-resolved readonly release-LTO checkpoint: the later Sonar findings are pending source fixes and a new freeze.

The direct stable Rust 1.98.1 toolchain built `cix`, `uncix`, `cixcat`, and `libcix_native.so` with `--locked --all-features --profile release-lto -j2`, CPU affinity 10,11, `memory.max=2147483648`, and `memory.swap.max=0`. Build exit was 0; its cgroup peak was 1187340288 bytes. The optimized all-feature lib/bin/integration/example suite exited 0 with a 1719988224-byte peak. Cargo emitted 44 successful result groups totaling 748 passed test executions, summed from each result line's `N passed` field. These are repeated executions, not unique test names. The log has 44 `running N test(s)` headers totaling the same 748. An earlier plural-only parser missed six singular `running 1 test` headers; this was a counting bug, not missing log output.

The separate Criterion `ppm_borrow_kernel -- --test` smoke exited 0 in its own equally constrained scope, with a 492560384-byte peak. Its raw output identifies both default random encode/decode cases as successful.

`raw/` contains copied textual build, suite, Criterion, cgroup, child-membership, command, source, fingerprint, checksum, and metadata receipts. `raw/manifest.sha256` binds those copies. The readonly binaries and metadata remain outside Git in `benchmark-work/final-a628-validation/final/`.
