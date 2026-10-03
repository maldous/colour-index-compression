# Independent adaptive segmentation: completed stage2/3

Frozen source `967c965dde6640039039a9a7b880ad5e3e1c0112f5c9de3c8ed75d95bbba5f3e`,
parent research `6c9758b9a709cb68057141afc0dcdca9f63f8664`, sealed native library
from production `d3a2cd416e49f93403d1dbd348a3e9a45db66ec6`. Production unchanged.

## Actual incumbent behavior

See current-audit.md for source/test references. Production chooses within
fixed frames/blocks (and separately some whole-archive candidates); it does
not discover arbitrary content-driven contiguous boundaries. M6 and CIXZ1
carry state that makes simple position-only DP invalid. Advertised nonzero
`--history` is rejected. No paid shared structural template wire was found.

The new physical trace on the 1,451-byte development changed-region input is
in raw/production-route-trace-cix_best-encode.stderr: CIXG2 emitted 1,024 and
427 byte blocks, choosing mixture (733-byte payload) and PPM (62-byte payload).
132 candidates, complete archive 931 B, fresh native restore SHA matched.
This verifies per-block selection on that path, not adaptive boundaries.

## Added isolated instrument

Four existing native routes: raw, Huffman, reset order0 adaptive, legacy LZ
at frozen effort1. No new codec. NativeCSC1 pays 17 global bytes (source
length/count/CRC included), then 9 bytes per segment plus each self-contained
payload, including its local metadata. Fixed-block boundaries are mandatory.
The adaptive bank scans matched 16/32/64-byte histogram/repetition changes,
keeps at most 17 endpoints spaced >=8 bytes, and always includes the unsplit
edge. Every admitted route is physically materialized; shortest path retains
endpoint and exact segment count <=32. Exact only within this declared bank,
route implementations, parameters and reset policy.

Nine small cases passed native exhaustive-partition comparisons (<=12 bytes)
and an independent Python DP over the measured route-minimum edge matrix.
All adaptive/all-cut reference gaps were zero. This is an independent
partition-selection check, not an independent implementation of the coders.

204 complete archives (including controls and production trace) restored in
fresh native child processes; nine malformed cases were rejected. Physical
accounting and input hashes were checked separately. Raw logs, metrics.json,
source/compiler/library hashes and artifact bindings make each cell repeatable.

## Complete bytes, frozen held-out seed

| Mechanism case | Whole | Fixed64 | Fixed256 | Fixed1024 | Adaptive | Current CIX BEST | Strongest declared control |
|---|---:|---:|---:|---:|---:|---:|---:|
| Homogeneous | 54 | 902 | 260 | 91 | 54 | 22 | 22 |
| Abrupt change | 867 | 1264 | 926 | 871 | **829** | 801 | 801 |
| Gradual change | 1080 | 1676 | 1234 | 1144 | 1080 | 917 | 917 |
| Short alternating regions | 1005 | 1466 | 1149 | 1053 | 1005 | 849 | 849 |
| A–B–A | 862 | 1240 | 921 | 866 | **819** | 758 | 751 zstd |
| Long crossing dependency | 1104 | 1792 | 1630 | 1585 | 1104 | 1086 | 1062 zstd |
| Interleaved noisy fields | 1094 | 1701 | 1388 | 1213 | 1094 | 903 | 903 |
| High entropy | 1575 | 1791 | 1629 | 1584 | 1575 | 1569 | 1563 zstd |

Development changed-region savings were 44 and 45 B; held-out savings 38 and
43 B. Other adaptive cells tie the unsplit result. All fixed-block controls
lose to unsplit on this bank; reset/header costs and cross-boundary dependencies
explain why fragmentation is not a goal. Full losses and external controls
are preserved. No result beats the strongest declared control at this stage.

## Actual discovered timeline: development abrupt

| Start | Length | Representation / coder | Shared model | Metadata | Payload | Complete segment |
|---:|---:|---|---|---:|---:|---:|
| 0 | 376 | bytes / Huffman | none | 9 | 70 | 79 |
| 376 | 644 | bytes / raw | none | 9 | 644 | 653 |
| 1020 | 431 | bytes / Huffman | none | 9 | 77 | 86 |

Sum 818 + global17 = **835 B**. Generated diagnostic boundaries were 379 and
1020; the compressor chose 376 and 1020 without receiving those labels.

## Resource evidence and scope

Batch wall195.196 s, CPU193.590 s; native candidate per-cell GNU peak RSS
<=8 MiB. Batch sampled cgroup high-water121,737,216 B is a sampled lower bound,
not a true peak. Active-work high-water5,586,881 B. Scheduler enforced one
CPU8/quota1, 2 GiB, swap0 and64MiB. All discovery, rejected route trials, internal
validation and fresh decode work are recorded; per-cell encoding and decoding
wall/CPU/RSS are separate in metrics.json. One observation/configuration;
no averages or imported performance rankings.

Offline encoder reads the entire bounded <=4096-byte input before emitting.
Its lookahead is input length, not a streaming guarantee. Decoder is also a
bounded standalone experiment, not an incremental production implementation.
Generalisation is limited to eight synthetic mechanisms at two frozen seeds
and varied lengths/alignment; no corpora or broader Silesia qualification.

## Attribution, prior art and next stage

This is established additive optimal partitioning implemented with measured
native costs and a bounded heuristic boundary bank. It is not new compression
theory or global optimality. Savings here are boundaries plus routing; there
is no retained state/model reuse. Candidate-generation omissions are separable
from DP errors, but the small reference controls reveal no omissions on their
own small cases and cannot certify medium-input optimality.

The evidence-selected next stage is paid decoded-prefix history, particularly
for A–B–A and long dependencies. A proof in history-proof.md states the narrow
condition under which history remains position determined; persistent adaptive
updates/template caches do not generally satisfy that condition.
