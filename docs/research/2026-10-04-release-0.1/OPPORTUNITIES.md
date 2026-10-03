# CIX v0.1 opportunity and frontier audit

**Audit date:** 2026-10-04  
**Evidence basis:** `research/silesia-competitive`, numeric-composition checkpoint `20e18503b`, production source `d3a2cd416`, and CPI1 evidence.  
**Scope:** history and code evidence review only. No experiment ran and no native source changed.

## Decision

There is no demonstrated, release-ready compression improvement after the current production revision. There is also no basis for claiming an information-theoretic limit: the record establishes a practical frontier for qualified mechanisms, not a universal lower bound for arbitrary lossless compression.

The only high-value unmeasured compression lead is the already implemented corrected FixedMix recurrence-v3 signal. CPI1 deliberately excluded it, so its negative decision does not apply to v3. Its smallest honest test is an isolated frozen causal trace against recurrence-disabled FixedMix on the existing CCA development/held-out split. PPM/SEE is a second, more fundamental gap: method-1 reachable original-byte mass is 0.5 in its full-alphabet self-check, so it cannot be silently treated as a normalized expert.

Every other item is either a finite unexecuted experiment, an explicit blocker, or throughput/release qualification work. It is not evidence that an improvement exists. [opportunities.json](opportunities.json) is the machine-readable counterpart.

## Status meaning

| Status | Meaning |
| --- | --- |
| `closed-negative` | A stated mechanism lost or failed its gate; do not reopen it by parameter fishing. |
| `closed-scope` | Evidence closes only the named mechanism or input scope. |
| `available-measurement` | Existing code can answer a causal or physical question without a new format. |
| `available-bounded` | A finite experimental implementation is specified but no gain is shown. |
| `blocked` | A method cannot be qualified under current resource/dependency rules. |
| `release-qualification` | Performance, compatibility, or packaging work; never a compression gain. |

## Consequential hindsight-oracle review

CPI1's hindsight oracle selects after seeing the byte. On 53,248 held-out real bytes it improves from 163,134.352 to 115,970.789 ideal bits: 47,163.564 bits (28.911%). Fixed-share causal weighting captures 937.523 ideal bits (0.5747%); the development-selected context gate captures 864.065 bits (0.5297%). Both miss the material gate and neither has a physical archive measurement.

That large oracle gap is not missed codec saving. Duplicate experts give zero gap, while redundant smoothing gives 2,335 bits and perturbed copies of one informative expert give 12,648 bits without a new causal signal. Those controls demonstrate selection advantage and calibration variance. The oracle points only to existing FixedMix components that sometimes rescue one another; the production composite already contains nearly all measured signal. The consequential omissions are recurrence-v3 and PPM's unresolved outcome space. There is no evidence that a gate, neural selector, route portfolio, transform, or post-hoc oracle label would recover the oracle gap.

Evidence: [CPI1 report](../2026-10-04-predictive-information/REPORT.md), [null controls](../2026-10-04-predictive-information/null-controls.json), and [native inventory](../2026-10-04-predictive-information/INVENTORY.md).

## Evidence ledger

