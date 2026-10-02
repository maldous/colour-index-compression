# Rank warning cleanup

Base: `f6aa99c38344bb49dc575f166b25170e3063c540`.

Mechanical substitutions preserve integer predicates, Fenwick steps and arithmetic encoder construction. Exact ranks retain arbitrary-precision integers. Independent read-only review approved the source and focused evidence.

The recorded command passed 14 repeated test executions, including canonical count-range bytes, large ranks, context layouts and truncation rejection. This is focused correctness evidence, not a full current-release validation or a throughput claim. The memory peak includes compilation. Existing unrelated compiler warnings remain in the raw log. Only the actual Rust 1.98 host toolchain was checked; no older toolchain or other platform is claimed.
