# R&D closure before packaging

User direction: test all identified programme opportunities, then package.
Status: **OPEN — packaging is not ready.** A proposal, source route name or
an absent implementation does not count as a tested opportunity. New production
changes receive distinct source-bound experiments. Completed historical results
are reused only within their documented scope; cancelled baselines stay stopped.

## Coverage register

- [Prediction, counts and structural substreams](prediction.md): eight finite
  cells covering probability/coder costs, mixing, long recurrence, calibration,
  context composition, joint/hierarchical counts, split/join and shared descriptions.
- [Representations](representations.md): seven finite cells for lane/residuals,
  dictionary exceptions, phrase/grammar, numeric bins/PFOR, sparse exceptions,
  bounded shallow combinations and OpenZL/Brevis encoder-search principles.
- [Reviewed methods](coverage.md): all 29 requested codec names plus supplementary
  inventories mapped by distinctive mechanism, including pending integer codes,
  literal/token coding, ANS/FSE, dictionary-reset and online neural controls.
  Shared cells are cross-references, not duplicated trials.
- [Performance and release](performance-release.md): profiling, allocations,
  compiler/LTO/native builds, disjoint PGO, thread/block/memory curves and
  current-source release validation. Historical screening is preserved and
  never relabelled final-source evidence.

## New completed mechanism screens

| Cell | Result | Still required |
|---|---|---|
| R1 lane/residual | 51 candidate rows, all exact; strong 278→129 B, weak 526→232 B, random literal 8,221 B; malformed checks reject. [Evidence](r1-results/REPORT.md) | New fixed CCA development and held-out replication before any promotion. |
| R2 word exceptions |18exact rows; strong matched wrapper273→267B (6B), all weak/absent palettes lose. [Evidence](word-exception-results/REPORT.md)| No plain-CIX production-size win; promotion remains open. |
| N6 integer codes |21exact rows; delta888→556B strong,632→616B weak; varint wins random. [Evidence](integer-substream-results/REPORT.md)| Real structural substreams and same-backend integration remain open. |
| COND-CONTEXT synthetic | 12 exact rows; order2 context 4,302→64 B strong, 4,302→85 B weak, expands on random; raw 16,414 B. [Evidence](conditional-context-results/REPORT.md) | CCA replication and appropriate profile/memory controls; no production-format promotion yet. |

These are complete experimental stored-byte comparisons, not corpus records.
They do not close calibration, predictor ablations, related-count deltas or
structural substream coding. Negative and fallback results are retained.

## Closure and package gate

Every declared cell must end with a recorded positive, negative or bounded failed
trial. If an opportunity cannot be executed, record its concrete dependency,
resource or implementation blocker; keep it visible as untested/blocked, never
claim all tested. No acquisition is opened to remove such blockers. No named
codec needs adding merely to increase codec count: its distinctive principle
still needs measured evidence or a documented untested boundary.

Replicated winners need production integration followed by current-source exact
restoration, compatibility, deterministic/error/streaming checks and the CCA gate.
Then freeze release source/binaries/settings, retain a portable build and produce
build/install/CLI examples plus a measured compatibility matrix. Only then package.
One observation per configuration; no timing averages. Root dispatches all heavy
jobs through WaveScheduler with four physical cores / decimal12GB memory /
4GB active temporary / no swap. Local computation only, no Actions or publication.

## Current refactor checkpoint

Native source d3a2cd416e49f93403d1dbd348a3e9a45db66ec6 passed its release
build, seven chain tests, eight focused footer/CLI checks and latest Docker
Sonar (zero current Rust issues). Compiler dead-code target warnings remain241.
Binaries are in benchmark-work/release-d3a2/final; [evidence](../release-d3a2/REPORT.md).
This does not close the pending full-current suite, large-pipe replay, build/PGO,
scaling or unexecuted compression experiments. The separate N6 integer-coder
harness initially failed compilation before any encode; corrected v2 completed
21 measured exact rows. Initial failure remains preserved, not silently replaced.
