# Representation closure queue

Audit date: 2026-10-03. This finite dispatch register is not a claim that every representation should enter CIX. It preserves negative results and uses existing fixtures only. Every queued cell needs a new freeze, complete framed identity control, one encode/decode measurement, fresh archive-only restore, and side-information accounting before policy can change.

## Existing coverage and boundaries

| Opportunity | Existing evidence | Established boundary |
| --- | --- | --- |
| Lane, modular delta and XOR | `chain.rs`; [RSL1 report](../representation-search-v1/REPORT.md) | Twelve 8 KiB programs were exact; identity (2,487 B) beat every tested transform. Delta and previous-stride residual are byte-identical at lags 1/4. Lanes 2/8/16 and nonduplicate compositions remain untested. |
| Exact transformed-byte reuse | [dedup results](../representation-search-dedup-v1/results.json) | Two duplicate native trials were eliminated with identical complete bytes. This proves no size saving and does not search new transforms. |
| Dictionary and exceptions | `main.rs:phrase_encode`; [WPV2 report](../word-palette-v2/REPORT.md) | Palette saved 17 B inside the strong wrapper, but wrapper overhead lost to plain CIX; weak/absent lost 48/170 B. Width 2/4 and in-format signalling are untested. |
| Phrases / grammar | `main.rs:phrase_encode/decode`, `legacy_lz.rs`, `bwt_legacy.rs`; [grammar receipt](../../2026-10-02-rust-performance-audit/matched-best-grammar-summary.json) | Phrase route and grammar.lsp archive exist. No matched dictionary-cardinality or grammar-versus-literal representation ablation is registered. |
| Numeric bins / offsets / PFOR | `numeric.rs` FOR, delta, delta2 and PFOR; `chain.rs` numeric operations | Candidate codecs and decoder bounds exist. No isolated complete-byte bin/offset/PFOR-exception ablation receipt was found. |
| Sparse exceptions / runs | `sparse_runs.rs`, `chain.rs:encode_sparse`; histogram-reuse report | Sparse/run payloads exist; histogram reuse has strong −333 B, partial −158 B, absent +42 B controls. No sparse-exception screen separate from histogram metadata exists. |
| OpenZL / Brevis | [RSL1 plan](../representation-search-v1/PLAN.md), [programme status](../PROGRAMME-STATUS.md) | Their encoder-side ideas were documented. No adapter, dependency binding or receipt exists; no pretrained decoder asset is permitted. |

## Finite missing cells

Each synthetic input is deterministic and 8 KiB. It tests mechanism presence, weakness and absence without corpus identity routing. Every candidate stores instructions, counts, exceptions, tails and complete framing.

| Cell | Frozen controls | Candidate set / prerequisite | Promotion decision |
| --- | --- | --- | --- |
| R1 lane/stride | Periods 2/8/16, modular counters, xorshift absent. | Identity; transpose, delta and XOR lags 2/8/16; at most six declared nonduplicate depth-two pairs. Reuse RSL1 exact-byte cache. | Complete-frame win on strong and recorded weak/absent losses. |
| R2 dictionary exceptions | Existing WPV2 strong/weak/absent fixtures. | Width 2/4 palettes, cardinalities 8/16, explicit raw escapes. Requires versioned in-format experiment, not another wrapper. | Same-frame identity comparison; nested savings alone cannot promote. |
| R3 phrase/grammar | Repeated pair strong, shuffled-pair weak, xorshift absent; grammar.lsp later only. | Existing phrase route versus identity, caps 8/16/32; charge dictionary, tags and literals. | Complete bytes plus fresh restore; no inference from one grammar archive. |
| R4 numeric bins/PFOR | u32 narrow offsets, alternating wide values, random absent, 1–2% outliers. | Existing FOR/delta/delta2/PFOR at width 32/64; report base, bit width, exception positions/values, tail. | Same numeric information/frame; preserve expansion losses. |
| R5 sparse exceptions | All-zero 1%, 10%, 50% deterministic exceptions. | Existing M6 sparse/run versus identity; fixed M6 archive-only runner required. | Break-even includes positions and values; separate from histogram reuse. |
| R6 bounded language | Strong controls from R1–R3 only. | Atoms identity, transpose, delta, XOR, phrase/palette/literal; depth two; ≤24 declared semantic-distinct programs. | Complete archive selects; finite enumeration, not optimal-search claim. |
| R7 OpenZL/Brevis feasibility | R1 strong and absent only. | Documentation/interface work: pin source/dependency/version, deterministic reversible transforms, stored operation program, no model/checkpoint. | Separate adapter freeze and independent restore before any run; external portfolio results stay separate. |

## Order

Dispatch R1–R5 independently before R6. R7 does not authorize acquisition. Do not rerun the RSL1 twelve-program screen, WPV2 width-8/16 wrapper screen, histogram-reuse rows, or historical grammar timing averages. R1 and R5 are first because native inverse paths already exist. All cells remain pending scheduler leases and source/binary freezes.
