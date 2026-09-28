# Focused directive: prediction shrinks the CIX possibility space

The Silesia first-place objective remains active. The user's latest directive
centres research on PAQ-quality prediction plus conditional CIX representations,
with feedback from CIX structural state to prediction. The decisive question is
whether identical predictive information yields fewer physical bytes through a
smaller residual possibility space. Merely changing the entropy coder does not
demonstrate this hypothesis.

Required directions include conditional multinomials, ranked candidate sets,
inside/outside membership, successes versus exceptions, composition residuals,
context-dependent alphabet partitions and ranks, match removal, transformed
residuals, runs/distances/tokens/fields, hierarchical elimination, recursive
residuals, representation mixtures, and joint model-selection/residual costs.
Reverse feedback includes block compositions, remaining-count deficits,
occupancy, rank prefixes, local entropy, and previous residual composition.

## First controlled experiment

`build_paq_prediction_bridge.py` builds an isolated copy of v215. The reference
binary and all running reference experiments remain untouched. The bridge records
the exact probability and outcome for every coded bit, including block headers
and transformed substreams. A traced archive must be byte-identical to the
ordinary PAQ archive before any result is accepted.

`paq_cix_residual.py` partitions prediction failures by deterministic confidence
bins. It transmits every bin length and failure count. Knowing these counts
restricts the arrangement space to the product of binomial coefficients,
instead of all binary masks. It compares:

1. Original PAQ arithmetic coding, unchanged predictions.
2. Exact integer ranks inside each conditional type class.
3. Arithmetic coding with the identical remaining-count constraint.

The third control matters: any improvement from paid composition knowledge is
separate from a benefit of enumerative ranks themselves. Quantizing confidence
also discards predictive detail, so a loss can reveal quantization or metadata
cost rather than disprove all prediction-constrained CIX designs.

The decoder reads only the CIX frame, reconstructs residual streams, and runs the
PAQ model causally to recover the source. It has no original input, saved
prediction trace, or oracle probability stream. PAQ transforms and model updates
remain in effect. The uncompressed intermediate residual file is decoder work
space, generated entirely from the counted CIX frame.

Record raw coded-event uncertainty, PAQ cross-entropy, conditional combinatorial
uncertainty, composition metadata, physical output, encode/decode time, hashes,
source/binary revisions, and exact restoration. Prefix results are diagnostics,
never full-corpus ranks. Retain original PAQ/CIX streams whenever a candidate loses.

Next refinements depend on these measurements: richer probability-preserving
partitions, smaller context-conditioned candidate alphabets, structural match
removal, and remaining-count feedback. No claim of superiority or disproof is
made before the controlled runs complete.

## Completed first tournament

`results/leaderboard/paq-cix-prefix64k/complete.json` contains 32 independently
decoded trials on 64 KiB prefixes of xml, nci, mozilla and mr at PAQ v215 level 4.
All traced archives match the unmodified reference exactly. Best physical CIX
sizes versus PAQ are 2307/2197, 2080/1964, 8084/7918 and 10807/10610 bytes.
The corresponding identical-constraint arithmetic controls are 2330, 2106,
8134 and 10854 bytes. Source and binary hashes are preserved in the checked-in
`2026-09-28-paq-cix-controlled-prefixes.json` report.

Finer confidence partitions reduce arrangement uncertainty but increase the
paid composition description. For xml, moving from 31 to 248 possible bins
reduces log-cardinality from 2201.37 to 2142.35 bytes, while composition metadata
grows from 74 to 515 bytes. The final stream grows from 2307 to 2718 bytes.
This is a concrete negative result for this fixed-bin construction, not a
disproof of prediction-constrained representations generally. The enumerative
advantage over the arithmetic control is mostly framing/termination overhead.

An unscored feedback diagnostic preserves each original PAQ probability's odds,
adjusted by the remaining-count odds relative to its confidence-bin midpoint.
The estimates in `results/leaderboard/paq-cix-feedback-estimates.json` exclude
all metadata and are not physical codecs or round-trip results. On xml, nci and
mozilla, their residual-only advantage at the coarsest setting is about 20–25
bytes, already less than the current 74–76-byte composition header. Do not
present this as a compression win or repeat it as a scored result.

The next discriminating experiment should reduce the cost of the constraints,
not just replace uniform ranks with a weighted coder: predict composition from
previous matching regions or known structure, code count deviations, and jointly
optimize partitions plus their description. Preserve exact PAQ probability detail
where useful. Include the same-constraint arithmetic control to distinguish a
model/constraint gain from a coder/framing gain. Longer-prefix or full-file work
must carry the predictor and composition state causally across regions.

The independent competitive spatial portfolio has separately completed all 12
Silesia files: 50,770,960 physical bytes, equivalent 159th among the 322-row
snapshot. It includes the 1,671,101-byte MRI volume and 3,560,136-byte X-ray image
modes and fresh restoration of every selected stream. It is not a result for the
new PAQ/CIX residual architecture. The stronger 3,547,548-byte oriented X-ray
experiment remains outside that complete portfolio. Full PAQ v215 -12L and v216
-8 reference cohorts are still running; inspect processes, not these notes, to
establish current state.