| ID | Opportunity | Status | Evidence and conclusion | Bounded decision |
| --- | --- | --- | --- | --- |
| P1 | FixedMix composite, static/online mixture, context gate | `closed-negative` | Fixed-share gains 937.523 ideal bits; gate gains 864.065, loses to fixed-share, and both miss the material gate. [CPI1](../2026-10-04-predictive-information/REPORT.md) | Close the frozen 28-expert branch; no physical mixer. |
| P2 | Corrected recurrence-v3 FixedMix | `available-measurement` | Implemented, causal, replayable, but untraced. CIXG route 9 dispatches recurrence-disabled FixedMix; legacy v2 used lookup-after-observe. [Inventory](../2026-10-04-predictive-information/INVENTORY.md) | Freeze v3/no-v3 trace, validate intervals, evaluate existing split without tuning. Advance only on repeated material held-out gain. |
| P3 | PPM/SEE probability interface | `available-measurement` | Causal coding path exists, but reachable byte mass is 0.5 in the method-1 check. [Exposure amendment](../2026-10-04-predictive-information/EXPOSURE-AMENDMENT.md) | Prove an outcome space with unit reachable-byte mass at every prefix, or retain PPM as coding-path-only. |
| P4 | Long causal match predictor | `available-bounded` | LZ parser is not an original-byte forecast. FixedMix match4 is measured; no standalone long-match residual model exists. [Prediction queue](../2026-10-03-rust-rnd/closure-queue/prediction.md) | One frozen-window predictor versus current residual, strong/weak/absent, charged complete framing. |
| P5 | FixedMix interval calibration | `available-bounded` | No complete ideal-versus-interval-versus-finish cost ledger exists. [Prediction queue](../2026-10-03-rust-rnd/closure-queue/prediction.md) | Run PRED-COST-1 before one frozen monotone calibration test. |
| P6 | Context type-class partition | `closed-scope` | Synthetic context partition can win, but CCA transfer is unmeasured. [Context result](../2026-10-03-rust-rnd/closure-queue/conditional-context-results/REPORT.md) | One frozen CCA gate only; it is representation work, not mixture evidence. |
| P7 | Joint/hierarchical count headers | `available-bounded` | Histogram reuse wins for related metadata and loses for all-distinct metadata. [Prediction queue](../2026-10-03-rust-rnd/closure-queue/prediction.md) | Test declared delta-count and two-level headers against independent and reference-only controls. |
| R1 | Lanes, stride, delta, XOR | `closed-negative` | Shallow identity won; 51-row R1 gains are constructed-case only. [R1 result](../2026-10-03-rust-rnd/closure-queue/r1-results/REPORT.md) | Do not broaden transform search. |
| R2 | Dictionary/word exceptions | `closed-scope` | Strong wrapper saves 6 B; weak/absent lose; no plain-CIX win. [Exception result](../2026-10-03-rust-rnd/closure-queue/word-exception-results/REPORT.md) | At most one existing same-frame width-2/4 identity control, otherwise exclude from v0.1. |
| R3-R5 | Phrase/grammar, numeric/PFOR, sparse exceptions | `available-bounded` | Native routes exist, but isolated complete-frame cells are not all measured. [Representation queue](../2026-10-03-rust-rnd/closure-queue/representations.md) | One declared test per mechanism. Never reopen numeric M6 composition. |
| R6-R7 | Bounded representation language, OpenZL/Brevis | `closed-scope` / `blocked` | 12-program shallow search lost; no local deterministic OpenZL/Brevis adapter is bound. [Representation queue](../2026-10-03-rust-rnd/closure-queue/representations.md) | Only run R6 after independent positive cells; record R7 dependency blocker unless local pinned code exists. |
| C1 | Constraint intersection/rank theory | `closed-negative` | Established finite-set/MDL coding; paid direct controls remove general claimed gain. [Theory report](../2026-10-03-constraint-space/REPORT.md) | No general-theory or synergy promotion claim. |
| C2 | Exceptions, positions, segmentation/history | `closed-negative` | Synthetic gains lose to stronger controls or real-prefix incumbent. [Model queue](../2026-10-03-constraint-space/model-evidence/QUEUE.md) | Preserve; do not extend local geometry, hierarchy, or template caches. |
| C3 | Latent layout and numeric M6 composition | `closed-negative` | New representation saves 4 internal bytes but costs 29 bytes of description; incumbent wins 1,393 to 1,418 B. [Composition report](../2026-10-03-constraint-space/segmentation/composition-evidence/REPORT.md) | Preserve checkpoint `20e18503b`; permanently do not reopen this branch. |
| E1 | Bounded LZ parser versus lazy parse | `available-bounded` | Current bounded hash-chain grammar is not a test of all named LZ library parsers. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | One <=64 KiB parser test with grammar/coder fixed. |
| E2 | BWT local streams | `available-bounded` | BWT/MTF route is partial; no paid local run/literal split comparison. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | One <=64 KiB same-coder control with primary-index cost. |
| E3 | Dictionary/filter backends | `closed-scope` | Brotli/XZ/Zstd are backends, not native predictive wins; generic policy forbids identity/type routing. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | Do not add static dictionaries or filters for v0.1. |
| E4 | LZW and XPRESS-Huffman | `available-bounded` | Both native frames are absent; components do not qualify wire equivalence. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | One named <=16 KiB experiment each, or a recorded implementation blocker. |
| E5 | rANS/FSE substreams | `available-bounded` | Native rANS/FSE absent; Huffman/range are controls, not equivalents. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | One fixed LZ payload, with table/normalization/termination charged. |
| E6 | Universal integer codes | `closed-scope` | Delta/Rice/varint synthetic cell completed; real entropy-coded token integration unmeasured. [Integer result](../2026-10-03-rust-rnd/closure-queue/integer-substream-results/REPORT.md) | One current phrase/LZ length stream versus Elias/Rice, or exclude. |
| E7 | Compact online neural predictor | `not-v0.1-candidate` | No native neural model; FixedMix is not one. A new topology and persisted update protocol would change the frozen release surface. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | Defer bounded zero-init N7 to separately authorized post-v0.1 work. |
| E8 | External ZPAQ/PAQ | `closed-scope` / `blocked` | ZPAQ wrapping expanded 431 B; PAQ -12L is blocked by 12 GB. [Coverage queue](../2026-10-03-rust-rnd/closure-queue/coverage.md) | Comparator only; do not substitute lower PAQ preset or call external gain CIX gain. |
| T1 | M6 discarded histogram scan | `available-measurement` | Current `m6_fill_block` calls `fill_candidate_block` and discards its `[u32; 256]` result. This is not a second input read: the reader scans each newly read segment to build a histogram that M6 does not use. [Current source](../../../rust/cix-native/src/main.rs) and [proposal](../2026-10-03-rust-rnd/next-hotspot-proposal.md) | Profile and parity-qualify removal of the unused scan before a small source change. |
| T2-T4 | Build/PGO/allocation/scaling/final gates | `release-qualification` | Historical build/scaling evidence is not final-source release evidence; d3a2 has 241 compiler dead-code warning instances. [Performance queue](../2026-10-03-rust-rnd/closure-queue/performance-release.md), [d3a2 report](../2026-10-03-rust-rnd/release-d3a2/REPORT.md) | Complete B/G/A/S and Q1-Q5 on frozen release source, then remove or justify dead code. |

