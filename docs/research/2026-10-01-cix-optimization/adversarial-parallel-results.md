# Native review, parallelism and DEFAULT selection checkpoint

This checkpoint implements and locally verifies corrections found during parallel
adversarial review. It is method development on already verified Dickens ranges
and synthetic correctness fixtures. It does not renew Silesia qualification,
rank against imported Squash CPU times, or establish exhaustive BEST search.
All jobs were local; no acquisition, Actions or public publication occurred.

## Implemented corrections

- Independent CIXG blocks use a persistent ordered worker pool. Outstanding
  work, including completed out-of-order results, is bounded by worker count.
  Scratch permits are shared. Candidate workers do not nest inside block workers.
  Slow output stops additional source admission. Input buffers are reused.
- Worker errors, panics, cancellation and SIGINT/SIGTERM cancel remaining work.
  Interrupted file operations remove incomplete temporary archives. The footer
  is emitted only after ordered drain and successful worker join. Unix stdout
  handles partial nonblocking writes, downstream stalls and cancellation.
- Route/backend overrides honor compatible dimensions and reject contradictions;
  raw fallback carries route 0. Trial deadlines use remaining search time.
  Winners are copied into exact-capacity payloads before scratch release.
- Decoder admission sums frame payload, reconstructed bytes and route scratch,
  including nested context tables. CIXG1 rejects CIXG2-only payload variants.
  Exact combinatorial ranks retain arbitrary precision.
- Serial CIXM6 retains bounded causal history and adaptive state. History pruning
  avoids capacity growth. Parallel CIXG blocks explicitly reset models.
- Corrected experimental recurrence uses mixture payload v3/config v2; defective
  prototype v2 decoding remains available. It has not been selector-promoted.
- Fixed-mix per-bit scratch arrays replace heap vectors; history uses a bounded
  circular buffer. Encoder/decoder model order and deterministic bytes remain
  unchanged. A counted-allocation regression passed.
- DEFAULT's cheap prediction signal now admits affordable PPM before the route
  cap. Policy v2 requires prediction rate >0.1 and at least 64 causal prediction
  opportunities. FAST and BEST policy breadth are unchanged; duplicate detection
  remains eligible even when byte entropy is high.
- An omitted FILE now means stdin. `--` permits dash-prefixed names. `-c` with a
  named `-o` is rejected instead of silently ignoring the output name. Help
  describes the supported single optional input. Multiple named inputs remain
  a CLI gap.

Original isolated Python validation reference: `80b95427725ecf59d626b2982d50f6349abd56e1`; see [reference freeze](../2026-10-01-rust-native/REFERENCE.md). It does not constrain new native-format R&D.

Source identities: initial review/pipeline `90e457277dcb80b1ff713413b07a8c904bb660df`;
DEFAULT v1 `2b26cc074370c4db9c13c4dd0471a2f37f16443e`; mixer scratch
`08711c49659ddddb73e5f19b34bf29d50845e3d2`; stdin/confidence v2
`ee6b4396df760d19005c4e0800783fef58d52334`.

## Measurement method and inputs

Release binaries use Rust 1.98.1 and full LTO with one codegen unit. Hardware is
an Intel i9-13900K, Linux x86_64. Each cell used one existing WaveScheduler
lease on distinct physical CPUs 16,17,18,19; aggregate limits are four cores,
decimal 12 GB RAM and 4 GB temporary space with no swap. Cells ran serially.
Each encoder and archive-only decoder was a fresh native process. GNU `time`
provides wall, CPU and process max RSS; sampled cgroup memory is a lower bound,
not a replacement for RSS. Model/cache state and other host activity were
uncontrolled. No throughput figure is compared to public Squash CPU time.

