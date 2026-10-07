# Combined validation: 55aac92

This packet preserves the successful immutable host checkpoint at source
`55aac92a13fc0d068fbc359a3f8afdb7d6bf48e3`, tree
`3ca41edf7ffb4c7d8701d08c7dc06f0e260f17cc`. `raw/` contains copied build,
suite and Criterion logs, actual exit receipts, and readonly source/build/DSO
metadata. No binary or input data is tracked here.

The direct-toolchain release-lto all-feature suite exited 0 under the 2 GiB,
no-swap cgroup. Forty test executables reported 652 passing test executions;
this is not a unique-test count because aliases and examples repeat tests. The
separate `ppm_borrow_kernel -- --test` Criterion smoke exited 0. This is a
readonly checkpoint, not a final release.
