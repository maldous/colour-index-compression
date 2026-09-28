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

## Predicted composition and structural match tests

The H3 codec predicts 16/64/256-event block compositions from a confidence prior,
past counts, or previous composition, then bit-packs exact arrangement ranks.
All 36 physical 64 KiB trials independently restore. Best sizes for xml, nci,
mozilla and mr are 2309, 2077, 8131 and 10888 bytes, still above original PAQ.
Metadata prediction alone did not overcome the lost probability detail.

The CIXW1 bridge uses PAQ's actual match candidate and strength. A token identifies
the first differing bit, or an exact byte match. This forces the matching prefix
and first differing bit; the remaining suffix retains the original PAQ arithmetic
probabilities. Four strength-conditioned token streams compare multinomial ranks,
same-count arithmetic, and an adaptive 9-symbol arithmetic control. Every ordinary
instrumented archive matches the reference, and the filtered probability/outcome
trace is byte-identical to the original trace. All 12 candidates restore without
the original source or probability trace. Best physical sizes are 3971, 3681,
10534 and 12704 bytes: another negative result. Removing a large number of very
cheap decisions is not the same as removing a large coded uncertainty.

Detailed physical evidence, timings, hashes and source provenance for these 48
trials is preserved in `2026-09-28-paq-cix-structural-trials.json`.
An unscored selective-bin diagnostic also found no individual confidence bin whose
rank plus count metadata beat its original PAQ cross-entropy on these prefixes.
Do not spend further full-corpus computation on this fixed-bin construction.

Refine the hypothesis toward information not already present in the PAQ state:
structural relations, known field counts, geometry, and cross-record constraints.
The NCI prefix has directly identifiable coordinate and bond fields; its raw
source is present unchanged after nine coded header bytes. This permits exact
source-field attribution of PAQ loss and controlled reversible structural trials.
Use ordinary PAQ on the same transformed representation as the control, and retain
the original PAQ stream if both structural candidates lose. The user has renewed
the instruction to continue autonomously until a verified first-place total.

## Structural geometry result

`sdf_geometry.py` preserves a V2000 record skeleton and predicts coordinates from
an earlier bonded atom. Unsupported/noncanonical records remain literal. It
compares signed binary residuals, textual residuals, and joint displacement
palettes with atom-type-conditioned compositions. Palette entries, escapes,
counts, type-class payloads, record flags, framing and checksum are all paid.
The palette encoder uses the existing exact type-class codec (enumerative for
short groups, same-count arithmetic beyond its established 2048-event threshold).

Three disjoint 64 KiB windows at offsets 0, 16776722 and 33487909 completed using
v215 -4. Ordinary PAQ sizes are 1964, 2938 and 2334 bytes. Framed textual geometry
residuals plus PAQ are 1631, 2136 and 1797; conditional palette variants are 1823,
2386 and 2058. Every full framed stream restores exactly. This establishes a
structural predictor improvement on these windows, not superiority of CIX's
combinatorial representation over arithmetic coding with the same structure.
See `2026-09-28-sdf-geometry-probes.json` for hashes, costs and timings.

Two complete NCI candidates (textual residuals and conditional palettes, both
v215 -8) are running in `results/leaderboard/sdf-geometry-paq-full8`. Check process
and result state. They do not change the complete 12-file score until restoration
and portfolio integration are complete. The original v215 -12L and v216 -8 full
reference cohorts remain untouched. Next refinements may expose rounded geometric
relations, predict compositions from atom/graph state, or use CIX count deficits
to improve the predictor; always retain the arithmetic control.

## Geometric candidate elimination and ordering constraints

`sdf_hydrogen.py` uses deterministic integer CORDIC geometry. Known heavy-atom
bond directions define a set of hydrogen slots in the largest angular gap.
Each slot is used once, so the skeleton supplies an exact occupancy constraint
without another histogram header. Small residuals retain the actual coordinates,
including unusual layouts. Negative-zero signs are preserved separately.

All 8964 NCI records transform and restore exactly. Among 155971 predicted atoms,
148216 lie within two integer coordinate units of their predicted slot. The
ordering constraint reduces log-cardinality from 115050.30 independent-choice
bits to 60318.77 bits. These are structural measurements, not compressed sizes.

Eighteen 64 KiB physical trials are complete in
`2026-09-28-sdf-hydrogen-probes.json`. PAQ on textual restricted-choice digits gives
1508, 1845, 1631 bytes on start/middle/end, versus original PAQ 1964/2938/2334.
CIX mixed-radix ranks give 1512/1856/1640. Identical-constraint uniform arithmetic
gives 1514/1858/1636; its predictive loss equals the CIX log-cardinality. Adaptive
arithmetic on the same restricted candidate alphabet gives 1509/1844/1630.
Every candidate independently restores. This supports structural prediction and
occupancy feedback, not an intrinsic information advantage of enumerative ranks.
Predictable slot ordering explains why uniform ranks leave savings unused.

The textual-choice and adaptive-choice variants are now running on the entire
NCI member at PAQ v215 -8 in `results/leaderboard/sdf-hydrogen-full8`. Do not edit
`sdf_hydrogen.py` or its probe while this run is live: the runner checks source
immutability. Earlier geometry-only full runs and both reference cohorts remain
live independently. Their cached sources/streams must remain intact.
