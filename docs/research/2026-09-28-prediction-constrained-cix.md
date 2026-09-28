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

## Newly completed NCI palette candidate — integrate next

The full `sdf-geometry-paq-full8/2-2` candidate completed independent decoding:
**572,416 physical bytes**, all 33,553,445 source bytes restored. This is 204,217
bytes below PAQ's author-reported -12L NCI size. It uses the earlier bonded
coordinate model, displacement palette and type classes, then PAQ v215 -8.
The physical CIXG frame, original input and current geometry source hashes were
checked again after completion. Encode took 2789.04 seconds; decode 3289.39.

It is not included in portfolio 5 or the published 124th-place total yet.
Compact provenance: `2026-09-28-nci-full-palette.json`. The next concrete task is
to integrate completed chemical candidates without invalidating ongoing runs or
wasting an hour repeating already proven extraction. Reuse independently decoded
streams only after exact input/frame/source/backend provenance checks, as for
unchanged portfolio members; keep an uncached reproducible encoder and a
standalone decoder. The other full chemical candidates and raw references must
be checked from live process/artifact state before deciding which to retain.

## Complete PAQ-backed constraint integration and bounded reference portfolio

The completed NCI palette frame was qualified into portfolio 6, giving
45,328,656 bytes (103rd equivalent). Optional cache reuse checks the complete
input, physical stream, source, backend, independent extraction evidence and
recomputed/inverted structural transform; uncached encoding remains available.
A fresh prefix encode matches the old physical stream exactly and decodes.

Portfolio 7 adds the completed v216 -8 backend with a reproducible compute gate:
inputs at most 12 MiB, excluding detected MyISAM records. The ordinary encoder
runs PAQ from the input; hashes only identify optional, independently restored
cached artifacts. The six-byte CIX header replaces the six-byte PAQ header
without changing physical size or payload. It completed **42,393,159 bytes,
87th equivalent**. Seven reference members have completed, including SAO at
3,730,635 bytes, confirming the selected 2,159,749-byte CIX SAO stream also wins
against an independently measured full-file PAQ configuration (v216 -8, not -12L).

The second full geometry candidate now completes **504,363 bytes** on NCI.
Textual bonded-coordinate residuals beat the palette/type-class representation
by 68,053 bytes after PAQ v215 -8. The structural model is useful; enumerative
palette coding is not the best final representation. Independent decoding took
3711.33 seconds after 3196.87 seconds encoding. Hydrogen-slot candidates remain
separate ongoing experiments.

Both full OSDB PAQ v215 -8 comparisons also completed: dictionary IDs
**1,723,002 bytes**, remaining-count arithmetic **1,698,992 bytes**. The latter
saves 24,010 bytes with the same field dictionaries and backend, and 30,418
against the earlier selected fixed-width/Brotli candidate. This is additional
full-file evidence for the CIX structural-state feedback direction.

Portfolio 8 qualifies the textual geometry and remaining-count database frames
without repeating their hour-long extraction. All twelve exact physical streams
retain independent full local restoration evidence. Final total:
**42,294,688 bytes, equivalent 84th among 322 entries**; 14,469,177 bytes remain
above the 27,825,511-byte leader. The live page was downloaded again at
2026-09-28T15:49:04Z and its SHA is unchanged. Compact complete evidence is in
`2026-09-28-competitive-paq-constraints-milestone.json`; controlled full-file
comparisons are in `2026-09-28-full-paq-structural-comparisons.json`.
New qualification checks passed seven tests in total across the chemical,
bounded-reference and refreshed-constraint modules; both refreshed uncached
prefix encoders reproduce the earlier streams and independently decode.

Exploratory cross-column OSDB counts show almost all 10,000 pairs across each
pair of 100-value columns. Empirical mutual information is only 0.070–0.074 bits,
consistent with sparse-count estimation noise; no deterministic cross-column
relation is established. Do not invent a joint-value constraint from this.
Next small test: combine inferred fixed widths with PAQ and compare literal,
six-bit and remaining-count representations, preserving the best physical frame.
The original full reference and Mozilla/Webster priority runs continue locally.
No Actions or source-repository push was used. Public-source eligibility remains
pending; numerical position is not an official listing or first place.