Full Dickens: 10,192,446 bytes, SHA-256
`b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.
Frozen development range: first 1 MiB, SHA-256
`afd479dd0e0339643530bf4ee3d10423265c515a06e7994bbe26ccba39aea9ab`.
Disjoint replication range: offset 1 MiB, length 1 MiB, SHA-256
`383e24c3b09f6be8ff1445febf9828ae71cf41bfbfaeffddf5d38dda3a143364`.
Mixer control: first 128 KiB, SHA-256
`20e33fcc8faa96dc32a2d0921115c0f363e64c598a5847ce1a3876e356d59872`.
These are historically exposed development bytes, not unseen holdouts.

## Ordered block parallelism: fixed PPM mechanism control

Source 90e457277, first 1 MiB, two repetitions per setting. Command constraints:
`--best --route ppm --format cixg2 --block-size 64KiB --memory 2GiB`
plus declared workers/parallelism. This isolates scheduling on the same legal
candidate set; it is not ordinary AUTO performance.

| Workers / scheduling | Archive bytes | Encode wall, s | Encode CPU, s | Encode max RSS, KiB | Decode wall, s |
|---|---:|---|---|---|---|
| 1 / candidates | 354,023 | 8.11, 8.10 | 8.09, 8.09 | 38,612, 38,728 | 0.61, 0.61 |
| 1 / blocks (serial) | 354,023 | 8.16, 8.11 | 8.15, 8.10 | 40,312, 38,948 | 0.61, 0.59 |
| 4 / candidates | 354,023 | 3.41, 3.38 | 9.12, 9.16 | 113,492, 104,080 | 0.61, 0.61 |
| 4 / blocks | 354,023 | 2.57, 2.56 | 9.56, 9.61 | 138,304, 138,292 | 0.60, 0.61 |

All eight archives have identical SHA-256
`6db100d63e208c80377d083deaa75dfee1c2df752925ef677df6fbdac1833dbf`;
all restored exactly. Each evaluated 144 candidates, with zero budget/memory
omissions. Four block workers averaged 0.390 MiB/s versus 0.123 MiB/s for one
candidate worker: **3.16x observed wall speedup**, about 24% less wall time than
four candidate workers. CPU work rose about 18.5%, max RSS about 38 to 135 MiB;
average utilization was 3.74 cores versus 2.69 for candidate scheduling.
This is a speed/memory tradeoff, not a size gain. Summed per-worker search time
is not elapsed wall time. [Complete measurements](adversarial-parallel-evidence/cix-parallel-qualification/qualification-summary.json).

## Ordinary FAST / DEFAULT / BEST

The same source 90e457277 and first 1 MiB were measured twice using only
`--fast`, no effort flag, or `--best`, plus operational output and verbosity.
No route/backend/format/block/history/memory/thread flags were supplied.
Defaults admitted four workers with 512 MiB estimated working memory.

| Effort | Complete bytes | Encode wall, s | Encode CPU, s | Encode max RSS, KiB | Decode wall, s | Trials |
|---|---:|---|---|---|---|---:|
| FAST | 476,034 | 0.44, 0.43 | 1.62, 1.63 | 10,588, 10,832 | 0.28, 0.29 | 128 |
| DEFAULT before repair | 407,643 | 2.90, 2.91 | 11.03, 10.99 | 10,592, 10,832 | 1.25, 1.22 | 544 |
| BEST | 354,023 | 18.51, 17.45 | 47.47, 47.61 | 138,740, 136,580 | 0.61, 0.59 | 736 |

FAST selected LZ, historical DEFAULT BWT, BEST PPM. Zero omissions; all
repetitions restored exactly. FAST's observed encoding rate was 2.30 MiB/s,
BEST's 0.0556 MiB/s. The size/time/memory tradeoff is explicit.
[Profile evidence](adversarial-parallel-evidence/cix-profile-qualification/profile-summary.json).

## DEFAULT model-admission repair

The old DEFAULT cap excluded PPM before evaluating it. Source 2b26cc074 v1
moved PPM into the shortlist when input-derived prediction rate exceeds 0.1.
The same DEFAULT CLI was compared with source 90e457277 on both frozen ranges.

| Range / implementation | Complete bytes | Encode wall, s | Decode wall, s | Encode max RSS, KiB |
|---|---:|---|---|---|
| Development / old | 407,643 | 2.85, 2.84 | 1.19, 1.20 | 11,196, 10,844 |
| Development / v1 | 381,955 | 2.46, 2.48 | 0.55, 0.55 | 10,836, 11,080 |
| Replication / old | 423,660 | 2.85, 2.84 | 1.24, 1.23 | 11,308, 11,380 |
| Replication / v1 | 397,078 | 2.48, 2.47 | 0.55, 0.55 | 11,596, 11,096 |

Exact size improvements are **6.30% / 6.27%**; observed encode wall reductions
about 13%, decode about 54–55%. All eight fresh decodes matched. No omissions,
544 trials per archive, BWT replaced by PPM. Conservative peak scratch
reservation rose from 80 to 288 MiB; measured process RSS remained about 11 MiB.
The replication average RSS rose slightly, so no memory win is claimed.
The original order was AABB. See the [revision/order erratum](adversarial-parallel-evidence/CONTROL-REVISION-ERRATA.md)
and the separate corrected ABBA v2 results below; do not present AABB timings
as isolated causal estimates.
[Original v1 evidence](adversarial-parallel-evidence/cix-default-model-qualification/default-model-summary.json).

## Corrected DEFAULT v2: interleaved replication

Policy v2 was frozen at source ee6b4396 before re-evaluation. The extra
64-opportunity requirement limits unsupported PPM trials on tiny or idle-flushed
blocks. Control/candidate/candidate/control order was predeclared separately
for each range; both source revisions and binary hashes are attested.

| Range / implementation | Complete bytes | Encode wall, s | Encode CPU, s | Decode wall, s | Encode RSS, KiB |
|---|---:|---|---|---|---|
| Development / old | 407,643 | 2.91, 2.90 | 11.04, 11.07 | 1.24, 1.23 | 10,832, 10,592 |
| Development / v2 | 381,955 | 2.54, 2.52 | 9.58, 9.60 | 0.58, 0.59 | 11,112, 11,136 |
| Replication / old | 423,660 | 2.94, 2.95 | 11.05, 11.13 | 1.28, 1.28 | 11,356, 11,616 |
| Replication / v2 | 397,078 | 2.52, 2.55 | 9.67, 9.62 | 0.58, 0.57 | 11,120, 11,100 |

All eight fresh native decodes matched; both candidate archives are identical
to the corresponding v1 archive bytes/hash. Each still evaluated 544 candidates
with zero omissions. The exact size improvement remains **6.30% / 6.27%**.
Observed mean encode wall improves **12.9% / 13.9%**, decode **52.6% / 55.1%**.
Candidate sustained encoding is 0.395 / 0.394 MiB/s and decoding
1.71 / 1.74 MiB/s; rates are from the full measured range, not initial probing.
RSS increased modestly on development and decreased on replication; no memory
domination claim. ABBA reduces order confounding but does not control all host
activity or prove unseen-input generalization.

A derived-summary failure after all successful cells exposed normalization of
`input.range_kind` out of runner identity. No encoder/decoder failed. The summary
was regenerated by checking each frozen manifest hash and recovering its
range/revision; no immutable cell was edited or rerun. Future harnesses retain
these fields in configuration and have a regression for normalization.
[Corrected measurements](adversarial-parallel-evidence/cix-default-confidence-v2/default-model-summary.json).

## Mixer allocation experiment: no measured throughput win

Source 08711c496 versus 2b26cc074, fixed mixture route, 128 KiB, one worker,
64 KiB CIXG2 blocks, 512 MiB. Each binary used its matching decoder.
All four archives were **52,400 bytes**, SHA-256
`e201719706d51f50b12523ca07a6969e1447efd5be38457ca13c93d942951cb5`.
Control encode wall: 1.45/1.45s; candidate: 1.43/1.50s. Control decode:
1.44/1.48s; candidate: 1.44/1.44s. Encode RSS: control 25,820/25,560 KiB,
candidate 25,820/25,564 KiB. These differences do not establish a throughput
or RSS improvement. The counted-allocation test verifies removal of per-bit
scratch allocation, while full archive and model state remain identical.
The remaining model-map/arithmetic work is an optimization target.
[Complete mixer evidence](adversarial-parallel-evidence/cix-mixer-qualification-mixer-stack-scratch-v1/qualification-summary.json).

## Streaming evidence and integrity

The open slow-producer harness emitted 2,048 bytes and withheld EOF until both
a compressed frame and reconstructed bytes appeared. With two FAST workers,
64 KiB maximum blocks, 16 MiB working budget and a 100ms flush interval, the
first complete compressed frame arrived at **150.904ms**, decoded bytes at
**150.986ms**, both before EOF. The completed 1 MiB archive was 1,048,355 bytes
and fresh archive-only decoding restored exactly. This demonstrates one
best-effort latency sample, not a latency distribution. Encoder work, 50ms
completion polling and downstream stalls can delay output. Flush never inserts
unframed bytes. Whole-stream integrity is confirmed only at footer verification.
The native pipe tests also cover idle flush, irregular chunks, slow consumers,
empty input, missing/corrupt frames, and 10 MiB input under a 9 MiB working
budget. Working-memory admission is estimated; it is not an OS RSS limit.

## Verification at delivered source

The final release suite passed **178 tests**, zero failures, with four repeated
copies of the previously verified expensive chain fixture filtered. That
fixture passed in the initial complete 164-test release run and its implementation
was unchanged. Native v1/v2/v3 model golden fixtures were rerun after the mixer
change. The suite includes minimum-opportunity selection, actual implicit stdin,
`--` parsing, contradictory output options, malformed/memory admission, worker
order/cancellation, pressure and interruption cleanup. Nine qualification-runner
unit tests and five benchmark-adapter option assertions passed. The current
shared library also passed irregular callback encode/decode in separate fresh
C processes; read/write failures, truncation and invalid level returned errors.
[Native ABI evidence](native-ffi-final-smoke.md).

## Packaging and remaining scope

The benchmark adapter now invokes actual ordinary Rust FAST/DEFAULT/BEST
behavior. Historical `current`/`size` aliases normalize to `default`/`best`;
expert flags are forwarded only when explicit. Binary hashes and exact commands
are recorded. This changes future recipe identity; frozen historical recipes
and results stay preserved.

Host binaries and native library are identified in
[dist/native-release.json](../../../dist/native-release.json). Rebuild with
`CARGO_BUILD_JOBS=2 cargo build --profile release-lto --locked --manifest-path rust/cix-native/Cargo.toml --bin cix --bin uncix --bin cixcat --lib`.
Install the three binaries using `install -Dm755 dist/cix ~/.local/bin/cix`
and equivalent commands for `uncix` and `cixcat`. No other platform is qualified.
The Squash shim is native; current-host Squash SDK availability and its narrower
ABI defaults must be distinguished from ordinary CLI benchmarking.

Automatic cross-package CIXM6/CIXG2 comparison, segmentation/transform beam,
conditional composition, ANS/FSE, PGO, native recurrence/periodicity ablations,
represented-input ZPAQ controls, broader Pareto replication and the preserved
Canterbury/Calgary/Artificial gate remain open. CIXM6, decoding and explicit
external portfolio modes remain serial. BEST is a bounded native search over
its eligible candidates, not the argmin over every legal encoding. No first
place, universal superiority, full port/optimization coverage, or full queue
completion is claimed. [Queue](experiment-queue.md), [coverage](coverage-matrix.md).
