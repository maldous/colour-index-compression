# Remaining local encoder cost after native PPM

Two diagnostic profiles retained exact restoration: the first 65,536 bytes of
Mozilla, and a cloned live encoder checkpoint extended by 65,536 bytes then
finished. These are profiling probes, never full-file scores. They did not alter
the live benchmark state.

The warmed profile attributed about 6.9 of 29.2 instrumented encoder seconds to
4.99 million exact binomial calls, 6.1 seconds to periodic estimates and 8.2
seconds to LZ (overlapping cumulative times, not additive). The actual emitted
blocks depend on buffered checkpoint state and final flushing. This evidence
motivates generic arithmetic reuse rather than a source-specific model change.

An optional 8,192-entry cache stores exact coefficients only when n <= 4,096.
Integer-index validation is preserved. The focused property test passed all
coefficients for n=0..149 with a deliberately tiny eviction limit, invalid
arguments and bypass cases. On a separate same-checkpoint paired probe, encoding
fell from 44.41 to 37.86 seconds (14.8%). Both complete 3,604,480-byte prefixes
decoded exactly and produced the same compressed SHA-256. The cache recorded
4,517,309 hits and 1,148,601 misses, including verification activity.

This single probe ran under concurrent load and is not a speed-leaderboard claim.
The cache remains disabled in the main Silesia cohort while a four-complete-member
qualification runs in `results/leaderboard/runtime-comb-cache/`. The explicit
runner option is `--comb-cache`; it records settings and implementation hash.

The broader qualification subsequently passed all four complete-stream hash
comparisons and exact round trips. Aggregate encoding time was 68.90 seconds
cached versus 90.48 seconds uncached under concurrent load. All 84 tests passed
in 42.20 seconds; 28,670 additional exact coefficient comparisons covered the
entire cache domain and its bypass boundary. This qualifies the cache for the
unchanged byte policy, not a general speed-leaderboard claim.

After qualification, the nine remaining original Silesia workers were stopped
at recoverable checkpoints, confirmed absent, and resumed with `--comb-cache`.
The three verified members were preserved. The independent bounded-PPM trial
was not restarted or changed. Four-member measurements and accelerator hashes
are recorded in `2026-09-28-comb-cache-streams.json`.