## Completed hydrogen slots, standalone reproduction and next database trials

Both hydrogen-slot full streams completed independent extraction. PAQ choice
text: **447,748 bytes**. Adaptive constrained arithmetic: **447,749 bytes**.
All 8,964 records and 339,696 atoms restore, including negative zero. Geometric
prediction locates 148,216 of 155,971 predicted atoms within two coordinate
units. Independent slot uncertainty is 115,050.30 bits; using each slot once
reduces combinatorial log-cardinality to 60,318.77 bits; adaptive ordering costs
4,888.20 predictive bits and a 614-byte intermediate payload. PAQ on the plain
choice digits produces an almost identical final stream. The model supplies the
important improvement; mere reduction in uniform cardinality is insufficient to
outperform an adaptive probability model of the same choices.

Portfolio 9 qualifies the 447,748-byte physical frame. Complete twelve-member
total **42,238,073 bytes, still equivalent 84th**, gap **14,412,562 bytes**. The
selected NCI stream is 328,885 bytes below the author's -12L value, but the full
local -12L NCI reference remains in progress. Eight v216 -8 reference members
have now completed: the new OSDB reference is 2,018,086 bytes, independently
confirming the selected 1,698,992-byte CIX database model wins against this
configuration by 319,094 bytes. No change to the complete total from that losing
reference. Full evidence: `2026-09-28-nci-hydrogen-full.json` and
`2026-09-28-competitive-hydrogen-milestone.json`.

The fresh hydrogen prefix exactly reproduces the original 1,508-byte stream and
restores independently. Qualification correctly rejected the old prefix's stale
source hash (it predates added arithmetic controls); the current full trial
qualifies. Two tests pass. `benchmarks.competitive_cli` now provides an entirely
uncached encoder and standalone decoder. A fresh 992-byte mixed probe compresses
to 67 bytes and restores in a separate process; the encoder independently
verifies before writing. It refuses existing output paths. Reproduction notes
are in `competitive-reproduction.md`; public source packaging remains pending.

Nine fixed-field/PAQ probes have completed across three independent database
regions. Fixed width plus six-bit alphabet yields **16,135 / 16,029 / 15,953**
bytes, versus the previous same-backend remaining-count representation
16,182 / 16,075 / 16,001. Replacing six-bit letters with remaining-count arithmetic
is slightly larger on each region. Full modes 2 and 3 at PAQ v215 -8 now run in
`results/leaderboard/mysql-fixed-paq-full8` (two workers); do not edit
`mysql_fixed_paq.py`, `mysql_fixed_columns.py` or their dependencies while live.
No partial or projected size is scored. The framed checksum/partial-record test
passes. The original PAQ references and Mozilla/Webster priority comparisons
remain active; inspect actual state before restarting anything.

Next structural hypothesis: known earlier heavy-atom coordinates and the bond
graph may restrict heavy-atom placement to a small set of angular or circle-
intersection candidates, just as hydrogen slots do. Start with measured bond
length/angle distributions and three short independent regions; transmit any
learned lengths and preserve exact residuals. Do not assume arbitrary molecules
obey the drawing model. Retain the incumbent unless actual complete bytes win.

The initial heavy-atom diagnostic is complete (not a compression result):
183,608 heavy atoms; 140,023 have one earlier heavy neighbour, 26,662 have two,
and 278 have three or more. The dominant heavy-bond length is 10,000 coordinate
units (173,133 edges when rounded to 100 units). Frequent displacements follow
hexagonal drawing directions, with exact +/-1 rounding residuals. These measured
facts motivate relative angular candidates and two-circle intersections. Any
inferred radius must be carried in the frame; deviations remain exact residuals.
Evidence: `2026-09-28-heavy-atom-diagnostic.json`.

## Heavy-atom candidate tournament and complete PAQ medium-input tier

