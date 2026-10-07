# CIX / Six complementary predictive information audit — CPI1

**Decision: a small causal improvement exists in the frozen 28-expert set, but it does not clear the material-gain gate. Do not build a physical mixed codec from this result.**

The development-selected context gate saves **864.065 ideal bits (0.5297%; 0.016227 bits/input-byte)** against the strongest constituent, the existing FixedMix eta-6 composite. It captures only **1.8321%** of the hindsight gap. The gate loses to simple fixed-share online weighting on held-out data and is rejected. The ordinary fixed-share result is also below the material threshold.

This is a bounded predictive-information audit, not a compression leaderboard or an archive-size result. There is no new compression-theory claim. Existing production CIX and the closed numeric composition result remain unchanged.

## 1. Scope, frozen evidence and exposure

Checkpoint `20e18503b` on `research/silesia-competitive`; native predictor source copied from incumbent `d3a2cd416`. Source hashes, mechanical doc-comment rewrite, binary identity, input ranges and settings are bound in [freeze.json](freeze.json), [binary.json](binary.json), [inputs.json](inputs.json) and [trained.json](trained.json).

All 33 existing Canterbury/Calgary/Artificial members were traced, at most 4096 bytes each. Sorted even/odd file positions within each family define development/held-out membership. This is a CCA prefix integrity screen, not completion of full-file CCA compression qualification. No Silesia, Hutter, acquisition, Sites or Actions jobs ran.

Primary held-out evidence is **13 real files / 53,248 bytes**. Artificial files are separate controls. Before held-out extraction, `calgary-pic` was quarantined because its sampled bytes duplicate development `canterbury-ptt5`; its result is retained separately. [Exposure amendment](EXPOSURE-AMENDMENT.md). These are historically exposed corpus assets, held out only from this instrument's fitting. Neither file balance nor a small prefix screen establishes broad transfer.

| Split | Files | Bytes | Role |
|---|---:|---:|---|
| development / canterbury | 6 | 24,201 | real data |
| development / calgary | 9 | 36,864 | real data |
| development / artificial | 2 | 4,097 | diagnostic |
| heldout / canterbury | 5 | 20,480 | real data |
| heldout / calgary | 9 | 36,864 | one held-out duplicate excluded |
| heldout / artificial | 2 | 8,192 | diagnostic |

## 2. Actual model inventory and common interface

| Implemented mechanism | State / predicted unit | Causal probability and audit disposition |
|---|---|---|
| Adaptive frequencies, orders 0/1 | Counts and Fenwick tree per history bucket; byte | Integer masses `2c+1`, total `2seen+256`; normalized, adaptive, independently replayable; traced. |
| Context-expert orders 0/1/2/4 | Sorted counts per preceding suffix; byte | Additive-one normalized frequencies; all tables updated after observation; four traced experts. |
| Context-expert selector, mode 17 | Prior exponentially decayed losses plus those tables; byte | Chooses one model before target; traced as causal selection, not probability mixing. Native floating update retained; no new integer-codec claim. |
| FixedMix v1 eta=6 | 13 pattern tables, six lags 1/2/4/8/16/32, match4, per-bit reliability, weights/bias, bounded history; bit | Already internally mixed. All 20 components and full existing composite traced as exact conditional-bit products over bytes. |
| Corrected recurrence v3 / legacy v2 | Previous-byte recurrence-distance feature, reliability buckets and additional mixer weight | Implemented optional native extension; **untraced in CPI1**. Current registered CIXG route uses v1. V2 lookup-after-observe collapses the recurrence feature; v3 corrects it. No global claim about this unmeasured signal. |
| PPM fixed escape / SEE | Context counts, exclusion and escape state; sequential escape/hit/fallback symbols | Causal native coding paths can be subnormalized over the byte alphabet. The full-alphabet method-1 selfcheck gives reachable byte mass **0.5**, not 1. Excluded rather than silently renormalized. No per-real-position PPM loss claim. |
| LZ and phrase parsers | Match/token history plus encoder token search; matches and tokens | Actual parser routes do not expose an original-next-byte normalized distribution. Only FixedMix's existing causal match4 signal is traced. |
| Runs, composition/counts | Run lengths/positions or paid block count vectors | Future run extent and final block statistics are not causal original-byte experts; excluded. A valid paid count-conditioned coder is not an eligible history-only forecast. |
| Stride/periodic residuals, BWT, numeric, wavelet, bitplane, chains | Transformed symbols/blocks and selected transform descriptions | Transforms/routes, not additional comparable original-byte probability experts. FixedMix lag signals are separately eligible. |
| Arithmetic/range, count-range, Huffman and nested/external coding | Intervals or transformed substreams | Coders/backends; range coding itself contributes no predictive signal. |
| Whole-input portfolio / local routing | Finished candidate archives or regions | Post-encoding selection, not predictive mixing; excluded from ideal mixture table. |
| Python-only CTW and retained research variants | Reference/research models | Not dispatched by current native CIX; excluded from this native screen. |

