# Track C integration control — direct zstd 19

This is a harness integration control, not a CIX gain and not promotion-ready.

On the fixed 65,536-byte enwik9 development range at offset zero, pinned direct
zstd level 19 produced a 23,182-byte physical archive.  Separate archive-only
decode restored SHA-256 `05fc5f44993ef0557959db76bf47e45badb2dd9c69d93ce08911935b5e52bf40`.
The immutable screening receipt is
`track-c-results/e261c9056de2b435fdd9c6a33111c16630742a209f0048debf803b6e59ea7261/receipt.json`.

The uncached encode/decode phase wall times were 0.1323 s and 0.1271 s.  A second
identical invocation reused the artifact-rehashed receipt in 0.0250 s wall time;
it did not run compression.  CPU was pinned to 6 with a 1 GiB cgroup cap, zero
swap and a 300-second shared deadline.  Memory values in the receipt are sampled
cgroup high-water lower bounds, not process-RSS peaks.