`sdf_heavy.py` keeps the proven hydrogen skeleton and changes coordinate
residuals using a radius inferred from input bonds and transmitted in the frame.
Absolute directions, relative bond angles and two-neighbour circle intersections
produce causal candidate sets; occupied bond directions are excluded, while
unrestricted exact residuals preserve all deviations. Five tests cover arbitrary
3D layouts, signed zero, partial records, circle candidates and uniform-control
uncertainty equality. All 21 PAQ v215 -4 regional physical trials restore exactly.

Best (circle/relative model with adaptive choices): **1501 / 1840 / 1618 bytes**,
versus the incumbent hydrogen-only model **1508 / 1845 / 1631**. Gains are modest:
7 / 5 / 13 bytes. With identical candidate sets, uniform ranks yield
1544 / 1869 / 1652 and uniform arithmetic 1547 / 1870 / 1659. Rank framing saves
only 1–7 bytes; adaptive modelling of candidate choices is much more useful.
The summed log candidate counts is conditional uniform path uncertainty, not a
claim that all future branching counts are independent of the chosen path.

The complete structural transform was independently inverted before starting
an expensive PAQ trial. All 33,553,445 bytes restore; 166,963 heavy atoms receive
multiple candidates and 130,843 residuals are within two units. Conditional
uniform choice uncertainty is 411,554.28 bits; the adaptive model costs
214,964.85 predictive bits, with 26,874 physical intermediate choice bytes.
The full model3/representation3 trial is now running in `sdf-heavy-full8`.
Do not edit the heavy codec/probe or their dependencies while it is live. No full
compressed-size improvement is claimed yet. Compact evidence is
`2026-09-28-sdf-heavy-probes.json`.

Two more ordinary PAQ v216 -8 references completed: **NCI 809,461 bytes** and
**Samba 1,625,132 bytes**. NCI retains the stronger 447,748-byte CIX structural
stream. The fixed PAQ compute tier now extends from 12 to 24 MiB using input
length and the existing database detector, never filenames or corpus hashes.
Portfolio 10 qualifies the exact independently restored Samba archive with an
invertible six-byte header substitution and no physical size increase.

Complete result: **39,607,610 physical bytes, equivalent 66th among 322 entries**.
All 12 streams have independent full local restoration evidence; exact source,
input, backend and physical artifact identities are rechecked. This saves
2,630,463 bytes against portfolio 9, leaving **11,782,099 bytes** above the leader.
The live leaderboard page was downloaded again and its SHA is unchanged.
Evidence: `2026-09-28-competitive-medium-paq-milestone.json` and
`2026-09-28-paq-nci-samba-local.json`. Mozilla and Webster remain the largest gaps.

An isolated corpus-free source bundle is rebuilding in
`/tmp/cix-reproduction-20260928`, through `benchmarks.reproduce_build`, with three
compiler workers. It includes CIX source plus pinned PAQ sources and upstream
notices, excludes GitHub workflows, corpus bytes, saved streams and binaries,
and never performs network/CI operations. All four freshly built CIX native
libraries are already byte-identical to the qualified originals; PAQ builds
continue. This is a local release candidate only, not public source eligibility
or an official submission. Its CLI currently selects portfolio 9; after build
qualification, refresh the release candidate/CLI to the latest complete policy.

The fixed-field full PAQ follow-up is now a verified negative result: six-bit
alphabet **1,728,106 bytes**, remaining-count alphabet **1,728,093 bytes**.
Both restore independently, but exceed the incumbent 1,698,992-byte database
stream by 29,114 / 29,101 bytes. Regional gains did not survive whole-file PAQ
model interactions. No portfolio addition. Evidence is in
`2026-09-28-mysql-fixed-paq-full-negative.json`.

The isolated build completed successfully: all four CIX native libraries AND
both PAQ backends are byte-identical to the qualified original binaries. A
fresh uncached portfolio-10 API smoke test in the isolated tree, with no corpus
present, reproduces the original 67-byte stream from a 992-byte mixed input and
restores exactly. The main CLI is now updated to portfolio 10; the staged archive
still has the portfolio-9 CLI default but includes the portfolio-10 API.
Do not publish that archive as a final release without refreshing the default
and source revision. `2026-09-28-isolated-build-qualification.json` records source
archive/manifest hashes, six binary matches and the isolated smoke result.