The [code-grounded inventory](INVENTORY.md) provides file/line anchors, state, transform dependence and replay details. Each traced expert exposes a normalized byte distribution before scoring the target; `observe(actual)` follows. No final counts, transform search, source name or future bytes enter prediction. Full distributions are temporary; traces retain actual probability, entropy, maximum mass, argmax, pretarget run/match/context-selection diagnostics and normalized noise forecasts.

For FixedMix, the 255-node byte-prefix tree multiplies the native conditional bit probabilities. Earlier bit updates affect only that bit's keyed state, so enumeration from the pre-byte state matches sequential native updates. Selfcheck tests all 256 candidates across four histories against sequential native bit intervals. Components remain derived from shared native state; they are not independently trained replacement compressors.

## 3. Held-out first decision table

**Every number below is ideal predictive bits, not payload bytes or complete archive bytes.** Best single is the aggregate-best constituent; it is also the best on every primary held-out file and was selected on development. Highest-probability positions count ties within absolute tolerance 1e-12.

| Expert / method | Ideal bits | Bits/input-byte | Highest-probability positions |
|---|---:|---:|---:|
| adaptive_o0 | 265772.983 | 4.991229 | 212 |
| adaptive_o1 | 269515.527 | 5.061515 | 63 |
| context_o0 | 269633.754 | 5.063735 | 14 |
| context_o1 | 290470.560 | 5.455051 | 61 |
| context_o2 | 340782.830 | 6.399918 | 101 |
| context_o4 | 381228.411 | 7.159488 | 203 |
| context_selected | 265928.625 | 4.994152 | 46 |
| fixed_pattern_empty | 260736.802 | 4.896650 | 2780 |
| fixed_pattern_1 | 218886.272 | 4.110695 | 4766 |
| fixed_pattern_1_2 | 241873.919 | 4.542404 | 3859 |
| fixed_pattern_1_2_3 | 284394.907 | 5.340950 | 1379 |
| fixed_pattern_1_2_3_4 | 315661.791 | 5.928144 | 586 |
| fixed_pattern_1_3 | 256809.404 | 4.822893 | 2129 |
| fixed_pattern_1_4 | 261620.824 | 4.913252 | 2270 |
| fixed_pattern_1_5 | 278008.151 | 5.221006 | 1936 |
| fixed_pattern_2_3 | 269653.708 | 5.064110 | 1885 |
| fixed_pattern_2_4 | 277301.810 | 5.207741 | 1657 |
| fixed_pattern_3_6 | 301531.452 | 5.662775 | 1682 |
| fixed_pattern_4_8 | 296686.353 | 5.571784 | 2634 |
| fixed_pattern_1_4_8 | 322203.710 | 6.051001 | 774 |
| fixed_lag_1 | 343470.264 | 6.450388 | 1011 |
| fixed_lag_2 | 351598.133 | 6.603030 | 707 |
| fixed_lag_4 | 345671.084 | 6.491720 | 854 |
| fixed_lag_8 | 339365.690 | 6.373304 | 733 |
| fixed_lag_16 | 338554.651 | 6.358073 | 792 |
| fixed_lag_32 | 341318.218 | 6.409973 | 731 |
| fixed_match4 | 323799.139 | 6.080963 | 2399 |
| fixed_mixer_eta6 | 163134.352 | 3.063671 | 22140 |
| equal_static | 230193.801 | 4.323051 | — |
| optimized_static | 162287.714 | 3.047771 | — |
| bayesian | 163196.848 | 3.064845 | — |
| hedge | 163180.537 | 3.064538 | — |
| fixed_share | 162196.829 | 3.046064 | — |
| context_gate | 162270.288 | 3.047444 | — |
| HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY | 115970.789 | 2.177937 | — |

Best single: **163134.352 bits**. Hindsight gap: **47163.564 bits (28.911%)**. Selected causal capture: **864.065 bits**, or **1.832% of the oracle gap**. Remaining hindsight gap: **46299.499 bits**.

**HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY.** It sees the realised symbol before choosing an expert. Its gap is not achievable compression and cannot be charged as an archive saving.

## 4. Static, online, context and switching controls

Static weights use 500 deterministic EM steps on development real files only. The non-negligible global weights are: `fixed_pattern_empty` 0.022360, `fixed_pattern_1` 0.037789, `fixed_mixer_eta6` 0.939851. Other weights remain at approximately the 1e-12 numerical floor.

Development selected Hedge eta=0.25, fixed-share eta=0.5 and alpha=0.0078125. All online methods predict before weight updates and reset to uniform per file. Eta=1 is the Bayesian baseline (with numerical underflow protection); fixed-share permits transitions between experts. No held-out hyperparameter fitting occurred.

The six-bucket context gate uses only prior run length crossed with prior match availability. Its development-fitted weights are frozen with shrinkage to the global static mixture. **It is rejected:** its held-out 162270.288 bits are worse than simple fixed-share's 162196.829 bits. Fixed-share improves by 937.523 ideal bits (0.5747%; 0.017607 bits/input-byte), still below both material thresholds. The development-selected method is not silently replaced by the held-out winner.

The penalized hindsight switching path costs **163030.190 bits** with **58 switches**, including log2(28) initial identity and exact stay/change negative-log penalties. This is a **noncausal comparator**, not a deployable path selector. The causal fixed-share forward method has separate results. The weighted simultaneous probability mixture can beat a single penalized path; no architectural classification is inferred from switches alone.

| Primary held-out file | Selected gate gain over file-best, ideal bits |
|---|---:|
| canterbury-asyoulik.txt | 40.478 |
| canterbury-fields.c | 4.429 |
| canterbury-kennedy.xls | 98.520 |
| canterbury-plrabn12.txt | 115.691 |
| canterbury-sum | 299.829 |
| calgary-book1 | 61.702 |
| calgary-geo | -237.092 |
| calgary-obj1 | 222.575 |
| calgary-paper1 | 68.532 |
| calgary-paper3 | 73.286 |
| calgary-paper5 | 55.095 |
| calgary-progl | 27.103 |
| calgary-trans | 33.916 |

The gate wins on 12/13 real files, but loses 237.094 bits on `calgary-geo`. Artificial `aaa` and `random` gains are approximately +3.20 and −407.39 bits; they never enter the primary decision. The duplicate `calgary-pic` is retained but excluded.

## 5. Null-oracle controls

| Null | Hindsight gap, bits | Causal Bayesian capture, bits | Interpretation |
|---|---:|---:|---|
| Duplicate best-development expert | 0.000 | 0.000 | Normalized distributions; no new history signal |
| Uniform-smoothed redundant copies | 2335.028 | 326.128 | Normalized distributions; no new history signal |
| Uniform + adaptive order0 | 8938.325 | -13.000 | Normalized distributions; no new history signal |
| Four noisy copies of one informative expert | 12648.354 | 151.382 | Independent perturbations conditional on a common informative base |
| Independent weak random-symbol forecasts | 43129.537 | not selected | No matched-quality claim |
| Alignment-broken realised-loss columns, 16 repeats | median 124278.445 | **invalid** | Oracle bias diagnostic only; not valid aligned forecasts |

The informative-base perturbations use exp(±0.25) factors generated independently of the target, then normalize across all 256 symbols before scoring. Their average loss is near the base, but their 7.685% hindsight gap appears without a new causal source. This directly demonstrates oracle selection advantage. Redundant smoothing alone also captures 326.128 bits through ordinary calibration. The measured 864.065-bit primary gain exceeds those causal null captures, but the nulls do not support a statistical-significance or wholly new-information claim.

Four independently perturbed copies of the entire expert bank change average individual losses by approximately 0.0395–0.0402 bits/byte. They produce hindsight gaps around 50.5k bits and selected-gate captures of 1141–1182 bits. Randomness can enlarge both apparent oracle complementarity and variance-reduction benefit. Entirely independent random-symbol forecasts have substantially worse marginal quality; they are not represented as quality-matched controls. [All null results](null-controls.json).

## 6. Complementarity and conditional error tails

The complete [pair matrix](complementarity.json) contains every pair: directional >1/>4-bit wins, loss correlation, argmax disagreements, mean absolute disagreement, and high-loss/uncertainty conditional tails. The compact examples below use the same frozen held-out positions.

