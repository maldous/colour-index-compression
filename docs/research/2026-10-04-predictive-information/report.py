"""Render the consolidated report exclusively from retained evidence."""
import csv
import json
from pathlib import Path
import statistics

AREA = Path(__file__).resolve().parent


def read(name):
    return json.loads((AREA / name).read_text())


def main():
    result = read('results.json')
    trained = read('trained.json')
    nulls = read('null-controls.json')
    pairs = read('complementarity.json')
    marginal = read('marginal-information.json')
    residual = read('residual-attribution.json')
    costs = read('costs.json')['experts']
    inputs = read('inputs.json')
    assert not result['material_gate_pass']
    lines = ['# CIX / Six complementary predictive information audit — CPI1', '',
        '**Decision: a small causal improvement exists in the frozen 28-expert set, but it does not clear the material-gain gate. Do not build a physical mixed codec from this result.**', '',
        f"The development-selected context gate saves **{result['captured_bits']:.3f} ideal bits ({result['gain_percent']:.4f}%; {result['captured_bits_per_byte']:.6f} bits/input-byte)** against the strongest constituent, the existing FixedMix eta-6 composite. It captures only **{result['captured_gap_percent']:.4f}%** of the hindsight gap. The gate loses to simple fixed-share online weighting on held-out data and is rejected. The ordinary fixed-share result is also below the material threshold.", '',
        'This is a bounded predictive-information audit, not a compression leaderboard or an archive-size result. There is no new compression-theory claim. Existing production CIX and the closed numeric composition result remain unchanged.', '',
        '## 1. Scope, frozen evidence and exposure', '',
        'Checkpoint `20e18503b` on `research/silesia-competitive`; native predictor source copied from incumbent `d3a2cd416`. Source hashes, mechanical doc-comment rewrite, binary identity, input ranges and settings are bound in [freeze.json](freeze.json), [binary.json](binary.json), [inputs.json](inputs.json) and [trained.json](trained.json).', '',
        'All 33 existing Canterbury/Calgary/Artificial members were traced, at most 4096 bytes each. Sorted even/odd file positions within each family define development/held-out membership. This is a CCA prefix integrity screen, not completion of full-file CCA compression qualification. No Silesia, Hutter, acquisition, Sites or Actions jobs ran.', '',
        f"Primary held-out evidence is **{result['real_files']} real files / {result['real_heldout_bytes']:,} bytes**. Artificial files are separate controls. Before held-out extraction, `calgary-pic` was quarantined because its sampled bytes duplicate development `canterbury-ptt5`; its result is retained separately. [Exposure amendment](EXPOSURE-AMENDMENT.md). These are historically exposed corpus assets, held out only from this instrument's fitting. Neither file balance nor a small prefix screen establishes broad transfer.", '',
        '| Split | Files | Bytes | Role |', '|---|---:|---:|---|']
    for split in ['development', 'heldout']:
        for family in ['canterbury', 'calgary', 'artificial']:
            selected = [row for row in inputs if row['split'] == split and row['family'] == family]
            lines.append(f"| {split} / {family} | {len(selected)} | {sum(row['bytes'] for row in selected):,} | {'diagnostic' if family == 'artificial' else 'one held-out duplicate excluded' if split == 'heldout' and family == 'calgary' else 'real data'} |")
    lines += ['', '## 2. Actual model inventory and common interface', '',
        '| Implemented mechanism | State / predicted unit | Causal probability and audit disposition |', '|---|---|---|',
        '| Adaptive frequencies, orders 0/1 | Counts and Fenwick tree per history bucket; byte | Integer masses `2c+1`, total `2seen+256`; normalized, adaptive, independently replayable; traced. |',
        '| Context-expert orders 0/1/2/4 | Sorted counts per preceding suffix; byte | Additive-one normalized frequencies; all tables updated after observation; four traced experts. |',
        '| Context-expert selector, mode 17 | Prior exponentially decayed losses plus those tables; byte | Chooses one model before target; traced as causal selection, not probability mixing. Native floating update retained; no new integer-codec claim. |',
        '| FixedMix v1 eta=6 | 13 pattern tables, six lags 1/2/4/8/16/32, match4, per-bit reliability, weights/bias, bounded history; bit | Already internally mixed. All 20 components and full existing composite traced as exact conditional-bit products over bytes. |',
        '| Corrected recurrence v3 / legacy v2 | Previous-byte recurrence-distance feature, reliability buckets and additional mixer weight | Implemented optional native extension; **untraced in CPI1**. Current registered CIXG route uses v1. V2 lookup-after-observe collapses the recurrence feature; v3 corrects it. No global claim about this unmeasured signal. |',
        '| PPM fixed escape / SEE | Context counts, exclusion and escape state; sequential escape/hit/fallback symbols | Causal native coding paths can be subnormalized over the byte alphabet. The full-alphabet method-1 selfcheck gives reachable byte mass **0.5**, not 1. Excluded rather than silently renormalized. No per-real-position PPM loss claim. |',
        '| LZ and phrase parsers | Match/token history plus encoder token search; matches and tokens | Actual parser routes do not expose an original-next-byte normalized distribution. Only FixedMix\'s existing causal match4 signal is traced. |',
        '| Runs, composition/counts | Run lengths/positions or paid block count vectors | Future run extent and final block statistics are not causal original-byte experts; excluded. A valid paid count-conditioned coder is not an eligible history-only forecast. |',
        '| Stride/periodic residuals, BWT, numeric, wavelet, bitplane, chains | Transformed symbols/blocks and selected transform descriptions | Transforms/routes, not additional comparable original-byte probability experts. FixedMix lag signals are separately eligible. |',
        '| Arithmetic/range, count-range, Huffman and nested/external coding | Intervals or transformed substreams | Coders/backends; range coding itself contributes no predictive signal. |',
        '| Whole-input portfolio / local routing | Finished candidate archives or regions | Post-encoding selection, not predictive mixing; excluded from ideal mixture table. |',
        '| Python-only CTW and retained research variants | Reference/research models | Not dispatched by current native CIX; excluded from this native screen. |', '',
        'The [code-grounded inventory](INVENTORY.md) provides file/line anchors, state, transform dependence and replay details. Each traced expert exposes a normalized byte distribution before scoring the target; `observe(actual)` follows. No final counts, transform search, source name or future bytes enter prediction. Full distributions are temporary; traces retain actual probability, entropy, maximum mass, argmax, pretarget run/match/context-selection diagnostics and normalized noise forecasts.', '',
        'For FixedMix, the 255-node byte-prefix tree multiplies the native conditional bit probabilities. Earlier bit updates affect only that bit\'s keyed state, so enumeration from the pre-byte state matches sequential native updates. Selfcheck tests all 256 candidates across four histories against sequential native bit intervals. Components remain derived from shared native state; they are not independently trained replacement compressors.', '',
        '## 3. Held-out first decision table', '',
        '**Every number below is ideal predictive bits, not payload bytes or complete archive bytes.** Best single is the aggregate-best constituent; it is also the best on every primary held-out file and was selected on development. Highest-probability positions count ties within absolute tolerance 1e-12.', '',
        '| Expert / method | Ideal bits | Bits/input-byte | Highest-probability positions |', '|---|---:|---:|---:|']
    for row in result['rows']:
        lines.append(f"| {row['name']} | {row['ideal_bits']:.3f} | {row['bits_per_input_byte']:.6f} | {row.get('highest_probability_positions', '—')} |")
    lines += ['', f"Best single: **{result['best_single_bits']:.3f} bits**. Hindsight gap: **{result['oracle_gap_bits']:.3f} bits ({100*result['oracle_gap_bits']/result['best_single_bits']:.3f}%)**. Selected causal capture: **{result['captured_bits']:.3f} bits**, or **{result['captured_gap_percent']:.3f}% of the oracle gap**. Remaining hindsight gap: **{result['remaining_oracle_gap_bits']:.3f} bits**.", '',
        '**HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY.** It sees the realised symbol before choosing an expert. Its gap is not achievable compression and cannot be charged as an archive saving.', '',
        '## 4. Static, online, context and switching controls', '',
        'Static weights use 500 deterministic EM steps on development real files only. The non-negligible global weights are: ' + ', '.join(f"`{name}` {weight:.6f}" for name, weight in zip(trained['names'], trained['static']) if weight > 0.001) + '. Other weights remain at approximately the 1e-12 numerical floor.', '',
        f"Development selected Hedge eta={trained['eta']}, fixed-share eta={trained['share_eta']} and alpha={trained['alpha']}. All online methods predict before weight updates and reset to uniform per file. Eta=1 is the Bayesian baseline (with numerical underflow protection); fixed-share permits transitions between experts. No held-out hyperparameter fitting occurred.", '',
        'The six-bucket context gate uses only prior run length crossed with prior match availability. Its development-fitted weights are frozen with shrinkage to the global static mixture. **It is rejected:** its held-out 162270.288 bits are worse than simple fixed-share\'s 162196.829 bits. Fixed-share improves by 937.523 ideal bits (0.5747%; 0.017607 bits/input-byte), still below both material thresholds. The development-selected method is not silently replaced by the held-out winner.', '',
        f"The penalized hindsight switching path costs **{sum(row['bits'] for row in result['switching']):.3f} bits** with **{sum(row['switches'] for row in result['switching'])} switches**, including log2(28) initial identity and exact stay/change negative-log penalties. This is a **noncausal comparator**, not a deployable path selector. The causal fixed-share forward method has separate results. The weighted simultaneous probability mixture can beat a single penalized path; no architectural classification is inferred from switches alone.", '',
        '| Primary held-out file | Selected gate gain over file-best, ideal bits |', '|---|---:|']
    for row in result['files']:
        if row['family'] != 'artificial' and not row.get('exclude_from_primary'):
            lines.append(f"| {row['label']} | {row['captured_bits']:.3f} |")
    lines += ['', 'The gate wins on 12/13 real files, but loses 237.094 bits on `calgary-geo`. Artificial `aaa` and `random` gains are approximately +3.20 and −407.39 bits; they never enter the primary decision. The duplicate `calgary-pic` is retained but excluded.', '',
        '## 5. Null-oracle controls', '',
        '| Null | Hindsight gap, bits | Causal Bayesian capture, bits | Interpretation |', '|---|---:|---:|---|']
    for key, label in [('duplicate', 'Duplicate best-development expert'), ('redundant_uniform_smoothing', 'Uniform-smoothed redundant copies'), ('weak', 'Uniform + adaptive order0')]:
        row = nulls[key]
        lines.append(f"| {label} | {row['oracle_gap']:.3f} | {row['causal_captured_bits']:.3f} | Normalized distributions; no new history signal |")
    noise = nulls['independent_noisy_copies_of_one_expert']
    lines += [f"| Four noisy copies of one informative expert | {noise['oracle_gap']:.3f} | {noise['best_single_bits']-noise['causal_bayes_bits']:.3f} | Independent perturbations conditional on a common informative base |",
        f"| Independent weak random-symbol forecasts | {nulls['independent_random_symbol_weak']['oracle_gap']:.3f} | not selected | No matched-quality claim |",
        f"| Alignment-broken realised-loss columns, 16 repeats | median {statistics.median(row['oracle_gap'] for row in nulls['alignment_broken']['repetitions']):.3f} | **invalid** | Oracle bias diagnostic only; not valid aligned forecasts |", '',
        'The informative-base perturbations use exp(±0.25) factors generated independently of the target, then normalize across all 256 symbols before scoring. Their average loss is near the base, but their 7.685% hindsight gap appears without a new causal source. This directly demonstrates oracle selection advantage. Redundant smoothing alone also captures 326.128 bits through ordinary calibration. The measured 864.065-bit primary gain exceeds those causal null captures, but the nulls do not support a statistical-significance or wholly new-information claim.', '',
        'Four independently perturbed copies of the entire expert bank change average individual losses by approximately 0.0395–0.0402 bits/byte. They produce hindsight gaps around 50.5k bits and selected-gate captures of 1141–1182 bits. Randomness can enlarge both apparent oracle complementarity and variance-reduction benefit. Entirely independent random-symbol forecasts have substantially worse marginal quality; they are not represented as quality-matched controls. [All null results](null-controls.json).', '',
        '## 6. Complementarity and conditional error tails', '',
        'The complete [pair matrix](complementarity.json) contains every pair: directional >1/>4-bit wins, loss correlation, argmax disagreements, mean absolute disagreement, and high-loss/uncertainty conditional tails. The compact examples below use the same frozen held-out positions.', '',
        '| Pair: first / second | Correlation | First >1-bit wins | Second >1-bit wins | Argmax disagreement | First gain when second loses >8 bits |', '|---|---:|---:|---:|---:|---:|']
    selected_pairs = [('fixed_pattern_1', 'fixed_mixer_eta6'), ('fixed_match4', 'fixed_mixer_eta6'), ('context_o4', 'fixed_match4'), ('adaptive_o0', 'fixed_mixer_eta6'), ('fixed_lag_4', 'fixed_mixer_eta6')]
    for first, second in selected_pairs:
        row = next(row for row in pairs if row['first'] == first and row['second'] == second)
        lines.append(f"| {first} / {second} | {row['correlation']:.4f} | {row['first_wins_1bit']} | {row['second_wins_1bit']} | {100*row['disagreement_fraction']:.2f}% | {row['first_gain_when_second_loss_above8']:.3f} |")
    lines += ['', 'These measure prediction errors, not proof that a particular structural mechanism causes a miss. PPM-versus-LZ and count-rescue questions remain unmeasured because those full routes do not supply an eligible normalized common forecast. `fixed_match4` is the actual four-byte-following-byte predictor, not the LZ parser. Lag signals likewise are not the excluded numeric transforms.', '',
        '## 7. Operational marginal information', '',
        'Each static leave-one-out control is refitted on development only; online controls remove an expert without retuning the frozen rule. Positive removal cost means that expert helped the full mixture; negative values are retained.', '',
        '| Expert | Static removal cost, ideal bits | Fixed-share removal cost, ideal bits |', '|---|---:|---:|']
    for row in sorted(marginal, key=lambda row: row['static_removal_cost_bits'], reverse=True):
        lines.append(f"| {row['expert']} | {row['static_removal_cost_bits']:.3f} | {row.get('fixed_share_removal_cost_bits', 0):.3f} |")
    lines += ['', 'The existing composite dominates: removing it costs roughly 43.9k static-mixture bits. The clearest additional static contribution is its own order-1 pattern component (~323 bits). The non-negligible fitted weights are all the composite or signals already inside it. This supports a small recalibration opportunity; it does not show that alternative route families conceal a large new information reservoir.', '',
        '## 8. Residual-bit attribution', '',
        f"Relative to the **noncausal** per-position oracle, **{100*residual['positions_fraction_for_excess']['50']:.2f}%** of positions account for 50% of positive excess bits; **{100*residual['positions_fraction_for_excess']['90']:.2f}%** account for 90%. This concentration is descriptive, not an achievable regret bound.", '',
        '| Oracle rescuer identity | Attributed excess bits | Fraction of excess |', '|---|---:|---:|']
    for name, bits in sorted(residual['rescuer_identity_bits'].items(), key=lambda item: item[1], reverse=True)[:8]:
        lines.append(f"| {name} | {bits:.3f} | {100*bits/residual['excess_bits']:.2f}% |")
    lines += ['', 'Ties use the frozen expert order, so this table does not uniquely allocate shared information. Pretarget run/match bucket totals and the 20 largest contiguous >1-bit excess clusters are retained in [residual-attribution.json](residual-attribution.json). No causal labels such as “PPM failure”, “missed LZ recurrence” or “rare-count effect” are assigned without an eligible measured predictor.', '',
        '## 9. Computation, state and overhead assessment', '',
        '| Measured family, primary held-out set | Distribution enumeration seconds | State-update seconds | Maximum estimated family state, MiB |', '|---|---:|---:|---:|']
    for name in ['adaptive_o0', 'adaptive_o1', 'context_selected', 'fixed_mixer_eta6']:
        row = costs[name]
        lines.append(f"| {name} | {row['predict_group_seconds']:.6f} | {row['update_group_seconds']:.6f} | {row['maximum_estimated_group_state_bytes']/1048576:.3f} |")
    lines += ['', 'These are one-observation instrument wall times. Context and FixedMix rows are shared family measurements, not additive per-expert costs. Their internal components do not have separately measured standalone costs. State estimates omit/approximate container and allocation overhead; actual process peak RSS is recorded in each raw time receipt. Exact physical decoder cost and a production Pareto frontier are **not measured**. Full byte-tree enumeration is much more work than following one native bit path; do not extrapolate this instrument to FAST/DEFAULT/BEST performance.', '',
        'The 864.065-bit gain is only 108.008 bytes of **ideal code-length equivalent across all 13 files**, averaging 8.308 bytes per file. This is a break-even overhead budget, not a measured byte saving. A stored six-by-28 table of 16-bit weights would alone be 336 bytes, but a fixed format could specify weights without transmitting that table; generic decoder software must not be invented as wire metadata. Quantization, framing and termination might consume the gain, yet no physical loss is asserted without measurement. The gain fails the predeclared threshold even before these unknowns.', '',
        'Root used the existing WaveScheduler with one physical core (CPU8), 2 GiB RAM, no swap and 512 MiB temporary cap. All completed phases stayed within their budgets; raw process/time/cgroup receipts distinguish sampled cgroup high-water lower bounds from process peak RSS. Recorded temporary usage reached approximately 244 MB, including retained compressed traces, within the cap. [Per-expert/group cost evidence](costs.json).', '',
        '## 10. Validation and limitations', '',
        'Native validation checks normalized distributions, future-suffix invariance, all-byte fixed-mixer interval fidelity across four histories, adaptive/context interval fidelity and frozen codec round trips. Analysis validation checks closed-form duplicate/regime/alternating-context cases, Bayesian evidence identity, a known penalized switch and online suffix invariance. Synthetic cases validate calculations only; they do not select real-data parameters.', '',
        'Independent streaming verification reproduces primary expert totals, oracle, selected-gate totals and per-file gains, checks every pretarget run length, confirms all trace hashes and unchanged trained weights, and verifies that the reporting-only duplicate-key repair left prior computed evidence byte-identical. [Verification](verification.json), [analysis validation](analysis-validation.json), [independent review](REVIEW.md).', '',
        'The initial selfcheck expectation and later output-label collision are preserved as failed receipts; neither changed learned parameters or caused a real trace rerun. Full source/trace bindings permit exact source replay; 17-digit floating trace values reproduce ideal-loss analysis, not a portable integer archive protocol.', '',
        'Limits: short historically exposed prefixes; one deterministic file split; no confidence interval from correlated bytes; no PPM/SEE or optional recurrence-v3 trace; no standalone component cost benchmark; no actual mixed entropy-coded payload. Consequently this is a scoped conclusion for the specified 28-expert set, not a proof that all CIX predictors or larger inputs lack complementary information.', '',
        '## 11. Prior-art boundary', '',
        'Probability mixtures, Bayesian log-loss weighting, Hedge, fixed-share switching, CTW, PAQ logistic mixing and universal model mixtures are established. CPI1 combines already implemented predictions with established weighting methods; it demonstrates no new general theory, predictor, gating algorithm or representation class. See the source-linked [prior-art review](PRIOR-ART.md), including [Bayesian sequence prediction](https://arxiv.org/abs/cs/0301014), [CTW](https://doi.org/10.1109/18.382012), [fixed-share tracking](https://doi.org/10.1023/A:1007424614876), and [PAQ context mixing](https://mattmahoney.net/dc/dce.html#Section_43).', '',
        '## 12. Exactly one evidence-selected next action', '',
        '**Close CPI1’s frozen 28-expert mixture branch without materializing a physical codec.** Preserve the tiny causal gains, the context-gate rejection, the oracle/null gap, the excluded-model limitations and all evidence. No production integration or expansion follows from this result.', '']
    (AREA / 'REPORT.md').write_text('\n'.join(lines))
    with (AREA / 'complementarity.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)


if __name__ == '__main__':
    main()