## Practical frontier, not a limit claim

The closed evidence rules out uncharged constraint intersections, metadata sharing treated as free, adaptive segmentation/history, lane separation alone, selective transforms, latent numeric layouts, numeric composition, and a simple second-level mixture of the 28 traced experts. It also keeps portfolio selection distinct from same-symbol predictive mixing.

It does not prove a Kolmogorov, entropy, or universal-code lower bound. Such a proof needs a source distribution and fixed model class; finite corpus/archive measurements cannot supply it. The defensible v0.1 statement is: **no qualified improvement remains after this ledger reaches terminal status**, not that no compression improvement is possible.

## Evidence-selected order

1. P2 recurrence-v3 trace: the sole implemented omitted causal signal with a direct CPI1 connection.
2. P3 PPM outcome-space audit: resolve eligibility before recording PPM losses or oracle comparisons.
3. P5 cost ledger: stop if finite-precision/termination overhead consumes any ideal gain.
4. Run remaining `available-bounded` items only as declared finite closure cells. A loss is terminal; do not fan out variants.
5. Freeze selected source and complete T1-T4. These decide a distributable v0.1 artifact, not a compression claim.

No evidence justifies materializing a predictive mixed codec, reviving numeric composition, broad benchmarking, acquisition, or a production edit before the first three items show a physical opportunity.

## Individual closure-cell register

This section expands every numbered cell in the retained prediction,
representation and method-coverage queues. Repeated cells are named separately
where their queue requires a separate wire-format or physical-archive result.
`Not a v0.1 candidate` means that the mechanism lacks the stated technical
precondition, has been superseded by later evidence, or is outside the frozen
generic/release policy. It never means that the underlying theory is exhausted.