| Pair: first / second | Correlation | First >1-bit wins | Second >1-bit wins | Argmax disagreement | First gain when second loses >8 bits |
|---|---:|---:|---:|---:|---:|
| fixed_pattern_1 / fixed_mixer_eta6 | 0.7433 | 5937 | 25352 | 53.34% | 5117.351 |
| fixed_match4 / fixed_mixer_eta6 | 0.5557 | 2662 | 36168 | 56.64% | 2201.423 |
| context_o4 / fixed_match4 | 0.6354 | 3181 | 16575 | 6.54% | 15988.912 |
| adaptive_o0 / fixed_mixer_eta6 | 0.5990 | 4875 | 34369 | 68.89% | 5334.783 |
| fixed_lag_4 / fixed_mixer_eta6 | 0.3289 | 3632 | 41676 | 83.43% | 5296.278 |

These measure prediction errors, not proof that a particular structural mechanism causes a miss. PPM-versus-LZ and count-rescue questions remain unmeasured because those full routes do not supply an eligible normalized common forecast. `fixed_match4` is the actual four-byte-following-byte predictor, not the LZ parser. Lag signals likewise are not the excluded numeric transforms.

## 7. Operational marginal information

Each static leave-one-out control is refitted on development only; online controls remove an expert without retuning the frozen rule. Positive removal cost means that expert helped the full mixture; negative values are retained.

| Expert | Static removal cost, ideal bits | Fixed-share removal cost, ideal bits |
|---|---:|---:|
| fixed_mixer_eta6 | 43941.489 | 36611.322 |
| fixed_pattern_1 | 323.290 | 125.863 |
| fixed_lag_2 | 0.000 | 2.943 |
| fixed_lag_4 | 0.000 | 19.695 |
| fixed_lag_1 | 0.000 | 10.578 |
| fixed_pattern_4_8 | 0.000 | 2.363 |
| fixed_lag_16 | 0.000 | 14.768 |
| fixed_lag_8 | 0.000 | 13.897 |
| fixed_lag_32 | 0.000 | 2.758 |
| fixed_pattern_2_3 | -0.000 | -4.864 |
| adaptive_o0 | -0.000 | 7.389 |
| context_selected | -0.000 | -4.615 |
| context_o0 | -0.000 | 6.752 |
| fixed_pattern_1_2 | -0.000 | -0.903 |
| fixed_pattern_2_4 | -0.000 | 9.297 |
| fixed_pattern_3_6 | -0.000 | -6.887 |
| fixed_pattern_1_4 | -0.000 | -6.270 |
| fixed_pattern_1_4_8 | -0.000 | -13.401 |
| fixed_pattern_1_3 | -0.000 | -7.546 |
| fixed_pattern_1_5 | -0.000 | -6.087 |
| fixed_match4 | -0.000 | -10.399 |
| fixed_pattern_1_2_3 | -0.000 | -14.893 |
| adaptive_o1 | -0.000 | -16.952 |
| fixed_pattern_1_2_3_4 | -0.000 | -15.864 |
| context_o1 | -0.000 | -18.399 |
| context_o4 | -0.000 | -18.489 |
| context_o2 | -0.000 | -19.530 |
| fixed_pattern_empty | -4.757 | 165.633 |

The existing composite dominates: removing it costs roughly 43.9k static-mixture bits. The clearest additional static contribution is its own order-1 pattern component (~323 bits). The non-negligible fitted weights are all the composite or signals already inside it. This supports a small recalibration opportunity; it does not show that alternative route families conceal a large new information reservoir.

## 8. Residual-bit attribution

Relative to the **noncausal** per-position oracle, **12.14%** of positions account for 50% of positive excess bits; **38.93%** account for 90%. This concentration is descriptive, not an achievable regret bound.

| Oracle rescuer identity | Attributed excess bits | Fraction of excess |
|---|---:|---:|
| fixed_pattern_1 | 4564.428 | 9.86% |
| fixed_pattern_empty | 4174.328 | 9.02% |
| fixed_pattern_1_2 | 3535.846 | 7.64% |
| fixed_match4 | 2662.235 | 5.75% |
| fixed_pattern_1_5 | 2452.715 | 5.30% |
| fixed_pattern_2_3 | 2421.687 | 5.23% |
| fixed_pattern_4_8 | 2286.080 | 4.94% |
| fixed_lag_1 | 2214.906 | 4.78% |