## Mozilla linker-table constraints

134 Alpha ECOFF objects are recognized by their actual headers inside the TAR
stream. Symbol names plus relocation indices determine canonical hash/msym
tables. Only exact reconstruction matches are replaced with zeros; unknown or
noncanonical layouts remain literal. Byte positions and executable code remain
unchanged, preserving PAQ instruction detection. The full structural transform
restores all 51,220,480 input bytes, deriving 1,760,988 table bytes with 833 bytes
of control metadata. This alone is not a compressed-size result.

All 15 physical PAQ v215 -4 trials on three complete embedded objects restore.
Ordinary PAQ sizes: **13,003 / 42,539 / 42,151**. Derived-table mode:
**11,830 / 41,335 / 41,527**, saving 1,173 / 1,204 / 624 bytes. These are regional
results, not a new full-corpus score. A complete Mozilla comparison at v215 -8
is now running in `ecoff-paq-full8` with ordinary and transformed streams.
Do not edit `ecoff_constraints.py`, `ecoff_probe.py`, or their dependencies
while it runs. Full evidence: `2026-09-28-ecoff-derived-tables.json`.

The new structural relation reduces selected table fields to one possible value.
An arithmetic coder supplied the same deterministic prediction can also omit
those bits; this is model information absent from the ordinary PAQ path, not a
claim that changing the entropy coder creates information.

## ECOFF symbol-name residual refinement

Twelve further physical regional trials independently restore. Predicting each
symbol-name offset from the previous transmitted string end gives
**11,596 / 41,126 / 41,183 bytes**, versus derived tables alone
11,830 / 41,335 / 41,527. Address deltas and byte-plane matrices do not improve
consistently beyond name offsets; retain the simpler mode1 candidate. All three
full structural variants restore all Mozilla bytes. Six tests cover arbitrary
64-bit values, modular wrap, malformed names and multiple arbitrary TAR names.
Full name-only mode1 PAQ v215 -8 runs in `ecoff-fields-full8`; all source files
`ecoff_fields.py`, `ecoff_fields_probe.py` and existing ECOFF dependencies are
frozen while running. Evidence: `2026-09-28-ecoff-field-probes.json`.

A separate unscored GOT diagnostic uses only symbol definitions transmitted
elsewhere in the same input archive. Same-object st_value matches 31,648 of
54,380 mapped GOT words; adding same-name definitions from the other objects
raises candidate membership to 50,462. Candidate choices and 3,918 exceptions
are not encoded yet, so this is not a compression result. This motivates an
explicit restricted-alphabet/escape tournament with identical-candidate uniform
rank and arithmetic controls, plus adaptive choices.

## Cross-object address candidates implemented

`ecoff_got.py` builds candidate alphabets using symbol definitions already
transmitted in the same archive. The current symbol value is first; additional
same-name definitions are ordered by observed definition frequency and address.
An explicit escape preserves arbitrary 64-bit values. GOT positions, executable
bytes and TAR positions remain intact; only selected GOT words become zeros.
The decoder first restores all symbol tables, then reconstructs the candidate
sets and selected addresses, with no external dictionary or original input.

All five full structural variants independently invert the complete Mozilla
input. 54,380 GOT words are mapped. Local symbol values match 31,648; adding
other transmitted objects gives 50,462 matches. Literal exception bytes fall
from 181,856 to 31,344. With the same candidate sets plus escape, uniform path
uncertainty is 87,255.08 bits. Blockwise ranks use 10,934 choice bytes; uniform
arithmetic 10,910; adaptive arithmetic 1,748 (13,965.61 predictive bits). These
are intermediate payloads, not final compressed sizes. Six tests pass, including
multiple rank blocks, adaptive rescaling, arbitrary exceptions and nonzero high
padding in the dynamic-header d_val union. The 32-bit union member must ignore
the high 32-bit padding; interpreting it as a 64-bit count initially disabled all
real objects and was corrected before any scored physical experiment.

