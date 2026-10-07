# Six capability audit and qualified release

Release source: `938e88054adef5b9c33bfe2022b73fc6546074e9`.
Linux x86_64 binaries: repository `dist/cix`, `dist/uncix`, `dist/cixcat` and
`dist/libcix_native.so`; exact hashes and build command are in
[release metadata](qualified-release-evidence/final-native-release.json).
Source was built from a clean detached worktree, excluding experimental edits
in `cix-best-parity`. Review and implementation were divided among parallel agents.

## Actual capabilities

“Partial” means a substantive mechanism is available but does not cover the
whole requested capability. Correctness evidence does not imply a size or speed win.

| Requested capability | Status and actual production behavior | Sources | Exact-restoration evidence and gaps |
|---|---|---|---|
| 1. Adaptive context mixing, recurrence distance and periodic models | **Partial.** Native CIXG route 9 mixes adaptive bit contexts; CIXM6 also selects expert/fixed mixing and record/periodic models. Recurrence v3 is **experimental**, not selected. | `rust/cix-native/src/fixedmix.rs:556`, `zpaq_context.rs:99`; `main.rs:981`, `main.rs:2204`, `main.rs:2378`; `record_periodic.rs` | Preserved fixed-mixture qualification restored identical 52,400-byte archives in fresh processes; recurrence tests preserve legacy v1/v2 fixtures and check corrected causal v3. Record/periodic evidence records 10 canonical payload matches and Rust restoration. No ZPAQ-equivalent MATCH/ISSE/SSE/periodic component graph or measured recurrence ablation is claimed. |
| 2. BWT/sort transforms with local or conditional coding | **Partial, production.** BWT → MTF → local zero-run representation; tags, nonzero literals and run-length varints are coded separately. The primary index is paid. CIXM6 includes additional BWT/local-coder variants. | `main.rs:1420`, `main.rs:1511`, `main.rs:1599`; `bwt_legacy.rs` | The constrained complete-archive oracle fresh-decodes BWT candidates. Preserved evidence includes 25 canonical Rust BWT encodes and 39 decoder fixtures. A global multinomial rank does not gain merely because BWT permutes input. New shared transform-order/conditional-rank search remains experimental. |
| 3. Input-derived stride/lane detection and delta/XOR residuals | **Partial, production.** Byte-derived sample scoring selects among byte delta, 4/8-byte little-endian delta, 4-byte big-endian delta, and 4/8-byte little-endian XOR; lane separation is invertible. | `main.rs:721`, `main.rs:733`, `main.rs:777`, `main.rs:822`, `main.rs:934`; `transform.rs`, `numeric.rs` | Constrained route/backend oracle and fresh native round trips cover the production route. Preserved transform evidence records 128 explicit and 12 beam encodes plus 32 restored fixtures. New widths 2/3/16/32 and cross-order beam experiments are not production-enabled. |
| 4. Cheap word-level dictionary prediction with exceptions | **Absent as specified; related work experimental.** Existing prediction events are causal **byte** successor tables, previous-byte and optional lag predictions, with literal escapes. They are not word dictionaries. Production phrases learn only two-byte entries. | Experimental worktree `prediction_events.rs`, `research_routes.rs`; production `main.rs:835` | Five helper tests restored strong, weak, random, periodic, empty/tiny and malformed cases before review. No production word-event archive, persistent word dictionary, or matched word-model gain exists. It is not promoted. |
| 5. Separate literal/token models, repeat offsets, ANS/FSE | **Partial, production.** LZ has distinct tags/literals/lengths/distances; BWT and phrase routes have separate paid streams. CIXM6 LZ has repeat-distance cache symbols and literal coder choices. Static rANS is **experimental**; FSE is **absent**. | `main.rs:538`, `main.rs:1623`, `main.rs:1692`; `legacy_lz.rs:969`, `legacy_lz.rs:1005`, `legacy_lz.rs:1078`; experimental `rans.rs` | Existing LZ canonical payloads and inverse fixtures, plus the complete-archive oracle, verify restoration. rANS's positive-frequency normalization defect was fixed and five focused tests pass; no production per-stream ANS/FSE or frozen structural-stream coder tournament is claimed. New ER framing still needs independently selectable four-stream coders before family-E promotion. |
| 6. Learned phrase dictionaries and universal integers | **Partial, production.** An input-derived dictionary of up to 32 two-byte phrases is serialized, with tag/literal/index streams. Unsigned self-delimiting base-128 varints describe LZ lengths/distances and BWT runs. | `main.rs:835`, `main.rs:892`, `main.rs:1503`, `main.rs:1692`; `legacy_lz.rs` | Dictionary bytes and all stream lengths count; inverse consumes every stream exactly. The constrained phrase oracle fresh-decodes archives. No arbitrary learned-word/fragment or base-plus-edit dictionary is claimed. Alternative Elias/Golomb/Rice/universal-code comparisons and cost-aware parser qualification remain open. |

