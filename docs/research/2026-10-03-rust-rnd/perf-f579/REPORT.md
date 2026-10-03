# Exact-arithmetic implementation optimisation

One matched, instrumented observation per configuration; no repeated averages.
The Canterbury Kennedy input is 1,029,744 bytes, SHA-256
`9af47239ca29dfe20e633f80bbbb9a4cc9783d0803d7b2b5626f42e4c3790420`.
Both use default effort, `--threads 2 --memory 512MiB`, CPUs 8 and 10,
portable release-lto, nested Linux perf stat/record and GNU time.

| Metric | Before 4af606b54 | After f579d8ac5 |
|---|---:|---:|
| Complete archive bytes | 82,984 | 82,984 |
| Encode wall seconds | 2.26 | 2.13 |
| Encode user CPU seconds | 2.23 | 2.10 |
| Encode peak RSS bytes | 9,334,784 | 9,363,456 |
| Decode wall seconds | 0.01 | 0.01 |
| Decode peak RSS bytes | 6,029,312 | 6,029,312 |

Observed encoding wall reduction: 5.75%. This is not a replicated or
uninstrumented speed claim. Decode timing is at GNU time's resolution.
The 28,672-byte RSS increase is observed, not evidence of a stable change.
Both archives have SHA-256
`3d934dfd0cdc5621516cc0c3edbb0688ff5ec006b140206562e12fd79b609358`;
fresh Rust decoder restoration equals the frozen input hash.

The change removes unused whole-type-class cardinality calculations for
mode-1 encoding, and shares arbitrary-precision cardinality work in ranking
and unranking. Integer precision, thresholds and format bytes are preserved.
Focused pre-change byte-equivalence and malformed-input tests passed in the
f579 audit packet. No algorithm, history or block-policy change is attributed
to this measurement. Rank source is unchanged in release 6ac05f8e9.

BigUint division remains the largest sampled hotspot. The cardinality subtree
fell from 8.03% to 3.79% of sampled CPU; sampling is descriptive, not a causal
allocation of every saved cycle. Raw samples and counters accompany the packets;
large perf.data artifacts remain outside Git in benchmark-work/perf-*.
The cgroup receipts prove affinity, memory and no-swap settings. CPU quota was
requested by the launcher, but these older receipts did not read back cpu.max
or cgroup path; do not infer that proof retrospectively.
No historical corpus baseline, Python reference or full-corpus run was restarted.