Ties use the frozen expert order, so this table does not uniquely allocate shared information. Pretarget run/match bucket totals and the 20 largest contiguous >1-bit excess clusters are retained in [residual-attribution.json](residual-attribution.json). No causal labels such as “PPM failure”, “missed LZ recurrence” or “rare-count effect” are assigned without an eligible measured predictor.

## 9. Computation, state and overhead assessment

| Measured family, primary held-out set | Distribution enumeration seconds | State-update seconds | Maximum estimated family state, MiB |
|---|---:|---:|---:|
| adaptive_o0 | 0.027897 | 0.002148 | 0.002 |
| adaptive_o1 | 0.024939 | 0.004663 | 0.448 |
| context_selected | 1.280630 | 0.029652 | 0.512 |
| fixed_mixer_eta6 | 6.741437 | 0.303312 | 9.508 |

These are one-observation instrument wall times. Context and FixedMix rows are shared family measurements, not additive per-expert costs. Their internal components do not have separately measured standalone costs. State estimates omit/approximate container and allocation overhead; actual process peak RSS is recorded in each raw time receipt. Exact physical decoder cost and a production Pareto frontier are **not measured**. Full byte-tree enumeration is much more work than following one native bit path; do not extrapolate this instrument to FAST/DEFAULT/BEST performance.

The 864.065-bit gain is only 108.008 bytes of **ideal code-length equivalent across all 13 files**, averaging 8.308 bytes per file. This is a break-even overhead budget, not a measured byte saving. A stored six-by-28 table of 16-bit weights would alone be 336 bytes, but a fixed format could specify weights without transmitting that table; generic decoder software must not be invented as wire metadata. Quantization, framing and termination might consume the gain, yet no physical loss is asserted without measurement. The gain fails the predeclared threshold even before these unknowns.

Root used the existing WaveScheduler with one physical core (CPU8), 2 GiB RAM, no swap and 512 MiB temporary cap. All completed phases stayed within their budgets; raw process/time/cgroup receipts distinguish sampled cgroup high-water lower bounds from process peak RSS. Recorded temporary usage reached approximately 244 MB, including retained compressed traces, within the cap. [Per-expert/group cost evidence](costs.json).

## 10. Validation and limitations

Native validation checks normalized distributions, future-suffix invariance, all-byte fixed-mixer interval fidelity across four histories, adaptive/context interval fidelity and frozen codec round trips. Analysis validation checks closed-form duplicate/regime/alternating-context cases, Bayesian evidence identity, a known penalized switch and online suffix invariance. Synthetic cases validate calculations only; they do not select real-data parameters.

Independent streaming verification reproduces primary expert totals, oracle, selected-gate totals and per-file gains, checks every pretarget run length, confirms all trace hashes and unchanged trained weights, and verifies that the reporting-only duplicate-key repair left prior computed evidence byte-identical. [Verification](verification.json), [analysis validation](analysis-validation.json), [independent review](REVIEW.md).

The initial selfcheck expectation and later output-label collision are preserved as failed receipts; neither changed learned parameters or caused a real trace rerun. Full source/trace bindings permit exact source replay; 17-digit floating trace values reproduce ideal-loss analysis, not a portable integer archive protocol.

Limits: short historically exposed prefixes; one deterministic file split; no confidence interval from correlated bytes; no PPM/SEE or optional recurrence-v3 trace; no standalone component cost benchmark; no actual mixed entropy-coded payload. Consequently this is a scoped conclusion for the specified 28-expert set, not a proof that all CIX predictors or larger inputs lack complementary information.

## 11. Prior-art boundary

Probability mixtures, Bayesian log-loss weighting, Hedge, fixed-share switching, CTW, PAQ logistic mixing and universal model mixtures are established. CPI1 combines already implemented predictions with established weighting methods; it demonstrates no new general theory, predictor, gating algorithm or representation class. See the source-linked [prior-art review](PRIOR-ART.md), including [Bayesian sequence prediction](https://arxiv.org/abs/cs/0301014), [CTW](https://doi.org/10.1109/18.382012), [fixed-share tracking](https://doi.org/10.1023/A:1007424614876), and [PAQ context mixing](https://mattmahoney.net/dc/dce.html#Section_43).

## 12. Exactly one evidence-selected next action

**Close CPI1’s frozen 28-expert mixture branch without materializing a physical codec.** Preserve the tiny causal gains, the context-gate rejection, the oracle/null gap, the excluded-model limitations and all evidence. No production integration or expansion follows from this result.
