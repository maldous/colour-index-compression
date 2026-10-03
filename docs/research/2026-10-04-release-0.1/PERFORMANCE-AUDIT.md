# v0.1 performance and compression opportunity audit

Status: `RESEARCH_REVIEW_ONLY — NO EXECUTION OR PRODUCTION EDIT`

This audit is the release decision record for the native implementation.  It
inspects source at research checkpoint `20e18503b` and the production incumbent
`d3a2cd416`.  The two revisions have identical `rust/cix-native/src`,
`Cargo.toml`, and `build.rs` trees: checkpoint `20e18503b` adds only retained
experiment files.  Consequently this record applies to the candidate v0.1
codec source, while the experiment tree must remain outside a public package.

It does **not** turn a historical experiment, an ideal predictive-bit result,
or a profiling hypothesis into a claimed archive or throughput improvement.
There was no new corpus run, build, benchmark, profiler, scan, or source edit
for this audit.

## Decision

No remaining compression mechanism is qualified for production promotion.
The complementary-predictive audit found a real but immaterial causal signal:
fixed-share weighting improved the held-out diagnostic by 937.523 ideal bits
(0.5747%, 0.017607 bits/input byte) over the best traced expert.  It captured
only 1.832% of the 47,163.564-bit hindsight gap.  The oracle selects after
seeing the symbol and its 28.911% gap is not an achievable archive saving.
The gate lost to fixed-share and both failed the declared material-gain gate.
The only next action for that branch is closure, not a codec.

The remaining release work is finite qualification and code hygiene.  The
only source-level throughput hypothesis with a sufficiently concrete target is
whole-archive portfolio work avoidance, but it is not an authorized
optimization until one final-source profile quantifies it.  The exact source
executes native CIXG trials serially, CIXM6 block trials serially, and then all
14 CIXB1 descriptors, validating candidate outputs before replacement.  This
is deliberate correctness and resource accounting, not proven waste.

## Evidence already closed

| Area | Evidence and result | Release consequence |
|---|---|---|
| Exact rank arithmetic | `perf-f579` retained byte-identical Kennedy archives (82,984 bytes) and one instrumented DEFAULT observation of 2.26 s to 2.13 s encode wall time.  Unused/duplicate cardinality work was removed. | Integrated.  BigUint division remains the largest sampled hotspot, so further rank work needs a new profile and exact-byte proof. |
| PPM temporary allocations | `ppm-eligible` removed temporary context-key vectors with byte-equivalent kernel results.  It is explicitly a kernel allocation screen, not a whole-codec speed claim. | Integrated.  No allocator or global RSS claim follows. |
| Chain duplicate inner encoding | `chain-cache-93d1` led to a bounded cache that reuses identical inner encodings under admitted block memory. | Integrated; do not replace it with speculative caching without a new bounded-memory measurement. |
| Input reservation | The bounded reader and external-source changes replaced broad direct reservations with conservative bounded growth. | Integrated; preserve its race, interruption, and source-capacity protections. |
| Structural/count/transform ideas | Conditional contexts, histogram reuse, residual lanes, integers and word exceptions show synthetic effects, but no qualified ordinary-CIX held-out win.  The word-exception wrapper loses 63 bytes to its plain-native control. | No route, transform, metadata wrapper, or selector addition. |
| Predictive mixture | CPI1 tested 28 eligible experts over 13 real held-out prefixes / 53,248 bytes.  The oracle is non-causal; causal results did not clear promotion.  PPM and LZ full-route forecasts were properly excluded rather than fabricated. | Close this branch.  It does not justify a mixer, gate, or physical entropy stream. |
| Decoder scaling | Decode `--threads >1` is rejected; retained two/four-thread decoder cells failed natively.  CIXM6 is serial by design. | Not a v0.1 optimization candidate.  Do not market parallel decoding. |

## Remaining bounded opportunities