Seven full physical Brotli11 controls are now running in
`ecoff-got-brotli-full`: ordinary input (-1), parent table/name constraints (-2),
explicit global candidate choices (0), uniform ranks (1), uniform arithmetic (2),
adaptive arithmetic (3), and local-only adaptive candidates (4). Source/probe
immutability is enforced. Do not edit `ecoff_got.py`, `ecoff_got_probe.py`,
`ecoff_fields.py` or their frozen dependencies while active. Compact structural
proof: `2026-09-28-ecoff-got-structural-gate.json`. No updated corpus rank yet.

Three small constructed TAR fixtures are in `ecoff-got-cohorts-v2`; use their
explicit `--manifest results/leaderboard/ecoff-got-cohorts-v2/manifest.json`
for future regional PAQ tests. They contain only two or three original objects
each and have modest cross-object coverage, so the first fast backend tournament
uses the complete Mozilla input. The probe default still points at the earlier
single-object fixture; change it only after its live whole-file run finishes.

Further unscored diagnostic: 239,835 relocated pointers lie in rdata/data/sdata.
Same-name global definitions cover 89,395. Extending the alphabet to transmitted
symbols and function starts from pdata covers 169,969, using a global alphabet
of 122,959 addresses. Those broader ranks/escapes are not implemented yet. Their
metadata, candidate-choice probability and effects on PAQ must all be measured;
do not present candidate membership alone as a byte saving.

## Complete executable-constraint milestone: 54th equivalent

All seven full Mozilla Brotli11 streams independently restore. Ordinary input
**13,872,280 bytes**, derived tables/name offsets **13,131,258**, global candidate
choices **13,049,702**, global uniform ranks **13,057,530**, global uniform
arithmetic **13,053,276**, global adaptive arithmetic **13,049,557**, local-only
adaptive candidates **13,077,702**. The shared-symbol model saves 28,145 bytes
against local-only candidates with otherwise identical structure and coding.
Adaptive coding is 145 bytes smaller than leaving choices to Brotli, while
uniform ranks lose. Model information supplies the gain; no rank superiority.
Evidence: `2026-09-28-ecoff-got-full-brotli.json`.

Portfolio 11 (`competitive_ecoff.py`) recognizes real ECOFF content, considers
all seven physical representations and retains the smaller incumbent. Its
optional cache qualification checks all source/input/frame evidence, recomputes
each transform, and repeats complete standalone restoration under the current
Brotli native binary (whose hash is recorded). Seven fresh decodes qualify the
new candidates; eleven unchanged portfolio streams preserve their independent
full-restoration proofs. One new integration test covers uncached candidates,
changed input, incomplete evidence and corrupted physical artifacts.

Complete sum **36,937,786 bytes, equivalent 54th among 322 entries**; saves
2,669,824 bytes against portfolio 10. Gap **9,112,275 bytes** above the live
27,825,511 leader. The live page was downloaded again and its SHA is unchanged.
All twelve physical files are in `results/leaderboard/competitive-ecoff-v11`;
compact proof: `2026-09-28-competitive-ecoff-milestone.json`. First place remains
unachieved; public source release and official listing remain pending.

The longer PAQ v215 -8 Mozilla ordinary/table/name runs still execute separately.
Do not edit their ECOFF sources. The GOT/Brotli tournament has completed, but the
GOT codec/probe are now portfolio-qualified and should also remain frozen; add
new modules for extensions. The focused next full PAQ comparison is shared GOT
candidates plus PAQ versus the pending name/table control; schedule it with
actual free memory, because the -12L NCI decoder still grows toward 20 GiB.

An additional unscored call-target diagnostic finds 57,598 Alpha bsr-r26 calls,
36,087 targeting the transmitted symbol/function-start alphabet. Uniform target
indices would cost 391,675.09 bits, excluding membership flags and exceptions.
PAQ already absolutizes those call displacements, so any replacement must respect
its combined contiguous text/init/fini region and include a same-model control.
Do not infer a gain from candidate membership; no call-target codec exists yet.
