# CPI1 final independent review

**Review type:** read-only review of the frozen CPI1 source, freeze and split
records, held-out outputs, and reporting scope.  No experiment was run and no
implementation file was changed by this review.

## Finding

The reported first-decision result is internally consistent for the **traced
CIXG-focused expert set**.  It does **not** pass the predeclared material gate:
the frozen context gate saves 864.065 ideal bits on 53,248 primary real
held-out bytes (0.01623 bits/byte, 0.5297%), below the required 0.05
bits/byte and 1%.  It beats the per-file best single expert on 12 of 13 files,
but that does not overcome the two aggregate thresholds.  `results.json`
labels the values ideal-only and returns `material_gate_pass: false`.

This supports closing the physical-codec promotion path for this exact traced
set.  It does not support a claim that every implemented CIX predictive
mechanism has been exhaustively ruled out.

## Causal and analysis review

* The trace forms each adaptive, context-expert and FixedMix byte
  distribution before it passes the actual byte to metrics or `observe`.  The
  FixedMix prefix-tree enumeration holds state fixed throughout a candidate
  byte, and the self-check compares every enumerated composite probability
  with the native sequential bit intervals.  I found no target leakage in
  this path.
* The expert table is coherent: 2 adaptive experts, 4 context orders plus
  their existing causal selector, 20 FixedMix components, and the FixedMix
  composite give 28 columns.  PPM is correctly excluded from the normalized
  table after the native method-1 full-alphabet check found direct byte mass
  1/2.
* Static weights, online choices and context-gate weights were trained from
  development traces; `trained.json` is hash-bound in `freeze.json` before
  held-out tracing.  Evaluation uses those frozen choices, not held-out
  tuning.
* The oracle remains clearly labelled non-causal.  Duplicate, redundant,
  weak, broken-alignment, perturbation and independent-noisy-copy controls are
  separately labelled.  Broken alignment is used only as an invalid
  oracle-selection-bias diagnostic, not as a causal mixture result.
* The planned 16 repetitions apply to the alignment diagnostic.  The four
  normalized perturbations are a distinct control.  The unmatched random
  symbol control acknowledges its quality limitation; the same-expert noisy
  copies provide the informative marginal-quality control relevant to the
  decision comparison.

## Exposure and chronology

The duplicate 4096-byte input (`canterbury-ptt5` development,
`calgary-pic` held out) was identified after development fitting and before
held-out primary analysis.  The amendment quarantines `calgary-pic` from the
primary mixture, null, marginal and decision calculations while retaining it
as explicitly flagged evidence.  The remaining primary real held-out set has
13 files and 53,248 bytes, matching `results.json`.

The amendment retains the prior freeze and analysis source, says the trained
bytes are unchanged, and records the pre-held-out trained hash in the amended
freeze.  This is a suitable corrective quarantine.  It must be described as
an instrument-level held-out split, not evidence the files were globally
unseen.

## Scope limits that must remain in the report

1. **Corrected FixedMix recurrence v3 is implemented but untraced.** CPI1
   traces the recurrence-disabled CIXG route-9 FixedMix configuration.  The
   corrected v3 recurrence API is not selected by that route and was not
   included as a separate expert.  The historical v2 lookup-after-observe
   variant remains preserved but is not valid prospective evidence.  The
   current result therefore cannot close the broader predictive-mixture
   question for corrected v3 recurrence.
2. **Costs are instrumentation estimates.** The summaries report shared
   family timing/state estimates and explicitly say they are not additive;
   the analysis result does not combine them into a Pareto claim.  Do not
   report production CPU, memory, or bits-saved-per-cost conclusions from
   CPI1.
3. **Trace precision is floating diagnostic evidence.** Source, binary and
   compressed trace hashes bind the run, but the retained rows contain
   17-digit realised probabilities rather than every integer numerator,
   denominator and state identifier.  The output supports the recorded
   mixture calculations, not an independent bit-exact reconstruction of
   every extractor state.
4. **The result is not a physical archive measurement.** Ideal log loss is
   not payload or complete archive bytes; no promotion follows from this
   diagnostic result.

## Evidence-selected next action

Do not build a physical mixed codec.  Preserve CPI1 as a negative
qualification result for its traced set.  If the research question must cover
all implemented native predictors rather than only current CIXG routes, the
one justified follow-up is a separately frozen, isolated trace of corrected
FixedMix recurrence v3 with the same causal and held-out protocol.