| Priority | Exact opportunity | Why it remains | Required acceptance evidence | Decision rule |
|---|---|---|---|---|
| 1 | Measure whole-archive BEST candidate cost before considering pruning or ordering work. | For eligible small named inputs, `portfolio_auto` can run 1 baseline, up to 6 CIXG format/block trials, 3 CIXM6 trials, and all 14 CIXB1 descriptors.  They are serial because CIXG2 may itself use workers and external calls have coarse cancellation.  No final-source call graph apportions this cost. | One isolated `perf stat`/call graph on frozen Kennedy DEFAULT/BEST under the release queue P1/P2 rules; bind source, binary, input, archive, restore, CPU, memory, no-swap and lost samples.  Report candidate count, winner, omissions, per-family time, allocation and validation cost. | Only propose a change if a named non-winning trial or repeated validation dominates measured cost and a replacement preserves exact candidate eligibility, deterministic winner/tie order, complete archive bytes and fresh restoration.  Otherwise retain the finite search. |
| 2 | Choose, do not guess, portable build policy. | Historical compiler/LTO and PGO screens are nonfinal or disagree.  No current source-bound portable build choice exists beyond the sealed fat-LTO/CGU-1 reference. | Release queue B0–B9 and G: same frozen source/lockfile/C++ inputs; archive identity and fresh cross-decode; one FAST and constrained BEST guard. | Retain B0 unless a portable arm improves both wall and user CPU on DEFAULT, avoids regressions on both guards, and preserves bytes.  Host-native ISA remains a separate artifact. |
| 3 | Qualify encoder scaling policy rather than invent decoder parallelism. | The ordered CIXG block pipeline and candidate strategy exist, but retained old scaling evidence is unqualified. | Release queue S1–S12: one/four worker CIXG curves, deterministic archive equality, task/thread peaks, ordered-queue peak, memory admission, one serial M6 anchor. | Change a shipped default only for a nonregressing selected point with its measured resource limits.  Results apply only to the frozen input/configuration. |
| 4 | Remove dead code and keep the exported package statically clean. | The final d3a2 Sonar scan has zero current Rust issues and resolves the earlier three complexity findings.  Compiler dead-code notices remain outside that Sonar result, and `lib.rs` has a crate-wide `allow(dead_code)`. | Q2 full optimized suite and Q4 exported-source scan plus all-target/all-feature Clippy.  Classify each warning by compiled product target; remove unreachable release code or confine test/audit-only code behind explicit test/feature boundaries. | Do not suppress new warnings globally.  A source change must preserve all archive compatibility checks and pass fresh scan/suite before packaging. |

The release closure register already supplies the exact P/B/G/A/S/Q cell
definitions and resource protocol.  It is the authoritative execution plan;
this audit does not broaden it into Silesia, Hutter, acquisition, broad
benchmarking, or a new compression search.

## Static source findings

`portfolio_auto.rs` makes the candidate-work opportunity concrete.  CIXG
trials iterate formats and block sizes at lines 432–520, CIXM6 trials at
545–618, external trials at 620–711, and selection deliberately serializes
them at 714–717.  The fixed `--portfolio size` path also serially tries eleven
native routes in `main.rs` lines 3263–3302.  A current profile must distinguish
search work from the elected codec, validation decode, and external library
calls before any change is discussed.

The current source contains several `Vec` construction sites in search setup,
but their lifetime is bounded and their replacement has no measured benefit.
The relevant release behavior is already guarded by explicit capacity and
memory admission.  Replacing bounded vectors, adding unsafe indexing, making
validation lazy, or parallelizing a serial external search would be a
correctness/resource-policy change, not a safe micro-optimization.

`rank.rs` is still the most credible kernel target only because the prior
instrumented profile sampled BigUint division at 33.63% and found its
cardinality subtree at 3.79% after the integrated fix.  That source identity
predates the incumbent, and the single observation is insufficient to select
another arithmetic change.  The conditional-count experiment also found exact
rank and range payloads tied with the range wrapper 32 bytes larger; it gives
no new count-coding route.

## Compression boundary

The completed records rule out promotion of every concrete mechanism they
tested.  They do not prove a mathematical global limit for lossless
compression, and the current release cannot honestly say every imaginable
algorithm has been exhausted.  The defensible v0.1 statement is narrower:
all currently proposed native CIX extensions have either been integrated with
parity evidence, closed as a negative/insufficient result, or are awaiting a
specific finite release-qualification cell.  No evidence-selected new
compression implementation remains.

## Release gate

Before a public distribution build, complete the finite release queue against
the exact selected source and package artifact: P1–P4 profiling receipts;
B/G/A/S choices; Q1 locked build provenance; Q2 complete optimized suite; Q3
bench smoke; Q4 current Sonar/Clippy inventory; and Q5 PTT5 BEST current plus
frozen-BD2 decode compatibility.  Any code change discovered from P1 is a new
source identity and invalidates matching qualification rows.  The public
source/package split must omit `docs/research`, `benchmarks`,
`rust/cix-native/experiments`, private scheduler records, corpus assets and
local performance receipts; they are evidence, not runtime dependencies.

At this checkpoint, the evidence-selected next action is **execute release
queue P1 final-source profiling, then either retain the current portfolio
search or open one bounded, profile-backed optimization**.
