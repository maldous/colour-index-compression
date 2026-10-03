# Rust sustained R&D programme status

Snapshot: 2026-10-03. This is a read-only register, not a new experiment
identity or a claim that a queued mechanism improves compression.

| Track | Current implementation and evidence | Status | Smallest next matched experiment | Promotion condition |
|---|---|---|---|---|
| Prediction and calibration | CIXG route selection, entropy scoring and complete frame accounting are in `rust/cix-native/src/main.rs`; PPM modelling is in `ppm.rs`; arithmetic/count coding is in `rank.rs`. The exact combined release-validation packet is `docs/research/2026-10-03-rust-performance-audit/combined-bd2-validation/` (713 executions). The later `docs/research/2026-10-03-ptt5-numeric-fix/` retains one PTT5 run only, not a final combined release. | Implemented. An ideal remaining-count `log M` accounting log exists; quantised-CDF probability cost and a calibration ablation remain unmeasured. | On one frozen CCA development row, hold route/history/backend fixed and compare the existing predictive stream with one explicitly charged count/arithmetic control. Preserve raw as incumbent and produce full archives and fresh cross-decodes. | Candidate has smaller complete bytes after all model/count metadata; exact fresh restore and resource receipt. |
| Conditional and joint counts | `rank.rs` implements count-range, composition, colex and context-type-class operations; `ppm.rs` and `legacy_lz.rs` consume rank coding. Overflow guard evidence is in `docs/research/2026-10-02-rust-performance-audit/integer-overflow-guards/`. | Completed conditional-cost-v1 has eight matched control rows. Histogram-reuse-v1 completed 11 exact rows: −333B strong, −158B partial reuse, +42B absent. Six malformed cases rejected. These are metadata-only gains; no production claim follows. | One fixed route/block experiment comparing its present coding with a remaining-count conditional variant; side information, context reset and coder termination must be charged. | Byte win versus same predictive information and same frame, with malformed/truncation checks. |
| Versioned reversible language and representations | CIXG1/G2 framing, phrase/BWT/LZ/numeric and CIXM6 paths are in `main.rs`, `chain.rs`, `legacy_lz.rs`, `bwt_legacy.rs`, `sparse_runs.rs`. Narrow reciprocal-route evidence is retained in `docs/research/2026-10-03-sonar-bwt-sparse/` and chain packets. | WPV2 has six exact rows. Its nested 17-byte strong-control saving loses after 69B wrapper overhead. RSL1 completed a12-candidate screen: identity won; all tested transforms lost. Exact transformed-byte deduplication eliminated 2/11 native calls with identical complete bytes in its qualified finite screen. Production mode-7 per-call reuse is implemented at 93d1 and passed two focused tests plus old-Rust-decoder M6 full-block/G1 idle pipes. No corpus speedup or production representation-size win is claimed. M6 idle flushing is fixed at 4af606b54 and passed actual idle-pipe, empty, unchanged-no-flush, fresh cross-decode and footer-rejection checks. General throughput/scaling remains unmeasured. | One representation at a time against identity, with fixed backend/options and charged transform metadata. Start from an existing development fixture, not a selector-wide tournament. | Identical original-byte restoration and smaller complete archive; no automatic portfolio promotion from one result. |
| OpenZL / Brevis | No OpenZL or Brevis adapter, source binding, or qualified receipt was found in the Rust source tree or current audit register. | Absent. | Isolated feasibility adapter with a fixed original-byte control and explicit dependency/model/version accounting. | Full archive and independent restore before any selector or portfolio inclusion. |
| Parsing, history and neural models | Parsing/history mechanisms exist in `legacy_lz.rs`, `chain.rs`, `stateful.rs`, `adaptive.rs`, `zpaq_context.rs`; bounded history/resource checks appear in `main.rs`. No neural Rust backend/model artifact is registered. | Parsing/history implemented; neural absent. | Fix one parser/history window and compare with same parser reset at the same block boundaries. Treat a neural proposal as a separate model-artifact experiment. | Gain survives charged history/model bytes, exact decode and fixed-resource limits. |
| Resources, CPU and build optimisation | Resource admission is in `resources.rs` and `main.rs`. Hotspot preflight is `benchmarks/cix_rust_hotspot_audit.py`; build/ThinLTO/native/PGO staging is `docs/research/2026-10-03-rust-performance-next/build-pgo-queue.md`. | Prepared queue; no final-source PGO result. | After a qualified-release freeze and WaveScheduler lease, run one CPU-8 `perf stat` row with archive/decode identity. Build screening then begins O3 no-LTO CGU16 vs CGU1. | No changed archive bytes for implementation-only builds; PGO requires a new disjoint train/held-out identity. |
| Held-out, gates and qualification | Combined exact-source validation is retained in `docs/research/2026-10-03-rust-performance-audit/combined-bd2-validation/` (713 executions); static inventory is `docs/research/2026-10-03-sonar-bd2a0d97/`. Existing gate language in `build-pgo-queue.md` requires complete bytes, fresh native decode, resources and the user-authorized single measurement protocol where applicable; it supersedes older repetition wording. | Validation infrastructure implemented; held-out promotion is per new experiment. | Development first, then predeclared untouched held-out row only after a development result meets its promotion rule. | Independent archive-only restore SHA, limits, complete configuration, and no selector tuning on held-out result. |

## Constraints carried into every next cell

Use existing frozen assets and scheduler leases; do not acquire data or restart
historical baselines. Record source/tree, input SHA and range, flags, route,
block/history, model and side-information bytes, binary/DSO identity, cgroup
limits, full archive SHA and fresh decode SHA. Treat timing from concurrent
work as descriptive until run under the stated qualification receipt.

## Latest verified implementation and streaming milestone

Release source 6ac05f8e9: exact-arithmetic redundant work removal measured
2.26 → 2.13 s encoding on one matching instrumented Canterbury row, with
identical 82,984-byte archive and exact fresh restoration. See perf-f579/REPORT.md.
This is a 5.75% observation, not a replicated speed claim. No size tradeoff.

G1 and restricted-budget M6 actual-pipe 32 MiB qualification passed, including
idle output before EOF, slow-consumer backpressure, current/old native restoration,
empty input, corrupt/truncated footer and interruption checks. See
qualification-6ac0/REPORT.md; preserve the unsuccessful original M6 timing row.
Latest release Clippy has no Clippy/unused-variable findings but retains 241
dead-code target warning instances. Current Docker Sonar scan is pending a
harness cgroup identity fix; do not treat the older Sonar checkpoint as current.
Full current-suite, scaling/build matrix/PGO and held-out improvements remain queued.

## Closure audit requested before packaging

The finite [closure register](closure-queue/README.md) records all identified
pending mechanisms; queued/absent/unqualified entries are not completed tests.
R1 lane/residual now has51 exact candidate rows: strong278→129B, weak526→232B,
random selects literal8221B. Conditional composition now has12 exact rows:
strong global4302→context2 64B, weak4302→85B, random expands and selects raw.
These are synthetic experimental complete-frame wins. Neither is promoted
without frozen CCA and held-out replication. Packaging remains OPEN.
