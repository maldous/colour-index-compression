# v0.1 performance-release results

**Status: finite screen complete.** The bounded v0.1 performance screen has terminal receipts for every prepared cell. Its conclusions apply to the frozen 1,029,744-byte Kennedy input and the stated configurations only.

## Completed-build decision

Keep **B0**: portable `opt-level=3`, fat LTO, one code-generation unit, `target-cpu=x86-64`. B1--B5 all fresh-restored the frozen 1,029,744-byte Kennedy input and emitted bytewise identical FAST, DEFAULT, and constrained-BEST archives relative to B0.

| build / run | DEFAULT wall s | user CPU s | peak RSS KiB |
|---|---:|---:|---:|
| B0, first bound observation | 1.92 | 1.90 | 7,492 |
| B3, ThinLTO | 1.79 | 1.78 | 8,012 |
| B4, fat LTO / CGU16 | 1.79 | 1.78 | 7,984 |
| B5, host-native | 1.84 | 1.83 | 7,504 |
| B0 binary in A2 system screen | 1.83 | 1.81 | 7,244 |
| PGO held-out | 1.77 | 1.76 | 7,236 |

PGO appears 7.8% faster than the first B0 observation, but the unchanged B0 binary later measured 1.83 s. The difference overlaps observed run variation. Only one held-out PGO timing exists and the release queue prohibits repeats, so selecting PGO, ThinLTO, or host-native code would overstate the evidence. Manual SHA-256 comparison confirms PGO held-out FAST, DEFAULT, and constrained-BEST archives equal B0.

System allocator DEFAULT used 1.81 user CPU seconds and 7,244 KiB RSS; preload jemalloc used the same 1.81 seconds and 9,216 KiB RSS. Reject jemalloc.

## Completed scaling evidence

All CIXG1 scaling points produced the same 70,536-byte archive (`f1ec…227f`) and fresh-restored the input.

| policy | workers | wall s | user CPU s | peak RSS KiB |
|---|---:|---:|---:|---:|
| blocks | 1 | 1.91 | 1.87 | 19,968 |
| blocks | 2 | 1.11 | 1.91 | 19,968 |
| blocks | 4 | 0.65 | 2.12 | 19,968 |
| candidates | 1 | 1.89 | 1.85 | 19,968 |
| candidates | 2 | 1.08 | 1.92 | 20,028 |
| candidates | 4 | 0.71 | 2.10 | 19,712 |

Every CIXG1 block and candidate worker result has the same complete archive SHA-256 and the same restored-input SHA-256; the table is not inferred from timings alone. These frozen-input observations do not qualify a shipped-default change, decoder parallelism, or a general throughput claim.

The completed CIXG2 automatic-policy screen used **both** 16 KiB blocks and 256 MiB CLI memory, so it cannot attribute an effect to either variable separately. One worker completed in 1.84 wall / 1.83 user CPU seconds at 6,912 KiB RSS; four workers completed in 0.49 wall / 1.87 user CPU seconds at 8,924 KiB RSS. Both emitted and restored the same 102,668-byte archive (`37b920…64a9`).

The final CIXG1 one-variable controls isolate those settings at one worker:

| configuration | archive bytes | user / wall s | peak RSS KiB |
|---|---:|---:|---:|
| 64 KiB blocks, 512 MiB memory | 70,536 | 1.86 / 1.88 | 8,176 |
| 16 KiB blocks, 512 MiB memory | 102,668 | 1.84 / 1.85 | 6,912 |
| 64 KiB blocks, 256 MiB memory | 70,536 | 1.85 / 1.87 | 7,904 |

Every row fresh-restored. On this frozen input, 16 KiB blocks cost 32,132 archive bytes; lowering memory to 256 MiB leaves the archive unchanged. These are one-observation measurements, so they do not establish a universal throughput or memory policy change.

## Profiling probes

P1 (`perf record`) and P2 (`perf stat`) retained `perf_event_paranoid=4` receipts (exit 255). P4 reported disabled `lock:contention_begin` (exit 1). These are terminal unavailable observations under current host policy; no policy was changed. P3 completed its bounded `strace -f -c` probe and fresh-restored, but alone identifies no source change.

## Accepted exact-prefix prune

The sole additional release throughput optimization selected from this screen is the native whole-archive **exact-prefix prune**. A CIXG or CIXM6 trial appends immutable archive bytes. Once that prefix exceeds the current incumbent archive length, the candidate cannot win; the trial is stopped and recorded as a distinct prefix omission. Equal-length output remains materialized, preserving strict tie order. This is an exact monotonic size bound, not a heuristic, profile reduction, or deadline omission.

The matched before/after harness passed on two fresh-restored cases with identical selected archives and no actual deadline omission:

| case | archive bytes | before user / wall s | after user / wall s |
|---|---:|---:|---:|
| `grammar.lsp` native BEST | 1,096 | 10.14 / 10.17 | 10.22 / 10.24 |
| Kennedy constrained predictor | 79,507 | 1.18 / 1.19 | 1.07 / 1.08 |

These are single observations. They demonstrate output equivalence and the new omission accounting; they do not establish a general speedup. Unit/integration testing passed (115 unit, 4 CLI smoke, 7 streaming-pipe tests), Clippy passed, and the independent review accepted the change. The earlier no-source-change conclusion is superseded only by this prune and the previously accepted T1 M6 discarded-histogram avoidance; no other optimization is selected.

## Terminal screens and limits

`S-M6` exhausted its 300-second wall budget (300.95 wall / 300.02 CPU seconds) before producing a complete archive. It is explicitly **incomplete and unranked**, rather than evidence against the format.

The private A1 audit completed: 118,793,993 total allocated bytes across 59,593 allocations, with a 13,515,278-byte peak across 24 live allocations. The largest sites are fixedmix hash-table growth and rank/`num_bigint` work in the standalone audit path. The native cost result has fixedmix v3 payloads of 17,590 and 17,588 bytes versus v1 at 17,466 bytes; the audit does not measure complete archives. Neither result supports a release-path allocation rewrite.

Retain portable B0, do not retain PGO, and do not add jemalloc. Profiling permission and tracepoint limits remain documented above.
