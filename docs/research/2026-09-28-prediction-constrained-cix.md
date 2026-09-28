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

## Full SAO grid-constraint milestone

Ten full SAO trials independently restore all 7,251,944 bytes. The best is
2,285,288 physical bytes: integer decimal-grid coordinates, exact floating-bit
corrections, and Brotli 11. This saves 2,497,002 bytes against the current complete
portfolio's SAO member and 1,438,639 against PAQ's author-reported -12L SAO result.
The latter is an author comparison; the local PAQ reference has not yet completed.
No updated full-corpus total is inferred from the single-member result.

The record layout is documented by OpenZL. The grid scales are transmitted,
all IEEE corrections are stored exactly, and non-grid values, signed zero, NaNs
and partial records remain lossless. No original-byte lookup is used.
Under xz, conditional type-class ranks cost 2,347,578 bytes versus 2,349,446 for
the same-count arithmetic control and 2,361,130 for raw correction IDs. Under
Brotli, raw IDs win at 2,285,288 versus 2,291,651 ranks and 2,293,792 arithmetic.
This is a substantial additional structural constraint, not proof of a unique
information advantage for enumeration. All ten measurements and provenance are
in `2026-09-28-sao-grid-milestone.json`.

The competitive dispatcher now detects the declared 28-byte record layout and
compares all nine grid/backend candidates with its incumbents. A complete run
is in `results/leaderboard/competitive-grid-v2`. It started from the exact source
hashes committed as `6c7d9fb` immediately after launch, so its recorded startup
HEAD predates that integration commit; source hashes establish the implementation.
Fresh standalone decoding of all twelve selected streams is required before
updating the rank. Do not edit its tracked dependencies while running.

A second controlled experiment uses decoded integer coordinates to predict the
last exact floating correction seen at that coordinate. The table is causal and
requires no transmitted training data. A full physical tournament compares raw
IDs, CIX ranks, and identical-count arithmetic with and without this feedback.
The observational conditional-entropy diagnostic is not a scored result.

Sixteen markup trials also completed, using leaf-context value columns and
stack-constrained closing tags on xml/webster regions. Column separation loses
on all tested regions; stack constraints save eight bytes on one xml prefix
but lose on the middle region. PAQ already predicts this redundancy well.
Preserve the negative evidence in `2026-09-28-markup-constraints.json`; do not
launch full markup runs from this weak result.

## Complete constrained-grid portfolio: 135th equivalent

The parent grid portfolio independently decoded all twelve selected streams:
48,273,958 bytes, equivalent 139th. Mozilla's unchanged stream took 1096.84 seconds
to decode under the concurrent local workload. The parent uses the exact tracked
source committed in 6c7d9fb; its startup HEAD predates that commit as noted above.

Causal correction feedback reduces full SAO to 2,234,479 bytes. Bounded integer
intervals and Rice/raw fallbacks reduce it further to 2,159,749, with every byte
restored. All three final interval controls select the same 47 bounded blocks
and the same remaining Rice blocks. The interval rank saves 3,365 bytes against
fixed-bit coding and 92 against uniform arithmetic. All bound costs are paid.
The same-wrapper feedback control saves 51,267 full-file bytes. PAQ v215 -4 on
the same 64 KiB prefix saves 298 bytes with feedback, from 20,988 to 20,690.
See `2026-09-28-sao-feedback-intervals.json` for complete measurements.

`competitive_grid_refresh.py` exposes an uncached encoder and standalone decoder
for portfolio 3. It adds candidates only where the unchanged source-header
detector recognizes the fixed record layout. The full benchmark refresh checks
all twelve input hashes, physical frame hashes and original independent decode
evidence. Eleven streams are unchanged; their proven decodes are preserved. SAO
is re-encoded across the complete new portfolio and freshly decoded. The final
physical total is **48,148,419 bytes, equivalent 135th among 322 entries**.
This saves 2,622,541 against portfolio 1; 20,322,908 bytes remain above the leader.
No first-place claim is made. Compact evidence is in
`2026-09-28-competitive-grid-milestone.json`; full rows and physical streams are in
`results/leaderboard/competitive-grid-v3`.

All longer PAQ/NCI runs remain independent. Additional v215 -9L runs on Mozilla
and Webster started in `results/leaderboard/paq-v215-priority9L`, two workers,
to address the two largest gaps without waiting for the lower-level cohort queue.
They are not scored until independent extraction completes. No Actions used.

## Database fields, joint values and occupancy feedback

The MySQL/MyISAM database layout is confirmed by the official Silesia description
and OSDB's source schema. `mysql_record_constraints.py` parses 99,998 of 100,000
physical records, retaining the two exceptional/null records literally. It also
preserves noncanonical records and trailing fragments. Record headers and zero
padding are reconstructed only after exact canonical checks. Every field
dictionary and count is transmitted; no source-byte table or generator seed is
part of the codec. The floating/decimal pair shares one joint alphabet.

Five complete Brotli-backed trials independently restore all 10,085,684 bytes:
plain columns 2,355,383; dictionary IDs 1,855,675; fixed-probability arithmetic
1,837,302; remaining-count arithmetic 1,791,424; conditional permutation ranks
1,791,528. The latter uses exact remaining-set ranks for unique keys, exact
multinomial ranks for small cases, and remaining-count arithmetic otherwise.
Global occupancy knowledge saves 45,878 bytes with identical dictionaries and
count metadata. This is a concrete predictive-state gain; arithmetic retains a
104-byte advantage over the blockwise rank representation on the whole member.

PAQ v215 -4 comparisons also improve three independent record-aligned regions:
start (65,536 bytes), middle offset 5,042,924 (65,536), end offset 10,020,228
(65,456). Original PAQ sizes are 18,512 / 18,381 / 18,337. Dictionary-ID controls
are 16,801 / 16,686 / 16,609. Remaining-count arithmetic gives
16,182 / 16,075 / 16,001, and exact ranks give 16,162 / 16,066 / 15,987.
The model and constraints deliver the large gain; rank versus arithmetic differs
by only 9–20 bytes. Two full PAQ v215 -8 candidates (dictionary IDs and
remaining-count arithmetic) are running in `mysql-record-paq-full8`. Do not edit
the codec or its probe while they are live.

A second independent codec infers the fixed width of literal character columns
and transmits the width once. Four further full trials restore exactly:
plain fixed width 1,729,410; six-bit alphabet 1,729,941; remaining-count alphabet
arithmetic 1,729,940; same-count static arithmetic 1,730,011. Near-balanced
compositions save 71 bytes against the static control, but do not beat the simple
fixed-width column under Brotli. Keep the best complete physical representation.
The record, dictionary, ordering, width, alphabet, checksum and exception costs
are all included. Full and regional evidence, hashes, times and source provenance
are in `2026-09-28-mysql-constraints.json`.

Portfolio 4 completed 47,309,374 bytes, equivalent 124th. Portfolio 5 adds the
fixed-width candidate and reuses hash-qualified unchanged streams; inspect
`results/leaderboard/competitive-database-v5/complete.json` for its completed
result. Both expose uncached encoders and standalone decoders; the database
detector uses canonical source record bytes, never filenames or corpus hashes.

Portfolio 5 completed: **47,247,360 physical bytes, equivalent 124th**, with all
twelve exact streams hash-qualified and independent local restoration evidence.
OSDB was freshly re-encoded and decoded; unchanged streams preserve their prior
verified decodes. This saves 901,059 bytes against portfolio 3, leaving
19,421,849 above the leader. A fresh live download confirmed all 322 published
totals unchanged. The compact report is
`2026-09-28-competitive-database-milestone.json`.
