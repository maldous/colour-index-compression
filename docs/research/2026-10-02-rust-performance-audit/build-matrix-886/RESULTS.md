# 886 compiler candidate replication

This is a **concurrent-host screening**, not an isolated-host qualification.
Other disjoint-core research was active. The source was frozen at
`8865bfbccba354b02920da86c7088c17e5f96aab`; the readonly integrated artifact
and every resolved runtime DSO were SHA-256 rechecked before and after the
trial. Their hashes are recorded in `artifact-baseline.json`.

Each build used only CPUs 20 and 22, one Cargo job, a transient user cgroup
with `MemoryMax=2,000,000,000` and `MemorySwapMax=0`. The two persistent build
receipts are `/tmp/cix-buildmatrix886-cgu1-retry/{launcher.log,build.stderr}`
and `/tmp/cix-buildmatrix886-cgu16/{launcher.log,build.stderr}`. Both exited
zero. GNU time measured 623,432 KiB peak RSS for CGU 1 and 526,132 KiB for CGU
16. The completed candidate builds plus stored measurement archives occupied
169,146,102 bytes, under the 512 MB temporary cap.

Five counterbalanced repetitions ran ordinary FAST, ordinary DEFAULT, and a
CIXG1/LZ-constrained BEST check. All complete archive bytes were identical
between CGU 1 and CGU 16. Thirty owning decodes and sixty fresh cross-build
native decodes restored the frozen input hashes exactly.

| Workload | CGU 1 encode s (σ) | CGU 16 encode s (σ) | CGU 1 decode s | CGU 16 decode s | archive bytes |
|---|---:|---:|---:|---:|---:|
| FAST / kennedy.xls | 0.03739 (0.00180) | 0.03749 (0.00166) | 0.00812 | 0.00819 | 122,333 |
| DEFAULT / kennedy.xls | 4.82461 (0.22308) | 4.74373 (0.16610) | 0.00771 | 0.00753 | 82,984 |
| BEST CIXG1/LZ / grammar.lsp | 0.04129 (0.00126) | 0.04158 (0.00154) | 0.00923 | 0.00928 | 1,443 |

CGU 16's DEFAULT mean is 1.7% lower, but its uncertainty overlaps the baseline
and it offers no FAST or constrained-BEST gain. It is not retained as the
portable default. Its `cix` binary is 2,572,032 bytes, 1.1% larger than the
2,544,088-byte CGU-1 build.

## Disjoint PGO check

Rust PGO trained only on generic cached `alice29.txt` (FAST) and `book1`
(DEFAULT); the three timing cases were held out. Eight raw profiles were merged
using the Rust toolchain's matching LLVM 22 `llvm-profdata`. This instruments
Rust code only, not the vendored BSC/ZPAQ C++ code. The PGO temporary peak was
286,041,937 bytes, under the same 512 MB cap. The PGO runner completed only if
every produced archive decoded exactly in both freshly launched baseline and
PGO decoders.

| Held-out workload | baseline encode s (σ) | PGO encode s (σ) | baseline decode s | PGO decode s | archive bytes |
|---|---:|---:|---:|---:|---:|
| FAST / kennedy.xls | 0.04142 (0.00170) | 0.04019 (0.00135) | 0.00997 | 0.00972 | 122,333 |
| DEFAULT / kennedy.xls | 5.13318 (0.02638) | 4.97556 (0.03664) | 0.00950 | 0.00988 | 82,984 |
| BEST CIXG1/LZ / grammar.lsp | 0.04708 (0.00024) | 0.04690 (0.00079) | 0.01134 | 0.01113 | 1,443 |

PGO improves the held-out DEFAULT encode mean by 3.1% and FAST by 3.0%, without
changing compressed bytes. DEFAULT decode regressed 4.0% in this sample; the
short BEST timing is within its dispersion. The profile-guided build is 2,389,520
bytes, smaller than the same-build baseline, but no deployment conclusion is
drawn from that code-layout outcome. PGO remains experimental pending the full
frozen CCA gate and separate isolated-host replication.

No compressor algorithm, route, history, framing, block policy, selector, or
portable build default changed. The required PGO and CGU source scripts, frozen
inputs, individual samples, hashes, wall and CPU timing, and peak RSS are in
`plan.json`, `results.json`, `pgo-freeze.json`, and `pgo-results.json`.

## Resource receipt limitation

Independent review verified source/build/input/archive identities and fresh decode
checks. The transient cgroup had already exited; retained launcher logs record
unit IDs but do not retain an in-scope readback of `memory.max` and
`memory.swap.max`. The declared 2 GB/no-swap launch configuration therefore
cannot be independently reconstructed from those logs. GNU Time preserves
build RSS, exits and zero reported swaps. This is screening evidence, not
resource-qualified performance evidence. Future trials must retain cgroup
readbacks while the scope is alive.
