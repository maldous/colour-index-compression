# Compiler build-matrix results

Source revision: `15426f310f40b9a3d753313741c28e718f7aceb6`.
Toolchain: Rust 1.98.1 / LLVM 22.1.8 on a 13th-generation i9-13900K host,
Linux 6.8.0-138. Each process was pinned to CPUs 20 and 22, limited to 2 GB
virtual address space, and benchmarked five times. Input identities, toolchain,
commands, compiler flags, output hashes and individual timing/RSS samples are
in [freeze.json](freeze.json), [results.json](results.json),
[pgo-freeze.json](pgo-freeze.json), and [pgo-results.json](pgo-results.json).

All six normal builds produced the same complete archive bytes for every
workload. Their 90 own decodes and 540 fresh cross-build native decodes restored
the frozen input SHA-256 exactly. This establishes code-generation compatibility
for the exercised CIXG1 and automatic FAST/DEFAULT paths; it does not replace
the full CCA gate. The six measured build directories totalled 497,385,775
bytes, below the 1 GB cap.

| Build | Compile s | cix bytes | FAST encode s | DEFAULT encode s | constrained BEST encode s |
|---|---:|---:|---:|---:|---:|
| portable opt3 fat LTO, CGU 1 (current policy) | 66.792 | 2,523,288 | 0.04019 | 5.82614 | 0.05426 |
| portable opt2, no LTO, CGU 16 | 58.076 | 2,963,496 | 0.04064 | 6.14508 | 0.06061 |
| portable opt3, no LTO, CGU 16 | 59.260 | 2,931,712 | 0.03888 | 5.69113 | 0.05658 |
| portable opt3 ThinLTO, CGU 16 | 64.667 | 2,857,232 | 0.03976 | 5.46064 | 0.05209 |
| portable opt3 fat LTO, CGU 16 | 60.722 | 2,553,472 | 0.03768 | 5.33003 | 0.05129 |
| native opt3 fat LTO, CGU 1 | 66.891 | 2,603,552 | 0.03885 | 5.40039 | 0.05011 |

The portable fat-LTO/CGU-16 candidate was 8.5% faster on DEFAULT and 6.2%
faster on FAST than the current portable CGU-1 policy, with a 1.2% larger
`cix` executable. Its decode means were also no worse on these inputs. This is
a measured candidate, not a retained production setting: the matrix is a
screening experiment and must first pass the complete frozen CCA gate and the
end-to-end throughput/parallelism audit.

`target-cpu=native` did not beat the portable CGU-16 candidate on these
workloads, and produces a host-specific executable. It is therefore not a
deployment recommendation.

## PGO held-out replication

PGO trained only on distinct cached inputs `alice29.txt` (FAST) and `book1`
(DEFAULT); all timing inputs above were held out. The matching LLVM 22
`llvm-profdata` merged eight generated profiles. The PGO build instruments only
Rust: vendored BSC/ZPAQ C++ is outside this experiment. Five counterbalanced
held-out repetitions, with fresh baseline and PGO decoder cross-checks, were:

| Held-out workload | baseline encode s | PGO encode s | baseline decode s | PGO decode s | archive bytes |
|---|---:|---:|---:|---:|---:|
| FAST / kennedy.xls | 0.03849 | 0.03708 | 0.00924 | 0.00879 | 122,333 |
| DEFAULT / kennedy.xls | 5.50899 | 5.33417 | 0.00891 | 0.00848 | 82,984 |
| BEST constrained CIXG1/LZ / grammar.lsp | 0.05152 | 0.05112 | 0.01077 | 0.01040 | 1,443 |

This PGO profile improved held-out DEFAULT encode time by 3.2% and FAST encode
time by 3.7% without changing archive bytes. Its decoder result is promising,
but its absolute timing is short. Keep PGO experimental until it reproduces on
the broader CCA gate and a separate held-out set. The normal matrix result is
the stronger immediate build-configuration candidate.

No algorithm, route, selector, history, block-boundary, format, or streaming
change was made in this audit. The BEST result is explicitly route/container
constrained and must not be presented as an unconstrained compression-ratio
result. These samples also do not characterize multi-thread scaling, external
backend execution, cache-miss behavior, or the remaining allocation and
hot-kernel profile work.

The PGO run emitted eight raw profiles and its measured temporary peak was
285,394,545 bytes, below the 1 GB cap. Its PGO binary was 2,366,096 bytes,
6.2% smaller than the portable fat-LTO baseline, but that is an experimental
profile-guided code-layout result, not a release-size promise.