Source line numbers above refer to the exact release source. Experimental paths
refer to the separate development worktree and are not compiled into these binaries.
Historical wire-reference checks are preserved evidence; this release uses no
Python executable or subprocess for compression/decompression.

## Selector deployment

Existing native mechanisms retain generic content-derived eligibility and exact
materialized cost comparison. BEST considers all eleven existing native routes
under its documented resource/search policy; DEFAULT retains the replicated
PPM prediction-confidence admission repair. FAST remains a cheap shortlist.
Each stream stores the choices needed by its decoder; raw remains a fallback.

Ordinary named-file BEST now also compares **complete** CIXG2 and the nine
canonical CIXB1 configurations. This includes the verified Python-winning direct
bzip2-9 path, which previously required a separate portfolio option. Source,
incumbent, trial and validation allocations are charged; reconstruction comparison
does not allocate another whole-output buffer. Unexpected codec errors are fatal;
resource omissions are reported. Backend versions and complete costs appear in
`--explain`/`--verbose`. A backend win is attributed to the backend.

No new backend has been promoted. New Brotli q11 and larger XZ configurations
remain in an explicitly experimental API; automatic CIXM6 package competition
also remains experimental. CIXM6's existing selector is still available explicitly.
An advanced constraint excludes only incompatible candidates; `--route auto`
does not disable the whole-archive comparison.

The whole-archive comparison is restricted to regular named files up to 64 MiB
which fit the memory budget. Pipes, `--stream`, idle flushing, larger files and
incompatible framing constraints continue through bounded CIXG streaming.
Native CIXG blocks have explicit reset boundaries and an ordered bounded worker
pool; CIXM6 preserves its existing causal history serially. CIXB1 itself is a
bounded whole-archive wrapper, not an incremental streaming container.

## Current validation

[Final focused test evidence](qualified-release-evidence/final-tests.summary.json):
23/23 tests pass: automatic BEST registry/decode, native backend/archive admission,
gzip expansion bounds, interruption/atomic-output handling, real-pipe streaming,
and aggregate-budget validation of an actual 64 KiB native mixer frame.
Pipe tests verify pre-EOF compressed output and restored bytes, idle flush, irregular
chunks, slow downstream consumption, empty/corrupt/truncated streams, and a stream
larger than its working-memory budget. An additional [55 fresh native CLI round
trips](qualified-release-evidence/final-native-capability-smoke.json) passed at
this final source, with 110 corrupt/truncated archives rejected. Every native
route ID 0–10 was actually selected by at least one nonempty fixture; raw
fallbacks and empty streams are identified separately. This is mechanism and
restoration evidence, not a size or speed claim.

Mechanism-specific preserved evidence:
[implementation and canonical parity](implementation-smoke.md),
[bounded complete-archive oracle and measured native changes](adversarial-parallel-results.md).
The previous 178-test release pass is preserved separately; it is not relabeled
as a rerun at this source revision.

## Remaining gaps

- Word-level dictionary event prediction, production recurrence v3 and rANS/FSE.
- Independent structural-substream coder experiments and calibrated model ablations.
- General transform-order, block/history/segmentation and cross-package optimization.
- Matched automatic CIXM6 package qualification; its existing models are not yet
  automatically reached through ordinary BEST packaging.
- BEST remains a finite safety-bounded search, not exhaustive over all legal encodings.
- Native one-shot backend calls may delay interruption until the library returns.
- Other platforms and a Squash SDK-loaded plugin remain unverified on this host.

The [full Dickens comparison](cix-dickens-qualified-best-v1/README.md) completed
two repetitions per immutable binary pair, the same input hash, four physical CPUs and fresh archive-only
decoding. The historical Python archive is a size comparator, not a timing control.
No corpus rank, broad gate completion or experimental promotion is inferred from it.

The two corrected runs matched the Python record byte for byte: 2,799,567 bytes.
Their 20.16% size improvement over the old plain Rust client is a qualified
backend/selector repair. A [separately frozen full-Dickens final-source cell](cix-dickens-final-best-v1/README.md)
verified identical archive bytes and fresh restoration after the validation-budget correction.