| Cell | Disposition | Exact evidence or technical reason | Smallest terminal action |
| --- | --- | --- | --- |
| PRED-COST-1 | `available-measurement` | CPI1 measures ideal losses for eligible experts but not integer interval, termination and framing gaps. PPM's contribution is blocked by P3. | Counters for adaptive O0/O1 and FixedMix first; include PPM only after unit-mass proof. |
| PRED-MIX-1 | `superseded-partial` | CPI1 closes the specified 28-expert ideal mixture, but its archive-format v3 recurrence and PPM arms were not measured. | P2 then a single physical same-frame ablation only if P2 clears its causal gate. |
| PRED-LONG-1 | `available-bounded` | Existing LZ tokens are not a next-byte forecast and no bounded causal long-match residual exists. | Two fixed windows, one strong/weak/absent suite, charged model/window bytes. |
| PRED-CAL-1 | `blocked-by-PRED-COST-1` | Calibration cannot be credited unless interval loss, finish and table cost are known. | One frozen monotone table after PRED-COST-1 is positive. |
| COND-CONTEXT-1 | `terminal-synthetic` | Twelve exact synthetic archives prove the mechanism can pay under constructed conditional histograms; this is not CCA transfer. | One frozen CCA development then held-out gate, or explicit v0.1 exclusion. |
| COND-COUNT-1 | `available-bounded` | Exact-header reuse is positive only for exact/related headers; unequal joint-count coding remains unmeasured. | Delta and two-level headers versus independent/reference-only controls. |
| STRUCT-SUBSTREAM-1 | `available-bounded` | No bounded generic skeleton/value/literal split has a complete-frame result. | Fixed delimiter-class frame on the declared three synthetic controls. |
| STRUCT-SHARED-1 | `blocked-by-STRUCT-SUBSTREAM-1` | A shared dictionary has no meaningful base frame until the preceding structural split earns its descriptors. | Run only after a positive STRUCT-SUBSTREAM-1 result. |
| R1 | `terminal-synthetic` | R1's 51 rows include constructed wins but earlier RSL1 identity won its shallow real screen; later numeric/latent evidence forbids using R1 to reopen numeric composition. | One CCA transfer gate or exclude all lane transforms from v0.1. |
| R2 | `available-bounded` | Wrapper palette result loses to plain native archive; width-2/4 in-format signal is a distinct unmeasured frame. | Same-frame identity/palette trial with all escapes and dictionary bytes. |
| R3 | `available-bounded` | Existing phrase/grammar archives lack a cardinality/literal matched ablation. | Caps 8/16/32 on fixed repeated/shuffled/random controls. |
| R4 | `available-bounded` | FOR/delta/PFOR exist, but synthetic integer evidence is not a complete native representation result. | Width 32/64 framed offsets/outliers trial. |
| R5 | `available-bounded` | Histogram reuse does not pay sparse position/value costs. | M6 sparse/run versus identity at fixed 1/10/50 percent exception rates. |
| R6 | `blocked-by-R1-R3` | The depth-two language must not enumerate a new transform tournament without independently positive atoms. | Run only if an R1-R3 cell passes its own complete-byte gate. |
| R7 | `blocked` | No already-local pinned deterministic OpenZL/Brevis implementation; model/checkpoint use is disallowed. | Record dependency blocker; do not acquire dependency for v0.1. |
| COPY | `terminal-integrated` | Raw copy is the mandatory complete-frame control, not an optimization candidate. | Retain in every comparison. |
| LZ-LAZY | `available-bounded` | One lazy parse tests the parser principle across the named generic LZ family; 16 library clones would not add independent mechanism evidence. | One <=64 KiB repeat/distance fixture with token grammar/coder fixed. |
| BWT-LOCAL | `available-bounded` | Native BWT/MTF exists, yet no paid run/literal local-stream control separates it from backend effect. | One <=64 KiB control with primary index and same CIX coder. |
| DICT-FILTER | `not-v0.1-candidate` | Static dictionaries and type filters violate generic policy; a serialized input-derived dictionary is already R2. | No separate dictionary/filter implementation. |
| LZW | `available-bounded` | Resettable LZW frame is absent; LZ resemblance does not establish it. | One <=16 KiB reset-boundary frame or explicit implementation blocker. |
| FARI-LZHAM | `available-bounded` | Current range coding is uncoupled from parser/model; no FARI/LZHAM equivalence is claimed. | Same frozen literal stream through adaptive range and count-range, paid headers. |
| XPRESS-HUFFMAN | `available-bounded` | Existing Huffman cannot substitute for the distinct command/table grammar. | One <=16 KiB token/table frame or explicit blocker. |
| DEFLATE-RAW | `available-bounded` | Native inner DEFLATE exists; zlib-ng binary substitution is absent and cannot support a speed claim. | Materialize current raw-DEFLATE payload versus raw complete frame. |
| EXTERNAL-BACKENDS | `release-qualification` | Brotli/bzip2/XZ/Zstd are CIXB1 backends, not native methods. | Read back pinned binary/settings and archive-only decode evidence; no new backend tournament. |
| ZPAQ | `terminal-negative` | Raw match was reproduced; wrapping a CIXG1 archive expanded by 431 B. | Keep external comparator only. |
| PAQ-12L | `blocked` | Exact requested setting exceeds shared 12 GB cap; a lower preset is not an equivalent test. | Retain resource blocker. |
| SQUASH-ABI | `blocked` | Native callback smoke is not SDK plugin loading; host lacks the SDK and acquisition is prohibited. | Record SDK-unavailable blocker. |
| N1 | `superseded-partial` | N1 duplicates the recurrence/mixing portion of PRED-MIX-1; CPI1 closes only its ideal 28-expert portion. | P2 before the N1 physical archive cell. |
| N2 | `available-bounded` | FixedMix has lag signals, but no separately serialized periodic-feature archive test. | One base/periodic same-frame suite. |
| N3 | `available-bounded` | rANS/FSE absent; canonical Huffman is the correct common-stream control. | One four-stream LZ payload with all coding tables/termination charged. |
| N4 | `alias-LZW` | N4 is the native closure alias for LZW, with the same missing resettable frame. | Follow LZW action, do not duplicate run. |
| N5 | `alias-XPRESS-HUFFMAN` | N5 is the native closure alias for XPRESS-Huffman. | Follow XPRESS-HUFFMAN action, do not duplicate run. |
| N6 | `available-bounded` | Synthetic integer screen completed, but current phrase/LZ lengths have not been compared under their actual framing. | One current stream: varint versus Elias/Rice. |
| N7 | `not-v0.1-candidate` | No neural artifact exists; a new model topology and update protocol would add format and maintenance risk after the frozen release. | Defer to a separately authorized post-v0.1 experiment. |
| Q1 | `not-v0.1-candidate` | Heterogeneous equality/affine-plus-count discovery is an established bounded-counting research question, and later paid real-prefix/numeric composition results do not support opening it for v0.1. | Preserve as post-release theory work only. |
| Q2 | `not-v0.1-candidate` | A BDD/circuit certificate is a new representation language with compile/order metadata and no current local candidate. | Defer; no generic codec claim. |
| Q3 | `not-v0.1-candidate` | Higher-order interaction was unexecuted, but direct-model simplification and paid-pair losses preclude treating volume synergy as a release lead. | Defer; never reopen C3. |
| Q4 | `not-v0.1-candidate` | Approximate shortlist versus exact certificate is a research architecture problem, not a current archive mechanism. | Defer until a concrete paid representation has a bounded source freeze. |

## Source and quality corrections

The prior T1 wording is corrected above. `fill_candidate_block` performs the
read and increments `symbol_counts` while it fills the block. `m6_fill_block`
calls it and discards the histogram. Thus the opportunity is removal of one
per-byte histogram update/scan, not removal of a duplicate input read. It is
worth profiling but has no a priori throughput magnitude and cannot change
compressed bytes.

The final Sonar record is `sonar-d3a2`, not the older `sonar-6ac0` status:
source `d3a2cd416` was scanned by pinned fresh Docker images, with scanner and
compute engine completing and zero current Rust Sonar issues. That does not
clear 241 compiler dead-code warning instances, experimental adapters, or
vendor C/C++ outside the Rust scan. The release gate must therefore describe
Sonar as clean *within its scanned Rust scope* and keep compiler-warning
cleanup as Q4 work.

## Second-pass v0.1 disposition of finite cells

The first register says whether a small experiment exists. This second pass
answers the release question: whether the retained evidence and current code
make it a plausible v0.1 compression lead. Except for P2/P3, which are being
measured separately because they expose already implemented predictive state,
the answer is no. This is a review disposition, not empirical confirmation that
each hypothetical future format cannot win.

| Cell(s) | v0.1 disposition | Code/evidence reason |
| --- | --- | --- |
| PRED-LONG-1 | `reviewed-unproven; defer` | It requires a new causal match-table model and new residual frame. The closest existing causal `fixed_match4` has a negative fixed-share removal cost (-10.399 ideal bits), while the current LZ route is a token parser rather than a forecast. There is no retained residual failure pattern that identifies a bounded window as valuable. |
| COND-COUNT-1 | `reviewed-unproven; defer` | Exact header reuse already captures the only measured metadata redundancy (-333 B identical, -158 B partial, +42 B absent). Unequal-count coding needs a new header language; later paid support/segmentation and numeric-layout evidence did not beat incumbent. |
| STRUCT-SUBSTREAM-1 / STRUCT-SHARED-1 | `reviewed-unproven; defer` | These introduce a skeleton/join grammar and dictionary not present in the release format. Their intended repeated-structure gain overlaps paid record/exception/segmentation work, whose strongest real-prefix case remains behind CIXM6. No generic byte-derived delimiter class has a demonstrated residual advantage. |
| R2 dictionary exceptions | `reviewed-negative for v0.1` | The best nested palette saving is 17 B, while its 69 B wrapper leaves 256 B versus 204 B plain CIXG1; weak and absent cases lose. A new width-2/4 frame might differ, but no observed break-even margin supports adding a release format. |
| R3 phrase/grammar | `reviewed-unproven; defer` | Phrase and bounded-LZ routes already compete in the native portfolio. The queued work is a new explicit dictionary-cardinality frame, not a missing invocation of an existing optimizer; no retained archive shows an unpriced phrase cardinality gain. |
| R4 numeric/PFOR | `reviewed-unproven; defer` | Numeric/FOR/delta/PFOR code already exists, but a generic byte utility has no schema-free signal identifying a numeric substream. The later latent-layout and M6-composition gates rejected the only concrete numeric representation lead; this row cannot reopen C3. |
| R5 sparse exceptions | `reviewed-unproven; defer` | Sparse/run coding is already an M6/portfolio candidate. A new standalone position frame would duplicate position/value metadata, and existing header-reuse gains do not evidence sparse-position savings. |
| R6 bounded language | `not-v0.1-candidate` | A second enumeration language is explicitly a new transform programme. Its predecessor atoms lack a release candidate and the user has closed the numeric structural-composition path. |
| R7 OpenZL/Brevis | `not-v0.1-candidate` | It would import a new deterministic transform/program interface with no retained local candidate or evidence of an unrepresented signal. This is future architecture research, not an optimization omission. |
| LZ-LAZY | `reviewed-unproven; defer` | Current bounded hash-chain LZ already competes as a native route. Lazy parsing is a parser-policy replacement requiring new encode/decode qualification, and no profile or archive evidence identifies parse greediness as a dominant loss. |
| BWT-LOCAL | `reviewed-covered` | BWT code already emits MTF run tags, literals and lengths (`main.rs` `mtf_runs` and `bwt_legacy.rs` stream encoders), with paid primary index and integer choices. A further local split has no distinct defined signal; it is not a missing BWT capability. |
| LZW / XPRESS-Huffman | `not-v0.1-candidate` | Each requires a new token grammar, table/reset semantics, frame, decoder, and error surface. Similarity to existing LZ/Huffman does not yield a low-risk incremental optimization, and no retained input evidence gives either a priority. |
| FARI-LZHAM / DEFLATE-RAW | `reviewed-covered` | Current code already has adaptive/range and count-range controls, plus native raw DEFLATE as an inner coder. The queued tests distinguish named external designs; they do not expose a missing production predictor. |
| N2 periodic | `reviewed-covered` | FixedMix already has lags 1/2/4/8/16/32 and M6 already trials record/periodic candidates. CPI1 gives those lag components only 2.363-19.695 fixed-share ideal bits of marginal value, so there is no measured case for another periodic wire feature. |
| N3 rANS/FSE | `not-v0.1-candidate` | This is an entropy-coder replacement, not new predictive information. It needs a new finite-precision decoder/table format and can only improve coding overhead on already materialized streams; no measured interval-overhead budget yet exists (PRED-COST-1). |
| N6 universal integers | `reviewed-covered` | Current BWT/M6 code already has bounded varint and Rice alternatives. Synthetic delta/Rice gains show representation sensitivity, but no actual phrase/LZ length stream shows a remaining coding gap large enough to pay a third integer grammar. |
| N7 neural | `not-v0.1-candidate` | A neural model would create a new model artifact, update protocol, state/memory envelope, and archive compatibility commitment after release freeze. It is not an existing unexposed CIX model. |
| Q1-Q4 theoretical questions | `future research only` | They are explicitly project questions within established finite-set, knowledge-compilation and arithmetic-coding theory. They lack a concrete release representation, and cannot override the later C3 closure. |

This leaves one empirically necessary decision path for compression: the
already implemented recurrence-v3 signal (P2), followed by the PPM outcome
contract (P3). If either does not yield a material causal result and a
subsequent physical break-even case, the reviewed v0.1 compression ledger is
terminal: all other finite cells are retained as honest future work rather than
release candidates.
