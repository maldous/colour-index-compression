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

The CLI now selects portfolio 11. A separate process given only the selected
13,049,557-byte Mozilla frame restored 51,220,480 bytes exactly in 2.2696s,
peak RSS 394,692 KiB. Frame SHA:
`a1e7d1dbec5159a5e4ad1adeabbe51d85cdc98a9debe00ff95acdc30d842fadc`.
Proof: `2026-09-28-ecoff-cli-restoration.json`. The isolated source archive from
earlier still has the older default and must be refreshed before release.

## Function-constrained calls and measured alternate entries

Previous goal turn made a complete verified improvement to 54th; this turn
continues with new call-target codecs. `ecoff_calls.py` derives function addresses
from transmitted symbols and pdata, filters them to the contiguous text/init/fini
range recognized by PAQ, and preserves arbitrary branch exceptions. In-place
indices compensate for PAQ's existing absolute-call displacement transform.
Modes: 0 framed control; 1 in-place indices with membership bits; 2 explicit
side-stream indices; 3 uniform mixed-radix ranks; 4 identical-alphabet uniform
arithmetic; 5 adaptive arithmetic with per-object Fenwick frequencies. All six
full structural representations restore; seven tests cover signed branch edges,
unknown targets, rank/arithmetic controls and adaptive rescaling.

An exact offset diagnostic found all 21,511 initially unlisted calls target
16 bytes after an address in the function set. A separate frozen version,
`ecoff_call_entries.py`, adds +16 candidates (within the code range). All 57,598
calls then lie in the transmitted-information alphabet. This +16 offset is an
empirically tested model parameter, not an asserted universal ABI rule. Four full
structural representations restore; six additional tests preserve exceptions
outside the expanded set. Uniform rank payload 84,206 bytes; same-information
arithmetic 84,183; adaptive 70,870. In-place mode carries a 7,200-byte raw mask
which is subsequently compressed; no final-size claim from these raw payloads.

Eighteen fast physical Brotli trials restore. Expanded-entry in-place results
17,864 / 53,561 / 66,143 versus controls 17,792 / 53,530 / 66,215 are mixed.
The two in-place whole-file variants (base and expanded entries) are running in
`ecoff-calls-brotli-full`, two small-memory workers. The base PAQ tournament
`ecoff-calls-paq-objects` has completed the first two regions with almost no
benefit; its third region shows 70 bytes saved by in-place indices so far. The
expanded-entry PAQ tournament is queued in session 19635, waiting for the base
complete.json before starting three workers. Do not edit either call codec, its
probe, or frozen parent dependencies while these processes run.

The whole shared-GOT PAQ v215 -8 mode3 trial has also started in
`ecoff-got-paq-full8` after checking live memory availability (about 13 GiB).
This gives a same-PAQ-backend comparison against the existing table/name runs.
It remains separate from the completed Brotli portfolio. All older reference
runs and heavy-atom extraction continue; inspect processes before acting.

A broader pointer diagnostic rejects indiscriminate +16 expansion: address-pool
size grows from 122,959 to 212,498 but matches only 414 additional relocated
pointers (169,969 to 170,383 of 239,835). Keep the call-specific model separate.
Proof and completed Brotli regional trials are in
`2026-09-28-call-constraint-structural-gate.json`.

## Completed call-target controls and actual PAQ loss

The base/expanded call batch has finished **83 physical trials**, all independently
restored: 45 regional PAQ, 36 regional Brotli, and two full Mozilla Brotli streams.
Base in-place full stream **13,064,757 bytes**; expanded-entry in-place
**13,064,645 bytes**. Both lose against the 13,049,557-byte incumbent by
15,200 and 15,088 bytes and are rejected. The complete corpus remains 54th.
Compact evidence: `2026-09-28-call-constraint-physical-trials.json`.

Expanded in-place indices improve the three original PAQ regions by 10/8/57
bytes. Three additional complete objects selected for alternate-entry call
density improve by 31/60/34 bytes: 40,318→40,287; 24,280→24,220;
10,393→10,359. Separate adaptive streams instead give 40,591/24,318/10,378.
These are exploratory selected regions, not held-out generality claims. Uniform
ranks/arithmetic and explicit side streams are generally weaker than preserving
indices in the instruction stream. No regional result changes the corpus score.

A qualified trace of the ordinary 253,952-byte object at offset 43,270,656 is in
`ecoff-call-trace`. Its PAQ v215 -4 archive is byte-identical with and without
instrumentation; an independent extraction restores exactly. The complete
127,776-byte transformed code region maps uniquely into the trace. Its 469 calls
use an alphabet of 984 function/alternate-entry addresses. PAQ spends only
1,727.52 predictive bits (215.94 bytes) on their 21-bit target fields. Restricting
the binary trie to those addresses forces 4,827 bit decisions, but the original
PAQ cost of those forced decisions is only 419.93 bits (52.49 bytes). Candidate
and membership delivery costs are EXCLUDED: this is an optimistic diagnostic,
not a physical CIX gain. It explains why replacing detailed PAQ predictions with
uniform address ranks is a poor tradeoff. Preserve original probabilities when
adding constraints rather than discarding their conditional detail.

All 57,598 complete-input absolute call fields have low two bits equal to 3.
The first dense-index representation removes that alignment pattern. A separate
codec `ecoff_call_aligned.py` maps an index to 4*index+3 before compensating for
PAQ's absolute-call transform. It restores the full input exactly and passes the
literal-exception/target-index test. Twelve PAQ trials (control and aligned mode
on six complete objects) are running in `ecoff-call-aligned-paq-objects`.
Its sources are now frozen. This refinement tests compatibility with PAQ's
learned instruction representation; do not claim a gain before physical results.

All twelve aligned-index PAQ trials have now restored. In-place alignment saves
6/0/73/44/59/29 bytes against the six framed controls, with mixed performance
against unaligned indices (only 11 bytes smaller in aggregate across these
selected diagnostic objects). Full aligned/control Brotli streams are running
in `ecoff-call-aligned-brotli-full`; no full PAQ call variant has been launched.
Evidence: `2026-09-28-call-alignment-controls.json`.

The qualified trace diagnostic and the original 83 call controls were published
to the research Site; the complete 36,937,786-byte score is unchanged. A prospective
`competitive_large_paq.py` profile extends portfolio 11 above 24 MiB. It uses the
existing exact PAQ qualification and rejects pending artifacts. Its real NCI
qualification/unfinished-cache check passes. Do not run its complete refresh
until the eligible Mozilla and Webster v216 -8 results have independently
restored. The default standalone CLI remains the completed portfolio 11.

A broader follow-up exposes symbol-name boundaries to PAQ's text models.
`ecoff_symbol_text.py` first builds the shared-GOT constrained representation,
then swaps NUL/newline bytes within detected .dynstr ranges; an additional mode
also swaps underscore/space. Both are position-preserving involutions and support
arbitrary bytes. The inverse restores symbol names before the parent rebuilds
its dependent tables and addresses. Both full transforms restore exactly; three
fixture tests pass. They affect 3,915,136 symbol-table bytes. Nine physical PAQ
v215 -4 trials are running in `ecoff-symbol-text-paq-objects`, comparing the same
parent control, boundaries, and boundaries plus word separators. Freeze these
modules and dependencies until complete. Structural evidence:
`2026-09-28-symbol-text-structural.json`.

The aligned whole-file Brotli comparison also completed and is negative:
control 13,049,791 bytes; aligned indices 13,065,351 bytes (15,560 worse).
Both independently restore all Mozilla bytes. This confirms the alignment change
does not repair the full Brotli regression. No call variant enters the portfolio.
The combined call programme now has 97 completed physical trials. Retain the
qualified PAQ finding: the fields already carry little residual uncertainty.

The nine symbol-text trials completed. Control / boundary swap / boundary plus
underscore swap are 11,584 / 11,590 / 11,601; 41,081 / 41,087 / 41,090;
41,080 / 41,089 / 41,075 bytes. All restore. There is no consistent gain and no
full symbol-text trial is warranted. PAQ's pinned `detectText` already accepts
NUL after printable ASCII as an asciiz exception, explaining the weak premise.
Source attribution and all physical proofs: `2026-09-28-symbol-text-controls.json`.

Site publication succeeded at 2026-09-28T17:57:13Z, source
`7c3950618cf2b3eb43cd0177fdb57a5111218039`, with all 97 completed call controls
and the unchanged 54th-place score. This goal turn produced controlled negative
results and a refined modelling explanation, not a new complete-byte milestone.
The ten long PAQ jobs still run. At the final local check, v216 Mozilla encoding
was 46.76% and Webster decoding 20.75%; these percentages are process progress,
not score estimates. Re-check processes before acting on this historical note.

## Relocation-conditioned data pointer research

Previous goal turn made progress through 106 completed controls and qualified
PAQ loss attribution; it did not change the complete score. The current turn
revalidated all reference processes before continuing. `ecoff_relocated_pointers`
uses existing relocation symbol indices to constrain 239,835 data/rdata/sdata
pointers. Same-object symbol values match 38,554; adding same-name definitions
from transmitted objects matches 89,395. Exceptions are always literal. Duplicate
or overlapping relocation fields are excluded deterministically. Modes compare
framed control, in-place indices with membership flags, explicit side choices,
uniform ranks, identical-alphabet arithmetic, and adaptive arithmetic. A seventh
control uses only same-object definitions with the adaptive coder.

All seven complete structural transforms independently invert Mozilla. Shared
uniform path uncertainty is 1,121,925.49 bits; ranks use 140,354 choice bytes,
uniform arithmetic 140,244, adaptive 2,185 (17,452.24 predictive bits). Shared
literal exceptions use 1,203,520 raw bytes versus 1,610,248 with local definitions.
These are raw structural payloads, not final compressed savings. Eight tests
cover exact exceptions, shared definitions, invalid indices, and conflicting
relocations. All six small physical Brotli fixtures restore. The immutable source
is committed as bb66c2a. Seven full physical Brotli trials are running with four
workers in `ecoff-relocated-brotli-full`, plus nine PAQ -4 cohort trials using two
workers in `ecoff-relocated-paq-cohorts`. No new rank claim yet.

The older heavy-atom NCI trial completed independent extraction:
**464,859 physical bytes**, encode 2,863.85s, decode 3,447.75s. This is
**17,111 bytes larger** than the selected 447,748-byte hydrogen-constraint stream.
The earlier 7–13-byte regional gains did not carry through; reject the complete
candidate and preserve the incumbent. Evidence: `2026-09-28-nci-heavy-full-negative.json`.

## Complete relocated-pointer portfolio: 36,864,338 bytes

All seven full Mozilla streams restore. Framed parent 13,049,926; in-place
indices 13,048,317; explicit choices 12,993,515; uniform ranks 13,113,781;
uniform arithmetic 13,048,527; shared adaptive 12,976,109; local-only adaptive
13,013,860 bytes. Shared definitions save 37,751 physical bytes with the same
adaptive coder; ranks lose. The selected result saves 73,448 bytes against the
prior portfolio member. Full evidence: `2026-09-28-ecoff-relocated-full.json`.

Portfolio 12 freshly decoded all seven candidates again after input/frame/source/
backend checks and transform recomputation. Eleven unchanged selected streams
retain their independent restoration proofs. Complete sum **36,864,338 bytes**,
still **54th equivalent**, with **9,038,827 bytes** above the 27,825,511 leader.
The live leaderboard was downloaded again at 18:11:41Z; its page hash and all
322 entries are unchanged. Proof: `2026-09-28-competitive-relocated-milestone.json`.
The standalone CLI now selects portfolio 12. A separate CLI process restored the
selected Mozilla frame in 4.8748s, peak 590,228 KiB, then an external comparison
confirmed every byte; `2026-09-28-relocated-cli-restoration.json`.

A separate causal feedback model `ecoff_pointer_deltas.py` predicts each next
pointer from the previous pointer sharing its relocation-derived candidate
alphabet. It also compares previous-any-pointer and declared-symbol predictors,
plus in-place versus variable-length residuals. All five nontrivial full raw
transforms restore; seven tests cover signed modular edges, exact context
predictions and residual overflow. The context model predicts 101,838 pointers
exactly and 232,516 of 239,835 residuals fit below 16,384. Those are raw diagnostics.
Six full Brotli streams are running in `ecoff-pointer-deltas-brotli-full`; initial
completed in-place context mode is 12,899,784 bytes and exact, but the full
portfolio remains at 12's score until the remaining controls and integration.
No ranking from a partial tournament. The new sources are frozen as 904f6df.

The relocation-symbol diagnostic clarifies the next possible restriction:
75,682 records refer to the .text section, 40,876 to .rdata, 20,449 to .rconst.
Section-labelled targets may be better constrained by that section's range or
local function starts than by same-name section bases from other objects. This
is an unimplemented follow-up, not an additional gain. No external byte table.

## Complete causal pointer-feedback milestone: 36,770,292 bytes

All six full feedback representations restore. Parent framed control 13,049,589;
previous-any-pointer in place 13,066,624; same-alphabet causal pointer in place
12,899,784; declared-symbol-only 13,045,261; previous-any-pointer varints
13,054,073; same-alphabet causal varints **12,882,063 bytes**. Grouping by the
transmitted candidate alphabet is essential; merely differencing adjacent
pointers loses. Evidence: `2026-09-28-pointer-feedback-full.json`.

Portfolio 13 freshly recomputed all transforms and repeated all six independent
full decodes, then retained the smallest exact physical stream. Complete sum
**36,770,292 bytes, 54th equivalent**, gap **8,944,781** to first. Saves 94,046
against portfolio 12 and 167,494 against the previous Site snapshot (portfolio
11). No first-place claim. Proof: `2026-09-28-competitive-pointer-feedback-milestone.json`.
The CLI now selects portfolio 13; a separate process restored the selected frame
in 4.9635s with peak 590,228 KiB. Frame SHA
`150e13e7dfae232b2f9c7383f303b607e309ae0b3351f2ea6c9a18eef0e44188`;
proof `2026-09-28-pointer-feedback-cli-restoration.json`.

The prospective large-input PAQ extension is now portfolio 14 and inherits the
completed pointer-feedback dispatcher. It remains unscored until all eligible
v216 Mozilla/Webster references finish extraction. Twelve new same-fixture PAQ
feedback controls (modes 0/2/3/5) run with three workers in
`ecoff-pointer-deltas-paq-cohorts`, alongside the two-worker nine-trial relocated
pointer cohort. No whole-file PAQ pointer-feedback run has started yet. Inspect
all three cohort outcomes before selecting a whole-file PAQ candidate.

Site publication of portfolio 13 succeeded at 2026-09-28T18:23:18Z, source
`393b88bcfd2c2055ee677b181ca30dec3780ec75`. It includes the new complete total,
all thirteen full pointer/feedback controls, and the completed heavy-atom negative.
No GitHub Actions or GitHub source push was used. Research source remains local;
public source eligibility is still outstanding.

At this turn's last PAQ cohort observation, relocated-pointer first fixture
control/in-place/adaptive = 70,358/70,355/70,286 bytes; second fixture
96,450/96,474/96,358. Feedback first fixture control/context-in-place/declared-only
= 70,357/70,298/70,410; variable-length feedback and later fixtures remain pending.
Sessions 32381 (two workers) and 11600 (three workers) are live; re-check actual
processes next turn. Full reference v216 Mozilla encoding was 54.74%, Webster
decoding 37.94%, and v215 -12L NCI decoding 40.59%, all historical progress only.
The inherited compute affinity remains CPUs 16–31; no affinity change was made.
This goal turn made a complete verified 167,494-byte improvement, but first place
remains unachieved and the goal stays active.

## Section/function pointer milestone: 36,744,807 bytes

Seven new full Brotli controls all restore. Framed causal-parent control 12,881,996;
local function ordinals 12,857,734; code-section intervals 12,880,707; all section
intervals 12,881,108; hybrid function/section ordinals **12,856,578**; identical
function-alphabet uniform ranks 12,928,583; uniform arithmetic 12,928,247 bytes.
The hybrid saves **25,485 bytes** against the previous selected member. Ranks
remain worse than predictive residuals. Raw ranks use 109,847 choice bytes;
identical-alphabet arithmetic uses 109,810. Both have the same 75,574 hits and
transmitted function alphabets. All seven candidates were recomputed and decoded
again during portfolio 14 qualification. Complete score **36,744,807**, still
**54th equivalent**, gap **8,919,296**. A fresh live leaderboard fetch is unchanged.
Evidence: `2026-09-28-section-pointer-full.json` and
`2026-09-28-competitive-section-pointer-milestone.json`. Standalone CLI restoration
was 5.8359s, 445,000 KiB peak; independent byte comparison passed. CLI now selects
portfolio 14, and the prospective large-PAQ extension is unscored portfolio 15.

All nine relocated-pointer PAQ cohort trials also finished. Shared adaptive modes
save 72/92/71 bytes against controls. All twelve causal-feedback PAQ cohorts
finished: context in-place saves 59/151/167; context varints save 66/178/161.
Declared-only loses 53/36 on the first two and saves only 28 on the last. The
varint feedback model has the best aggregate selected-fixture gain; one full
Mozilla PAQ v215 -8 trial is now running in `ecoff-pointer-feedback-paq-full8`.
Twelve section-pointer PAQ trials compare control, hybrid, ranks and arithmetic
on the same three fixtures in `ecoff-section-pointers-paq-cohorts`. Regional
results are diagnostic, never projected into the leaderboard total.

The next instruction experiment uses dynamic GOT mappings and header GP values
as a reversible coordinate system for LDQ instructions based on register 29.
It normalizes reachable unambiguous symbol references to identities derived from
transmitted symbol names. All unknown/ambiguous displacements remain literal;
flags make decoding exact even if an instruction has a different runtime GP.
HP's Tru64 specification (2002), 2.2.2 and 14, supplies the header/table layouts.
A full diagnostic finds 393,897 eligible loads, 364,075 naming known GOT symbols.
The 369 recognized LDGP prologues all reconstruct the header GP, but no prologue
transform is claimed or implemented. This is an input-derived model, not an
external symbol dictionary. `ecoff_symbol_loads.py` compares local lexical IDs,
global symbol-frequency IDs (aligned and dense), global lexical IDs, and a
framed parent control. Eight invariants pass; full structural gates follow.

## Shared symbol-load milestone: 36,690,274 bytes

The five full raw load transforms restore exactly. The global lexical alphabet
covers only 8,637 loads, so no full physical trial was allocated to it. Four
complete Brotli comparisons finish: framed parent control 12,856,408; local
lexical IDs 12,868,374; global symbol-frequency aligned IDs **12,802,045**; global
frequency dense IDs 12,802,330 bytes. Shared aligned identities normalize 306,223
of 393,897 eligible loads; local IDs normalize 364,075 but lose. The winning
representation saves **54,533 bytes** against portfolio 14. Full encode 177.45s,
decode 8.2749s, 754,148 KiB process peak under concurrent load. Eight invariants
and all full raw/physical restorations pass. Source f5e8710; four candidates were
qualified and independently decoded again by portfolio 15 (c6277d2). Complete
score **36,690,274**, still **54th equivalent**, gap **8,864,763** to first.
The leaderboard page hash and 322 rows were rechecked and unchanged. This goal
turn has improved the complete score by **80,018 bytes**, not achieved first.

The direct PAQ trace supplies a discriminating limit: 1,155 eligible loads in
one independently qualified 253,952-byte object; 927 belong to the transmitted
symbol alphabet. Their 6,811 forced prefix decisions cost original PAQ only
166.07197 bits (20.759 bytes) before candidate delivery/membership/framing.
PAQ spends 3,899.77 bits on the matched displacements altogether. This is a
specific forced-branch diagnostic with unchanged probabilities elsewhere, NOT
an upper bound on all conditional predictive architectures. Cross-object symbol
identity sharing remains a stronger hypothesis than simple support pruning.
Evidence: `2026-09-28-load-target-paq-loss.json`. Nine same-cohort symbol-load PAQ
trials compare control, global aligned and global dense in
`ecoff-symbol-loads-paq-cohorts`, two workers. Do not project those results.

A separate Webster test preserves prose order while lifting recognized tags
into an explicitly transmitted dictionary and identity stream. Both raw full
transforms restore all 41,458,703 bytes; five invariants cover literal tabs,
arbitrary bytes, dictionary overflow and invalid IDs. The file contains 3,010,125
tags with 190 spellings, occupying 13,043,977 bytes. Nine PAQ v215 -4 regional
trials reject the approach: control/binary-IDs/printable-IDs are
12,268/12,846/12,876; 12,844/13,495/13,528; 14,403/14,921/14,943. All restore.
Even keeping prose order loses 518–684 physical bytes per selected 64 KiB region;
no full PAQ prose-decomposition run is warranted. Preserve this negative in
`2026-09-28-markup-prose-paq-negative.json`, with full raw structural evidence in
`2026-09-28-markup-prose-structural.json`.

Site portfolio 14 publication succeeded 2026-09-28T18:50:39Z, source
5d37b745cc62aaff8c6ef95c058a3793886685a4. A follow-up publishes portfolio 15.
Long references still run; the most recent local checks were v216 Mozilla
65.57% encode, Webster 59.99% decode; v215 -9L Webster 62.25%, Mozilla 30.92%
encode; v215 -12L NCI 48.52% decode. These are historical process percentages,
not completed scores. Ten long PAQ processes plus bounded regional controls
remain local, on inherited CPUs 16–31. No Actions, workflows or GitHub pushes.

Portfolio 15 now has a fresh source-only release candidate at
`/tmp/cix-source-portfolio15-20260928.tar.gz` (source 1054b52, 1,007 files,
2,095,539 bytes, SHA 9ee789e914e72e8f24c6728f89583f72a1ed74a1148e00b934d5b416affb1135).
Its isolated CLI restores the newest full Mozilla stream in 7.4799s, 495,704 KiB.
A file-access trace confirms no original repository codec source, corpus, or
benchmark cache was opened. The compressed input was explicitly supplied; an
external byte comparison subsequently passed. All staged source hashes remain
unchanged. This is a fresh Python/source qualification, not a claimed repeated
native rebuild: 749 dependency files match the previously rebuilt isolated
source, whose six binary hashes and proof are retained. Evidence:
`2026-09-28-portfolio15-source-isolation.json`. No public source was published.

The twelve section/function PAQ cohort controls are complete. Hybrid ordinals
save 88/132/68 bytes against controls; uniform ranks lose 1/27/6 and uniform
arithmetic loses 4/28/9. All restore. One full hybrid PAQ v215 -8 candidate is
now running in `ecoff-section-pointers-paq-full8`; the causal-feedback full PAQ
candidate remains separate and live. Frozen sources stay unchanged.
The first shared-symbol PAQ cohort is negative (aligned 70,735 vs control 70,212);
wait for the other representations and regions before concluding or launching
a full shared-symbol PAQ run.

Possible next modelling refinement (unimplemented): preserve original instruction
values for PAQ while adding contexts from previously decoded symbol identities.
A decoder-visible lookup would have to be transmitted and paid, or derived from
already decoded tables. Inspect PAQ block boundaries and model state first; never
feed an untransmitted future target or uncounted sidecar into a scored predictor.
The pinned DECAlphaFilter already byte-swaps memory instructions, so opcode and
registers precede displacement bits; DECAlphaModel.hpp already has many register/
displacement maps. A shared-symbol context must demonstrate new predictive value
against those existing maps, including lookup-delivery costs. No new PAQ fork or
model change has been made for this idea yet.

Portfolio 15 Site publication succeeded 2026-09-28T19:03:56Z, source
`dcb6344731190f00d4884f9d49c51f1854fbbec0`, deployment
`appgdep_6ababa0bff8c81918df165b8c90db77b`. The published page shows 36,690,274
bytes / 54th and the four full symbol-load controls, qualified PAQ loss diagnostic,
and nine Webster negatives. New section-pointer PAQ controls and isolated-source
proof are saved locally for the next material Site update. The active goal remains
unachieved, unpaused and unblocked; this turn made measurable progress. The next
turn must re-check live reference and full-candidate jobs before starting new ones.

## Causal instruction state fed directly into PAQ

Previous turn made progress: 80,018 verified full bytes saved, Site published,
and a fresh isolated source candidate passed a traced standalone full decode.
Current processes were revalidated; no job was restarted. Shared-symbol load
normalization is negative on the first two PAQ fixtures (aligned +523/+444;
dense +578/+531). Finish the last fixture before closing that controlled result.

`build_paq_gp_feedback.py` now builds an isolated PAQ v215 fork that leaves
instruction bytes unchanged and adds one causal displacement context to an
otherwise unused mixer-input pair in DECAlphaModel. Three modes use the last
completed GP load, the last two plus destination register, or the last load to
the same register. State resets at code-block boundaries; context-map training
persists. These are already decoded values, not future input or transmitted
lookup tables. The outer frame pays a mode byte and its full framing/checksum.
The native reference sources and binaries are untouched. Fork binary SHA
74837dadd8325b755cf7c92cd79920676901e5cd28c5331ed801728838db1585; original-model
SHA ed9e5304c5d00dca538967a9bb0eca0d5fd48be82b6bf554c4cffb475feaa6fd.

Two meaningful native tests pass in 29.49s: all four settings restore a recognized
synthetic executable exactly; mode zero produces the same PAQ payload as the
unmodified native reference; each enabled mode changes the payload. The map
is active only for LDQ instructions using register 29. Existing PAQ contexts,
other input slots, arithmetic coding and code transforms stay intact. Fifteen
whole-cohort trials now run in `paq-gp-feedback-cohorts`, two workers, comparing
native reference, disabled fork, and three feedback contexts on the fixed three
constructed subarchives. Each first applies the completed section/function
transform, so all variants get identical predictive information. No result or
full-file gain is claimed before restoration. Freeze builder, probe, fork and
all dependent codecs while the tournament is live.

## Exact continuation constraints and scalable binary Markov classes

`markov_euler.py` uses the classical directed matrix-tree/Whittle identity to
count only trails compatible with every transition count and fixed endpoints.
It compares a joint independent-row rank, remaining-row arithmetic, exact-trail
rank, and arithmetic using the same valid-completion counts. This is an
implementation of known counting theory, not a novelty claim for the theorem.
Exhaustive independent enumeration of every ternary sequence of lengths 1–7
confirms all class cardinalities and every rank. Six tests pass. Eighty complete
physical fixture trials restore: rank improves five of twenty fixtures over
independent rows, by up to six bytes; conditioned arithmetic matches nineteen
of twenty rank sizes, differing by one byte on the other. The largest excluded
space is 42 bits. Eight PAQ-error windows show no physical gain; two OSDB nibble
windows save one byte each but have substantial matrix metadata. These are
residual diagnostics, not full Silesia gains. Evidence:
`2026-09-28-markov-euler-tournament.json`. No portfolio addition follows them.
Sources: Whittle (1955), doi:10.1111/j.2517-6161.1955.tb00197.x; Jacquet, Knessl
and Szpankowski, https://www.cs.purdue.edu/homes/spa/papers/aofa10.pdf.

`paq_markov_residual.py` now tests that exact constraint through the real PAQ
prediction bridge on the independently qualified 253,952-byte object. All mode,
count, block, checksum and selection bytes are included. Whole-group binomial
composition remains a physical-size fallback. The complete control restores at
45,364 bytes versus the original PAQ's 45,041; conditioned 4,096-event rank and
arithmetic packets remain pending. Root: `paq-markov-residual-original`.

The binary case also factorizes into two positive run-length compositions:
C(n0-1,r0-1) * C(n1-1,r1-1). `binary_markov_runs.py` exploits that exact structure
without repeated determinants or bounded packet headers. Counts, initial bit
and run number are transmitted. A joint rank and identical-information arithmetic
control both support whole confidence groups. Every binary sequence of length
1–9 agrees with the general determinant count, and both representations restore;
three additional long/invalid-metadata tests and three wrapper tests pass.
`paq_binary_markov.py` compares this whole-group representation with the same
binomial fallback. The complete-source bridge tournament is running separately
in `paq-binary-markov-original`; no gain is yet claimed. Both active source sets
are frozen. The old trace and PAQ reference remain unchanged.

The nine shared-symbol normalization PAQ trials are now all complete and negative:
control/aligned/dense = 70,212/70,735/70,790; 96,149/96,593/96,680;
97,750/98,374/98,501. Preserve the full Brotli gain, reject a full PAQ normalized
load trial. Evidence: `2026-09-28-symbol-load-paq-negative.json`.
The direct causal PAQ-context fork is a separate experiment: first fixture native
and disabled controls both 70,207; last-load 70,197; two-load 70,199; register-local
70,199. Those small positive results do not establish a complete-file gain.

A prospective bounded portfolio 16 extends native PAQ to inputs of 24–48 MiB,
excluding the recognized database format. It can adopt a completed Webster
result while retaining the fully verified current Mozilla stream. This is a
fixed source-byte size policy, not a partial-file projection. Its NCI qualification
and pending-cache rejection pass. `competitive_large_paq.py` is now prospective
portfolio 17 above 48 MiB, inheriting the intermediate dispatcher; a real pending
Mozilla cache is rejected. Do not run portfolio 16 until Webster result.json has
independent full restoration; do not run 17 until Mozilla does. The scored default
and published Site remain portfolio 15, 36,690,274 / 54th.

## Completed residual negatives and local CPU scheduling

Both original-source Markov tournaments have completed. Bounded exact trails and
whole binary run compositions each retain the incumbent on every confidence
group. All six framed outputs restore the qualified 253,952-byte source through
the causal PAQ bridge. Each costs 45,364 bytes versus PAQ 45,041, a 323-byte loss.
The count constraints exclude arrangements, but their paid descriptions cost
more than they save here. Reject these refinements for this trace; the negative
does not disprove other structural constraints. Compact evidence is retained in
`2026-09-28-paq-markov-negative.json` and
`2026-09-28-paq-binary-markov-negative.json`.

A CPU inventory exposed idle performance cores: inherited affinity restricted
jobs to CPUs 16–31, although the cgroup allows CPUs 0–31. The same native PAQ
decoder restores the same qualified archive exactly on CPU8 in 46.4519 seconds
and CPU16 in 89.2131 seconds under the concurrent workload, an observed 1.9205x
ratio. This is a local paired observation, not a general speed guarantee. Seven
physical performance cores now host the longest local reference and full ECOFF
jobs. Only those benchmark process/thread affinities changed; no global settings
or unrelated applications changed. Managers inherit the new affinity for later
children. The process identities, before/after masks and exact decode proof are
in `2026-09-28-paq-performance-core-scheduling.json`. No jobs were restarted.

## Verified Webster and combined procedure-address milestone

Webster v216 -8 independently restored all 41,458,703 bytes: 4,626,898
physical bytes, encode 7,254.64s and decode 8,661.34s under the concurrent
workload (affinity changed during decode as recorded). Portfolio 16 qualified
all twelve streams at 32,727,345 bytes, equivalent 25th, saving 3,962,929
against portfolio 15. This large gain comes from the established PAQ backend.

`ordered_subset.py` implements known combinadic ranks and arithmetic with the
same valid-completion counts. Exhaustive small subsets prove every rank is a
bijection; both restore sparse 64-entry subsets from a 2^30 universe without
scanning the universe. `ecoff_pdata.py` applies these to strictly increasing
procedure-address components, paying low-bit flags and each block endpoint.
Exceptional tables remain literal. It runs after section-pointer prediction so
its parent sees the original procedure table. Nine invariants pass.

Twelve regional Brotli trials all restore. Simple previous-address differences
save 454/520/574 bytes. Subset ranks save -11/160/379, and same-information
arithmetic saves -189/212/172; all lose to simple differences. This supports
address prediction, not an intrinsic rank advantage. A twelve-trial PAQ control
is now running locally in `ecoff-pdata-paq-cohorts`; freeze its codec/probe.

`ecoff_pdata_symbols.py` combines the regional winner with the already verified
shared-symbol load transform. Three wraparound/exception tests pass. Both full
Brotli streams restore: control 12,802,097 and differences 12,733,922 bytes.
The latter saves 68,175 versus its same-wrapper control and 68,123 against the
selected portfolio-15 Mozilla stream. Portfolio 18 composes this with verified
Webster: **32,659,222 bytes, 25th equivalent; 4,833,711 bytes above the leader**.
All twelve physical streams have qualified independent restoration evidence;
both new Mozilla candidates were freshly decoded again during qualification.
This turn has saved 4,031,052 complete bytes. Compact evidence is in
`2026-09-28-competitive-intermediate-paq-milestone.json`,
`2026-09-28-pdata-symbol-full.json` and
`2026-09-28-competitive-pdata-symbols-milestone.json`. The leaderboard was
rechecked at 19:52:37Z and its 322-entry hash remains unchanged.

The direct causal PAQ-context tournament also completed all fifteen controls.
Native and disabled-fork PAQ payloads are byte-identical in each region.
Last-load context saves 10/11/29 physical bytes, two-load context 8/7/17, and
register-local context 8/8/22. A six-trial native/last-load comparison at level 6
is running in `paq-gp-feedback-level6-cohorts`, one worker, before any full new
fork run. Preserve the level-4 evidence in `2026-09-28-paq-gp-feedback-cohorts.json`.

The default CLI is now portfolio 18. Prospective complete-size PAQ is portfolio
19 (`competitive_large_paq.py`), inheriting 18 and gated above 48 MiB. Do not
qualify 19 until the full Mozilla reference result.json has exact restoration.
Portfolio numbers 17 and 19 were prospective/unscored; no completed 17 result
is claimed. The completed Webster decoder freed performance core10, which now
runs the existing name-offset full experiment. The v216 manager is constrained
to core8 for its remaining Mozilla run and subsequent decoder. Other long jobs
remain live, never restarted. First place remains unachieved and research active.

Portfolio 18 source isolation passed: bundle source
1ee42a6c902c1d4afcd1ff8809491188e866a7eb, 1,032 files, 2,116,608 bytes,
SHA 536c12949e12113d364b206440e9d0b07b0ceabe77c51df2e8462a21225d3678.
The isolated CLI restores the 12,733,922-byte Mozilla frame in 7.5747s,
594,852 KiB, with no original source/corpus/cache access in the file trace.
All staged sources remain unchanged. The six native binaries are reused from
the proven isolated rebuild after 718 relevant native/dependency source files
match; this is not another claimed native rebuild. Evidence is in
`2026-09-28-portfolio18-source-isolation.json`.

The Site published portfolio 18 successfully at 2026-09-28T20:02:24.726855Z,
source 66a80ac628b048079cd1ba43de3ad1af06ea4c22, deployment
appgdep_6abac7c0f6808191826b51c8898040df, version
appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_1ef0d4427ac88191948771c6533b58bc.
It shows 32,659,222 / 25th, all completed Markov and symbol controls, and source
isolation. Browser handoff is skipped for this autonomous/background goal.

A further causal procedure predictor uses the previous decoded unwind descriptor
to predict the next address difference from past lengths. Last-value, running-mean
and preceding-length controls all preserve modulo wraparound; five invariants
pass. Twelve regional Brotli trials restore but reject full trials: last-value
loses 79/226 and saves 103 bytes; mean loses 493/567/768; preceding-length loses
139, saves 33 and ties. Preserve the negative in
`2026-09-28-procedure-feedback-brotli-negative.json`. No scored candidate follows.
The separate procedure rank/PAQ tournament's first region is now complete:
control/differences/rank/arithmetic = 70,210/70,073/70,222/70,226. Wait for the
other two regions. Direct GP-feedback level6 has only its first native control
complete (69,853); do not infer the feedback effect.

At 20:04:16Z the remaining reference processes were live: v216 Mozilla 89.42%
encode; v215-9L Webster 76.50%, Mozilla 40.08% encode; v215-12L NCI 65.75% decode.
These percentages are historical observations, never scored results. Available
memory was about 8 GiB; avoid adding another large full PAQ allocation while
the 12L decoder grows. Goal active and unachieved; this turn made a material
verified 4,031,052-byte improvement. Continue from actual process/artifact state.


## Complete filtered portfolio 19 and causal alphabet feedback

The stored-mode decoder failure was isolated to v216 predictorMain being null
while block/filter decoding dereferences its Shared state. The separate
`build_paq_store_state.py` fork supplies state only and fails on an unexpected
probability request. Reference source/binaries are unchanged. All twelve native
level-zero archives restore exactly through this fork, and the qualified
253,952-byte nonzero control produces the identical native 45,027-byte stream.
The fork binary is 6b815f63502c515a95654df316deb30b6a050fbee1293897f4e643c54843212b.

The initial combined stdout/stderr segmentation reports contain progress
contamination and must not be used for path analysis. Native level-zero archives
were cheaply recreated with separate logs and must equal the already restored
archives byte for byte. Clean parsing was corrected to include x86/64 and reject
silently skipped records. The corrected compact path inventory includes all
native block lines, with lengths explicitly described as declared leaf lengths,
not original coverage or exact model-input byte counts. See
`2026-09-28-paq-store-state-qualification.json` and
`2026-09-28-paq-clean-path-inventory.json`.

All twelve procedure PAQ controls completed: differences save 137/207/206 bytes;
ordered subset ranks save -12/26/0; same-space arithmetic saves -16/20/-2.
Simple differences win. All six direct last-load PAQ level6 controls restore,
saving 7/7/23 bytes against native. The raw level6 report's
control_matches_reference=false denotes absent disabled arms, not a failed
comparison; disabled exact identity passed at level4. Compact reports preserve
these distinctions. Post-calloc hugepage advice was slower with identical
archives and is rejected; no live reference job uses it.

The new `ecoff_filtered.py` CIXB13 stream combines the existing procedure/symbol
transform with native PAQ v216 -0 reversible filters and Brotli11 (lgwin24).
Full Mozilla mode0 (CIX only) is 12,733,922 bytes; mode1 (both) is 11,249,835;
mode2 (filters only) is 12,398,643. All restore. Mode1 encodes in 150.560s and
decodes in 6.241s under the current workload; all native archive headers and
outer framing are counted. This is a measured representation-combination gain,
not a rank-coding advantage over identical-information arithmetic.

`competitive_filtered.py` is now portfolio19. It qualifies all three full
candidates by source/backend/input/frame identity, recomputes structure, and
freshly decodes each. Complete root `competitive-filtered-v19` contains all12
qualified streams: **31,175,135 bytes, equivalent24th, 3,349,624 above leader**.
This turn saved 1,484,087 complete bytes. Live leaderboard recheck at20:44:39Z
retains 322 entries, leader27,825,511, SHA78d29449a1036e1545d3665ccba9de65555f1b5afda78640c2e2b12dde946c86.
Default CLI is portfolio19. Prospective `competitive_large_paq.py` is now20,
inheriting19; its prior19 label was never scored. Wait for full native Mozilla
result.json before qualifying `competitive-large-paq-v20` from19.

Source-only bundle `/tmp/cix-source-portfolio19-20260928.tar.gz` is 3,032,867
bytes, 1,401 files, sourcef1d4f1f33133fcfcd89132e71cb2e610de2d0d86,
SHAb491d7baa97c774d319f7447eb6a3c623196a260f93f986a0c45af3024214ff6.
The stored-state decoder freshly rebuilt identically in the isolated tree.
Six other qualified rebuilt binaries were reused after 713 source files matched
against the prior isolated rebuild. The isolated default CLI restores full
Mozilla in10.3296s,583484KiB, exact SHA657fc3764b0c75ac9de9623125705831ebbfbe08fed248df73bc2dc66e2a963b.
Its file trace accesses no original research source/corpus/cache; the external
Python dependency environment is reused. All staged files retain their hashes.
See `2026-09-28-portfolio19-source-isolation.json`. The reproduction script now
stages/builds the separate repaired fork too, without Git/network at build time.

The Site published portfolio19 successfully at2026-09-28T20:50:04.725133Z:
sourcea04ebba58484b827582bf0badbf0020c75850162,
deploymentappgdep_6abad2ec4380819193d8d08e9f6b80ee,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_c670617eb9d48191a3012251d0b691e8.
It shows31,175,135/24th, all completed controls above, corrected path inventory,
and isolated source qualification. No browser handoff in this autonomous goal.
The GitHub repository was read-only confirmed private this turn. No GitHub push,
Actions job, public source release or official listing is claimed.

`build_paq_gp_alphabet.py` adds causal displacement multiplicity and alphabet
occupancy feedback in unused PAQ mixer slots. A uniform escape prior supports
all16-bit values; counts reset per detected block, and rescaling preserves
occupancy. It does not claim hard elimination of unseen values. Exact integer
probability/rescaling invariants and all four modes restore; mode0 equals native
bytes. Binaryc1d4d518df9fe85bd828c359b2a1c01c7502829ab41c10056646af2a8f536e60.
The 15-trial three-region level4 tournament is LIVE session86988,
manager3229196, `paq-gp-alphabet-cohorts`; freeze builder/probe/model sources and
all parent dependencies. The first native/disabled pair is70207/70207. No
feedback gain inferred yet. Only this manager/descendants were moved to CPUs0,18
after the full filter batch freed core0; scheduling journal records identities.

At20:50:03Z native v216 Mozilla is decoding14.39%, v215-12L NCI decoding74.74%,
v215-9L Mozilla encoding47.16%, Webster encoding86.71%. These are historical
process observations, never scored bytes. v216 Mozilla encoder completed at
20:27:28Z; decoder3202350 runs onCPU8. All full ECOFF PAQ branches remain live.
Available memory~9.8GiB; avoid gratuitous full PAQ allocations. First place is
unachieved; goal remains active, this turn materially progressed. Revalidate
processes before continuing rather than restarting any long run.


## Negative residual controls and targeted memory feedback

This goal turn made experimental progress, without changing the complete score:
portfolio 19 remains 31,175,135 bytes / 24th equivalent. Thirty new physical
regional trials completed and restored. Do not repeat or promote them blindly.

`ecoff_filtered_columns.py` (CIXB15) locates exact uniquely matched PAQ-shuffled
instruction regions in the native stored archive. Explicit offset/length
metadata pays for reversing byte planes, bit planes and opcode-conditioned
columns. All eight invariants pass, including vectorized shuffle equality with
the qualified PAQ trace mapping. Twelve regional trials reject the branch:
control/byte-plane/bit-plane/opcode-column sizes are
116154/135595/190855/116190;
144626/163150/215756/145442;
162108/191160/271929/161266.
Opcode grouping is mixed; other variants lose throughout. Session18658 is
terminal. Preserve `2026-09-28-filtered-columns-negative.json`. Repartitioning
is a bijection, not a smaller legal state space by itself.

`ecoff_gp_residual.py` (CIXB16) retains instruction positions/opcodes/registers
while moving GP displacements to paid residual streams. Modes1/2/3 use literal
byte planes, last-access differences, and register-specific differences.
Modes4/5 deliver identical register-conditioned counts and use exact type-class
ranks versus remaining-count arithmetic, in bounded 256-byte chunks. Thirteen
invariants pass, including alphabet bijections, wraparound, register contexts,
and full native filtered frames. All eighteen regional trials restore and lose:
control/literal/delta/register-delta/rank/arithmetic sizes are
116154/116426/116970/117043/117561/117676;
144626/144977/145796/145507/146222/146016;
162108/162807/163885/163654/164164/164133.
Counts reduce order-class bits to 20985.765/20538.843/32120.825 from field widths
54000/50544/83664, but counts, framing and lost sequence correlations outweigh
that conditional reduction. Field width is not PAQ uncertainty. Rank/arithmetic
have mixed final-byte differences and neither beats the incumbent. Session91867
is terminal; preserve `2026-09-28-gp-residual-negative.json`. No full run launched.

`ecoff_instruction_loss.py` attributes all bits of the qualified 127,776-byte
code region (31,944 instructions) inside the 253,952-byte real object, matching
every outcome to the unchanged native PAQ trace. Opcode loss is 6327.7725
predictive bytes, non-GP memory displacement4701.1122, memory Ra3889.0849,
memory Rb1877.2142, versus GP displacement535.2412. These are unscored prediction
costs. Count-conditioned classes exclude count delivery; opcode self-conditioning
is explicitly null, never treated as a zero-cost prediction. Full evidence:
`2026-09-28-instruction-field-loss.json`. Current exact author-reported deficits
are refreshed in `2026-09-28-portfolio19-per-file-deficits.json`.

This motivates `build_paq_memory_feedback.py`, which derives its isolated patch
from the already-qualified GP mixer insertion without changing that source.
It normalizes the current memory-displacement prefix against causal predictions:
mode1 last access using the same base register; mode2 last opcode/base access;
mode3 previous stride through the same base register. Block state resets; all
observations are completed decoded fields. No future counts or source tables.
The native/disabled and all three synthetic modes restore, and disabled payload
is byte-identical (one test,39.30s). Built binary SHA
ea5f908e79c07fbd3b14f43ad38f9804c9a9e537afa9014f4d341f3ba454b81f.
Root `benchmark-work/references/paq8px-cix-memory-feedback` holds source/build
and provenance. Build session39465 and test61787 are terminal success.
The five-trial qualified-object pilot is LIVE session20634, single workerCPU20,
`results/leaderboard/paq-memory-feedback-pilot`, using its manifest.json.
Freeze builder, `paq_memory_feedback_probe.py` (CIXB17), base GP builder, binary,
and parent transform closure until it completes. No completed pilot result yet.

The separate alphabet-feedback tournament session86988 remains live. Eight
results were complete at21:12:13Z: first region native/disabled/frequency/
occupancy/both =70207/70207/70189/70183/70183. Second region native/disabled/
frequency =96145/96145/96134; other arms pending. Do not infer whole-file gains.
The ProcessPool manager's additional threads still had old inherited masks;
all are now updated. Current pairs were pinned to distinct cores0/18 because
Linux was scheduling both on core0. Worker identities and before/after masks are
in `2026-09-28-alphabet-thread-affinity.json`. New workers may need revalidation;
never change unrelated jobs or claim timing comparability across affinity changes.

At21:12:13Z native v216 Mozilla decoder was live at25.35%, v215-12L NCI decoder
at80.96%, v215-9L Mozilla encoder50.52%, Webster91.74%. Native Mozilla still has
no result.json; keep prospective portfolio20 unqualified. All long full ECOFF
runs remain live, unchanged. Only process observations, never inferred scores.

The Site retains31,175,135/24th and now includes all thirty negatives, field-cost
attribution and current per-file deficits. Publication succeeded at
2026-09-28T21:12:55.038605Z, sourcec9b84f8896914e201de49982da5d75dcc2e1eed0,
deploymentappgdep_6abad847acb4819195a3755d94661966,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_3a60726357188191b6730f909d022f35.
No pending Site request or browser handoff. Goal stays active and unachieved;
this turn completed meaningful negative experiments and initiated the stronger,
evidence-directed predictive test. No GitHub Actions or GitHub push.

## Causal predictor screening and completed regional controls

This continuation is progress, not goal completion or a blocked turn. Portfolio19
remains31,175,135 bytes /24th equivalent; no new complete member is qualified.

All15 `ecoff-register-rank-cohorts` trials restore and lose. The unchanged / MRU /
protected-MRU / role-MRU / bounded-MRU sizes are116154/131535/119114/128612/120044;
144626/159003/147781/156484/148561;
162108/188477/169395/180581/170363. Preserve the negative evidence JSON; no full
run. Session71911 was already terminal and its handle is no longer retained.

Alphabet feedback session86988 is terminal success: native/disabled/frequency/
occupancy/both are70207/70207/70189/70183/70183;
96145/96145/96134/96125/96126;
97746/97746/97724/97715/97719. Native and disabled payloads match exactly.
Occupancy saves24/20/31 physical bytes. The bounded affinity controller14720
exited when manager3229196 finished. Do not restart it. Evidence is committed in
`2026-09-28-paq-gp-alphabet-cohorts.json`.

Memory pilot20634 is terminal success. Native/disabled/last-base/opcode-base/
stride sizes40086/40086/39980/39886/40012; all restored exactly. The best saves
200 physical bytes on the qualified253952-byte source after section4 transform.
Evidence `2026-09-28-paq-memory-feedback-pilot.json`. Broader native versus mode2
level4 tournament is LIVE session32637, manager3320626, CPU0, one worker,
`paq-memory-feedback-cohorts`. First region restores70207/69831 (376-byte gain).
Second native96145 is restored; remaining work pending. Freeze the memory
builder, base GP builder, probe, native fork and complete parent transform closure.
The old pilot and the selected overlapping regional cohorts are exploratory,
not held-out tests and not whole-member leaderboard scores.

`paq_register_screen.py` found a causal MRU prior useful while rewriting the
register stream was not. Shared MRU, weight1/8 on native probabilities in
[1/32,31/32], saves149.698756 predictive bytes on the qualified original trace.
This screen is not physical compression; selection used that same object.
`build_paq_register_prior.py` creates a separate v215 fork whose coder receives
the prior mixture while `updateModels` still receives the ORIGINAL native p.
Changing native p would also change Shared losses/misses and future SSE, so
preserving this update is crucial to the identical-information control.

New helper `benchmarks/native/CixRegisterPrior.hpp` handles all shuffled Alpha
register fields causally, resets at code-block boundaries, skips the BSR target
bits that PAQ labels Rb, and keeps unseen registers possible. The independent
C++/Python oracle matches every opcode and block reset. Native disabled/all3
synthetic modes restore; both tests pass39.80s. Binary SHA
53d9396388a31d5f8dfa5e34a53e4c3be11b3184f8830f6a4e113b2acb4a4077.
Build17625 and test12426 are terminal success.

Physical qualification is LIVE session41955, manager3330244 CPU18,
`paq-register-prior-qualified`. It carries a paid mode byte and checksum (CIXB19)
and captures the complete original native p/y trace on the encoder ONLY; the
independent decoder reads no source or trace. Mode0 restores exactly at45054
framed bytes /45041 native bytes, and all8,127,392 trace bytes match the original.
Modes1/2/3 remain pending at21:43Z; do not claim the predictive saving as physical.
Freeze builder/header/probe/qualifier and binary through completion. The new probe
uses the PLAIN source, unlike the section4 memory/alphabet probes, so their
absolute sizes are not directly comparable. Modes1/2/3 are shared recency
1/8 ambiguous,1/32 ambiguous,1/8 ungated. Before any broader rollout, require
mode1 restoration and unchanged original predictions. This is a predictor
improvement test, not a combinatorial-rank superiority claim.

A new cheap paid-composition screen completed (session33027 terminal) and is
negative. Five causal partitions—field, opcode/field, field/bit, prior opcode,
and byte-bit position—were compared against unpartitioned confidence groups at
four granularities. Exact binomial rank widths plus explicit lengths, counts,
sparse IDs and selection costs never choose a context partition. Proposed layout
sizes45796/45364/45424/45697 all exceed native45041. No decoder was implemented
because the cost screen rejects every tested family. Two tests prove labels
ignore current/future bits and exact widths match the existing type-class coder.
This is a negative layout-cost diagnostic, not a new compressed archive. Preserve
`2026-09-28-field-composition-screen.json`; do not launch its native branch.

Site publication succeeded2026-09-28T21:39:29.108893Z at the existing URL.
Source519295c2e4a640fa76aa6a8c7f233b1429b406d0,
deploymentappgdep_6abade8214608191b7442590febfc8a9,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_33ed5f9fac00819197cd4fa96020ec5b.
It includes completed alphabet/memory pilot gains and15 register negatives,
retains31,175,135/24th, and labels the prior screen unscored. It does not yet
include the new field-composition screen or the still-running qualifications.
No browser handoff in this background goal, no pending Site request.

### Subsequent physical register qualification and live handoff

Mode 1 has now independently restored at 44,904 framed bytes / 44,891 PAQ
payload bytes, saving 150 against the identically framed 45,054-byte control.
The complete original PAQ p/y trace remains byte-identical (SHA51a487fb83a2b35a4ec1a943d5b2262505f91f8c05f05cd5d856e35d3f39f36b).
The compact two-arm evidence is
`2026-09-28-register-prior-qualified-pair.json`. It explicitly states that the
four-arm tournament is not yet complete. Qualification session41955 continues
modes2/3 on CPU18. Do not restart it or alter frozen sources.

The six-trial native-versus-mode1 regional test is LIVE session12360,
`paq-register-prior-cohorts`, one worker on CPU20, using the plain regional
inputs. It has no completed result at21:47Z. The memory tournament32637 now
has two exact positive pairs:70207→69831 (376 saved),96145→95796 (349 saved).
Its third native/mode2 pair remains pending. No extrapolation to full Mozilla.
If both predictors validate across regions, the next useful interaction is a
controlled joint memory/register fork, with each individual predictor as an
ablation and all selector costs included; do not assume additive gains.

The Site has been updated again with the completed register pair and the
negative field-composition screen. Historical Mozilla headings/status wording
was corrected. Latest source d00555b807cac1df7ed30d43a2ecd7b6377faadf,
deployment appgdep_6abae02a9dc081918afb1dbd4c7a3480,
version appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_f3408b10fedc8191a58be3c5d2bcb84f,
succeeded at2026-09-28T21:46:34.554145Z. Cell817 is terminal and collected.
It retains31,175,135 bytes /24th equivalent. No pending publication call.
Credential expires21:48:20Z; renew next time if expired. No browser handoff
because this is the continuing background goal.

At21:47:06Z native v216 Mozilla decode is39.63%; v215-12L NCI decode89.31%;
v215-9L Mozilla encode55.92%; Webster encode99.58%. All lack result.json and
remain unscored. Long-job manager affinities are verified:12L→CPU6,
v216→CPU8,9L→CPUs12/14,derived-table pair→CPUs2/4,field→CPU10. New native
children may need revalidation after phase changes, never restarts. All full
ECOFF jobs remain live, with both ordinary/derived-table and field variants now
in decode. Available memory is bounded; keep pilot concurrency modest.

This goal continuation made verified experimental progress and rejected a
further paid-composition formulation. First place remains unachieved, the goal
stays active, and no GitHub Actions or GitHub push was used.

## Completed predictor controls and the interaction experiment

The previous turn was progress; this turn read the entire controlling attachment
again and revalidated live processes. Goal remains active and unachieved.

Register qualification41955 is terminal success. Modes0/1/2/3 use
45054/44904/44984/46165 framed bytes, respectively. All four independently
restore and every original PAQ p/y event remains byte-identical. The ungated
prior loses1,111 bytes; gating is essential. Preserve
`2026-09-28-register-prior-qualified.json`. Regional session12360 remains live,
manager3344300 CPU20. First native/prior pair73760/73452 saves308 bytes and
restores. Other regions remain pending. Freeze the register fork and dependencies.

Memory tournament32637 is terminal success: all six streams restore; native/
mode2 are70207/69831,96145/95796,97746/97185, savings376/349/561 bytes. Its raw
control flag is false because mode0 was not requested, not because the native
comparison failed. The preceding pilot proved native/disabled identity.
`2026-09-28-paq-memory-feedback-cohorts.json` records this distinction.

New isolated `build_paq_joint_feedback.py` combines the frozen memory and register
patches without modifying either source. One paid outer mode chooses disabled,
memory-only, register-only, or both (native reference is probe mode4).
`paq_joint_feedback_probe.py` uses CIXB1a and the existing section4 transform.
The register mixture still does not alter the p supplied to native model updates;
memory feedback deliberately changes its mixer information. Binary SHA
 a18622557c916a7bea26f9ba88794d480ab858c2bcc27107eb0154ac5fad906d.
Build45006 is terminal success. Six tests pass49.89s (session17708): every mode
restores; disabled payload equals native; each individual ablation's payload is
byte-identical to its earlier separate fork on identical transformed input.

Joint qualified-object pilot is LIVE session71145, manager3362208 CPU0,
`paq-joint-feedback-pilot`, using the memory pilot manifest. At22:02Z modes
4/0/1/2 restore40086/40086/39886/39939 bytes. Mode3 remains pending. Do not
assume additivity; do not change builder/probe/header/native or parent dependencies.
The freed performance core was reused only after the memory tournament exited.

Native Webster v215-9L encoding has completed, but remains UNSCORED until its
independent decode. Decoder3351985 and wrapper3351984 were identity-checked and
pinned toCPU14, leaving Mozilla onCPU12; journal
`2026-09-28-webster9-decode-affinity.json`. Never restart either. At22:02:31Z,
v216 Mozilla decode44.28%, v215-12L NCI decode93.81%, v215-9L Mozilla encode58.02%,
Webster decode3.46%; none has result.json. All other full jobs remain live.
Published target re-fetched21:52:06Z: identical SHA78d29449a1036e1545d3665ccba9de65555f1b5afda78640c2e2b12dde946c86,
322 rows, leader27,825,511. Evidence `2026-09-28-silesia-live-predictors.json`.

Site source9201b97e107528cd949f3decc7c46a268e87904b published successfully at
2026-09-28T21:57:35.231269Z, deploymentappgdep_6abae2c022f08191ae1f261d5775b223,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_9b8d813bb0b08191b53128a8f5309a1f.
It includes all memory/reg controls above, preserves31,175,135/24th and labels
joint feedback pending. Cell839 is terminal and collected; no pending Site call.
Credential expires22:05:04Z. Portable profile was configured this turn.

### Next stronger predictor: numerical screening evidence

`paq_register_adaptive_screen.py` tests five causal experts: unchanged PAQ and
MRU mixtures of1/128,1/32,1/8,1/2 on ambiguous register bits. Integer posterior
weights are learned only after each decoded bit. Two tests pass, including
comparison to exact short-sequence rational Bayes. Eight exploratory settings
show opcode/field partitioning saves296.52 predictive bytes, but global
learning unexpectedly loses718.33. Finite linear posterior floors forget past
evidence; this is not a reliable approximation to unbounded Bayesian evidence.
Do not promote that numerical implementation blindly. Screen95355 is terminal;
evidence `2026-09-28-register-adaptive-screen.json`.

A log-domain control (`paq_register_log_screen.py`) retains Q20 relative log
likelihood scores and derives Q48 coding weights. An expert whose current
coding weight vanishes still retains its score and can recover later. Two tests
pass, including900 bits that force severe underflow then reverse the evidence;
the mixture meets the best-expert-plus-one-bit bound within0.01 bit.
Screen77665 is terminal. Results: global149.41 predictive bytes saved (restoring
the expected control), field-role213.87, opcode/field305.08; native-biased variants
are similar and slightly worse. The qualified fixed prior saved149.70 predictive
bytes. Preserve `2026-09-28-register-log-screen.json` and the negative numerical
control. These are still unscored prediction diagnostics on the selection object.

The next implementation should be a NEW isolated native log-prior fork, not an
edit to any existing helper or binary. Keep original p for PAQ updateModels and
capture the unchanged original trace, as in the successful fixed-prior fork.
A useful control set is disabled / opcode-field log mixture / native-biased log
mixture / old fixed gated1/8; mode3 must reproduce the old prior payload exactly.
Keying by opcode and register field-start is equivalent to the screen's
opcode/field key and is causal before the register bits. Reset at each Alpha
block. Global/field-role controls may be cheaper alternative implementation choices.

The screen uses Python math.log2/exp2 and is NOT yet a portable stream algorithm.
Use pinned mathematical lookup constants and integer interpolation for a native
implementation: e.g.4,097 Q30 log2(1+i/4096) values and4,097 Q48 exp2(-i/4096)
values. Normalize p to Q30 mantissa with its leading-bit exponent; interpolate
log mantissa at12 index bits and18 fraction bits, then round to Q20. Derive Q48
weights from score difference whole/fractional bits with12-bit table index and
8-bit interpolation remainder. Keep all score evidence in signed64-bit state;
rounding tiny coding weights to zero must NOT reset scores. Use unsigned128-bit
products for weighted p and division; no floating computation in the codec.
First verify this proposed table formulation against the screen and a C++/Python
oracle, then build and physically qualify on the original source with exact
native-trace equality. This is a design, not implemented code or measured gain.

### Joint pilot completion and continued regional work

Joint pilot71145 is now terminal success. Native/disabled/memory-only/register-
only/joint frames are40,086/40,086/39,886/39,939/39,742 bytes, all restored.
Joint saves344 bytes versus native and144 versus memory-only. Individual
savings200+147 almost combine, but this is one qualified object. Evidence
`2026-09-28-paq-joint-feedback-pilot.json` is committed.

The twelve-trial joint regional tournament is LIVE in three separate local
processes, each with a single fixed CPU and four arms4/1/2/3. Root
`results/leaderboard/paq-joint-feedback-cohorts`; individual manifests and outputs
are named by cohort seed. Sessions:4274176→37994 onCPU0;
35383296→10268 onCPU18;47712256→87477 onCPU22. Current manager identities and
launch details are in `2026-09-28-joint-cohort-launch.json`. No agent delegation.
Freeze all joint/memory/register builders, helper header, probe, binary and
parent transform closure. Once complete, aggregate all three complete.json files,
compare native and memory-only PAQ payload hashes with the earlier cohort
controls, and retain all physical timings/restoration/source evidence. Raw
control_matches_reference is false here because disabled mode0 is absent;
this batch has direct native mode4 controls and the pilot proved mode0 identity.
Do not mistake the omitted disabled arm for a mismatch.

Fixed-prior regional session12360 continues onCPU20. The first two native/prior
pairs are73,760→73,452 (308 saved) and99,711→99,401 (310 saved); all restore.
The third region is still pending. This uses plain inputs, unlike the joint
section4 inputs, so compare only like-for-like ablations.

Latest Site source cd675416097b854e0746e69e00d09adef57c55b7 published at
2026-09-28T22:09:12.790544Z, deployment appgdep_6abae579a9048191b62a55c984086379,
version appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_6e83874ee9b481918df4335724973500.
It includes the completed344-byte joint pilot, labels the12 regional trials
pending, and retains the full31,175,135-byte /24th-equivalent score. Cell853 is
terminal and collected; no pending publication. Source credential expiry22:17:23Z.
Adaptive log-screen results remain unscored and are not promoted on the Site.

The next code task remains the NEW deterministic native log-prior implementation
outlined above; it has NOT been built. The existing fixed-prior and joint
streams must stay decodable with their frozen binaries. Do not overwrite them.
This turn made verified experimental progress; the complete leaderboard goal
remains active and unachieved. No GitHub Actions or GitHub source push.

### Native adaptive prediction and regional completion (2026-09-28,22:55Z)

This goal turn made progress. The completed portfolio remains31,175,135 bytes,
24th equivalent, default profile19. First place remains unachieved. Read the
controlling pasted-text objective before every goal continuation. No Actions or
GitHub source push. Preserve every live/scored source dependency and binary.

The deterministic log-domain native predictor is now implemented and qualified,
superseding the preceding design-only note. New frozen files include
`generate_register_log_tables.py`, `native/CixLogTables.hpp`,
`native/CixLogMath.hpp`, `native/CixLogRegisterPrior.hpp`,
`register_log_math.py`, `build_paq_register_log.py`,
`paq_register_log_probe.py`, `paq_register_log_qualify.py`,
`paq_register_table_screen.py`, and `paq_register_log_regional.py`.
No floating-point codec calculations: pinned mathematical integer tables;
Q20 scores preserve evidence when Q48 coding weights round to zero. All9 tests
passed49.08s, including native restoration, disabled identity, fixed-prior
payload identity, integer C++/Python oracle, resets and long underflow/recovery.
Fork `paq8px-cix-register-log` binarySHA
2b5f28580b82053f7e15c5f5a681d546b445268c07c1efbf780b70127534de1b.

Physical qualification18586 is complete. Modes0/1/2/3 framed sizes
45,054/44,749/44,753/44,904; all restore, every original native PAQ p/y trace
matches. Adaptive saves305 versus identically framed native, but292 versus
bare native45,041 after all13 outer-frame bytes. Do not conflate those controls.
Evidence `2026-09-28-register-log-qualified.json`. Integer screen saves
305.077644564 predictive bytes, matching the float control within0.000002 byte.
This changes predictive information while retaining arithmetic coding; it does
not establish a smaller hard state space or a same-information rank advantage.

Adaptive regional42203 is TERMINAL success. Framed native/adaptive pairs:
73,760/73,176;99,711/99,119;101,087/100,416. Savings584/592/671 versus framed
native,571/579/658 versus bare native after13 bytes framing,276/282/306 beyond
fixed prior. Three new independent restorations; six old native/fixed frames
retained only after full input/frame/CRC/payload/source/backend identity checks.
`2026-09-28-register-log-cohorts.json`, source report
`results/leaderboard/paq-register-log-cohorts/comparison.json`.
Regions overlap objects and are exploratory, not held-out or projected ranks.

Fixed-prior12360 and joint regional37994/10268/87477 are TERMINAL success.
Fixed regional gains308/310/365 against framed native, all6 restore. Joint
mode4/1/2/3 sizes70,207/69,831/69,896/69,526;
96,145/95,796/95,838/95,494;97,746/97,185/97,379/96,825.
Joint saves681/651/921 versus structural/native,305/302/360 versus memory-only.
All12 restore and native/memory payloads match prior independent tournament.
Evidence `2026-09-28-paq-joint-feedback-cohorts.json`, collector
`paq_joint_feedback_collect.py`. No disabled arm in regional batch; pilot
proved disabled identity. Raw false control flag means absent arm, not mismatch.

NCI v215-12L independently completed22:24:07Z:775,836 bytes, all33,553,445
original bytes restored, encode15,206.334s/decode21,130.887s, peak19,858,432/
15,387,136KiB. Selected CIX447,748 saves328,088 versus this local reference.
ArchiveSHA52467f80ad61f7f0c7ab35ccb34c1d7ef9940c90f698cd9358dc6c4f38ad2b0f.
Result `results/leaderboard/paq-v215-reference/nci/result.json`, compact
`2026-09-28-nci-paq12-local.json`. Runner deletes restored.bin only AFTER
independent byte equality and atomic qualified result; that deletion is normal.
Input/archive/backend/verifier hashes rechecked. Local archive is797 bytes below
author exact NCI value; cause unestablished. No full local12L total exists.
Manager2168849/session65954 proceeded to Webster native3416451 onCPU6.

Latest Site is SUCCESSFULLY deployed, source
44b8404e3ff84f8b0f021e43c630736e13200b65, deployment
appgdep_6abaef0508b08191b0fc6edf2e11a6fc, version
appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_9eccd90d637c81919bfe03008d85f83e,
2026-09-28T22:49:56.867126Z. Includes all adaptive/fixed/joint regional controls,
NCI12L and clear292-byte net pilot gain. Cell891 terminal collected. Site
credential expires22:58:51Z; stored in tool session only. No pending deployment.
Portable profile already configured; background task skips browser handoff.

### Next interactions now live

New isolated `build_paq_joint_log.py`, `paq_joint_log_probe.py`,
`tests/test_paq_joint_log.py` combine memoryopcode/base and adaptive log register
prediction, with0disabled/1memory/2adaptive/3both/4native controls. CIXB1c frame.
Fork `paq8px-cix-joint-log` binarySHA
48f7abee704313908d4ffd0c07b336eddca7f7532eb4c87804c438a7f5dd6425.
Build26157 TERMINAL success. All prior forks stay immutable. Test4607 is LIVE
onCPU24 as of22:55Z; wait for pass before launching physical pilot.
Pilot manifest prepared `results/leaderboard/paq-joint-log-pilot/manifest.json`,
one qualified253,952-byte source. No pilot codecs started yet. Launch all5 modes,
jobs1; only after tests. Compare memory/native payloads with prior pilot and
adaptive-alone with log codec on SAME section4 transformed input.

New `paq_joint_feedback_level6.py` tests fixed joint model at higher effort,
reusing three qualified nativelevel6 frames from GP tournament after full
input/frame/backend/source checks. Session41211/manager3464565 LIVE,
workers pinned0/18/22, about1.7GiB each. Root
`results/leaderboard/paq-joint-feedback-level6`, reportcomparison.json.
All three new joint streams must independently restore. Do not restart or
modify its source closure. Earlier level6 native controls use identical
section4 transform; final transformed hashes must agree.

New cheap `paq_register_multi_prior_screen.py` tests eight log-domain expert
mixtures using causal shared/role recency, opcode/role counts, and occupancy.
Session92231 onCPU20 LIVE. It must reproduce the qualified shared-recency
305.077-byte predictive control to1e-6 before accepting output. Other priors
use only past completed fields. No physical codec, no hard exclusion, no rank
advantage or whole-file extrapolation. Output expected
`docs/research/2026-09-28-register-multi-prior-screen.json`.

Full v216 Mozilla decoder3202350 CPU8 still LIVE,62.52%22:51:55Z.
Archive6,477,226 bytes is UNSCORED until result.json; restored.bin remains0
because PAQ buffers/inverts the archive, not evidence of stall. Other full
jobs revalidated alive; v215-9L Mozilla65.67%, Webster decode16.23%;12L Webster
encode6.04%. Freeze all dependencies. Do not restart on poll timeouts.

Only after v216 Mozilla result.json, run competitive_large_paq against
competitive-filtered-v19 to create competitive-large-paq-v20 using exact
native restoration proof and reversible same-length header substitution.
Then refresh liveleader, update default/reproduction/source package/Site.
Never declare a rank from the unfinished archive.

### Interaction verification completed; latest user requests fresh Site results

Tests4607 TERMINAL success:6 tests passed51.28s. Disabled adaptive-joint
matches native; memory-only matches qualified memory fork; adaptive-only
matches standalone adaptive codec on the SAME transformed input. All modes
restore. Joint log binary remains48f7abee704313908d4ffd0c07b336eddca7f7532eb4c87804c438a7f5dd6425.

Pilot42074 TERMINAL success. For speed, ran only new modes0/2/3 and retained
previous5 verified fixed-joint controls; no duplicate native/memory encodes.
New framed sizes40,086/39,786/39,589. All restore, disabled PAQ payload equals
native exactly. Collector `paq_joint_log_collect.py` checks source/frame/backend,
CRC/payload, transformed-input hashes and transform inversion for every new
and retained row. Evidence `2026-09-28-paq-joint-log-pilot.json`.
Joint adaptive saves497 versus matched structural/native,297 versus memory,
197 versus adaptive alone,153 versus previous fixed joint. All these controls
have13 outer framing bytes and the same structural transform. Comparing against
bare transformed-native payload would save484; do not imply same-information
rank coding superiority or a whole-file result. This is predictive feedback.

Higher-effort41211 TERMINAL success. Level6 native/joint pairs:
69,853/69,250;95,734/95,143;97,063/96,312. Savings603/591/751, all3 new streams
independently restored. Native controls are unchanged previously restored frames,
rechecked with full hashes. Compact `2026-09-28-paq-joint-feedback-level6.json`.

Adaptive joint REGIONAL session98956 is LIVE, discover its manager PID from /proc before acting.
Command:taskset -c0,18,22 python -m benchmarks.paq_joint_log_probe
--output results/leaderboard/paq-joint-log-cohorts --modes3 --jobs3.
Started about23:00Z. No complete regional rows at23:04Z. All three workers inherit
0,18,22, so OS may schedule them between these cores; no strict per-worker pin.
Freeze new builder/probe, log headers/math/tables and parent closure.
After complete.json: verify each frame, input/dependencies/backend, compare to
previous fixed-joint regions at
`results/leaderboard/paq-joint-feedback-cohorts/<seed>/complete.json`.
Those have native/memory/fixed-register/fixed-joint arms4/1/2/3. New joint should
be compared with exact matched physical sizes, especially oldjoint69,526/
95,494/96,825. No adaptive-alone regional arm is present. All three inputs
are exploratory overlapping object cohorts, not held-out. A regional collector
has NOT yet been written. Existing pilot collector assumes unique modes and
cannot directly consume three rows all with mode3. Do not misreport that.
If new combination improves all regions, consider one full level8 native trial
using this frozen fork; select by actual physical bytes and independent decode.

Multi-prior screen92231 TERMINAL. Combining17 experts from shared/role recency,
opcode/role counts and occupancy saves327.977 predictive bytes, only22.900 beyond
qualified persistent mixture305.078. Role recency alone51.787; occupancy6.084;
composition3.254. Full result `2026-09-28-register-multi-prior-screen.json`.
Control reproduced to1e-6. Remains unscored prediction-only; not yet native.

Discount screen96861 TERMINAL. More promising: explicit causal forgetting
improves the same mixture. Retention31/32 saves386.74054 predictive bytes,
81.66290 beyond persistent;127/128 saves379.54344 (+74.46580);511/512339.15241;
2047/2048317.33462. Persistent control305.077644918 recovered to1e-6.
`paq_register_discount_screen.py`, evidence`2026-09-28-register-discount-screen.json`.
This is purposeful adaptation to changing regimes, NOT the rejected numerical
posterior-floor bug. It does not retain the best-fixed-expert regret guarantee.
Scores are normalized after each informative observation, then their nonnegative
penalties are multiplied by(d-1)/d with nearest integer rounding. Uninformative
identical-expert observations skip update/discount. No future data.

Next useful native experiment, NOT implemented: NEW isolated discounted joint
fork, preserving current log/joint binaries. New copies of math/header need
explicit discount in posterior.observe. Suggested modes0disabled,1current
persistent joint,2joint31/32,3joint127/128; memory feedback on for1/2/3. Mode1
must reproduce current joint mode3 payload EXACTLY. All reset equalpriors,
remove old log header's native-bias/mode3fixed semantics in the NEW copy only.
Integer oracle should first reproduce the prediction screen closely; independent
C++/Python tests, block resets, native trace identity across modes1/2/3 (same
memory predictor information), and exact restoration then physical pilot are
required. Old `CixLogMath.hpp` is FROZEN and scores are private; make a new header,
not a live-source edit. New framing magic must avoid all existingCIXB variants.

User asked to update @Sites with new results while research continues. Site
source d724d91d43597222637a3ec899a18b50ac515d5f deployed successfully23:03:19.950704Z,
appgdep_6abaf227c69c8191a2c7a911bfa8a86a, version
appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_c94e4b24a8e8819183ecf2603cfade43.
Includes497-byte pilot and all higher-effort controls. Further source
27db0516930842b6692d934a2b1b182f1c9584c7 replaces top historicalNCI summary with
new497-byte result and refreshes stale21:10 snapshot time to23:04UTC. Whole
31,175,135/24th score remains unchanged. Deployment call cell921 is PENDING as
this checkpoint is written; collect it before further Site changes. Do not
restart save. Current credential expiry23:11:43Z. Source bundle archive
/tmp/cix-site-new-results-visible-20260928.tar.gz is immutable until completion.

All full jobs still live. Runtime snapshot`2026-09-28-local-jobs-2303.json`:
v216Mozilla decode66.20%;v215-9L Mozilla encode67.22%,Webster decode18.71%;
12LWebster encode7.87%. NCI12L complete as above. No pending full result may
enter score. Overall goal ACTIVE, unachieved, unblocked; this turn made progress.

Latest Site publication COMPLETE: cell921 terminal collected. Source
27db0516930842b6692d934a2b1b182f1c9584c7 deployed successfully
2026-09-28T23:05:27.669721Z, deploymentappgdep_6abaf2a7738c8191bc8bc0089ab2448a,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_4a068fe4ac7c819199a7524a7ee408d5.
New497-byte verified experiment is visible in the top summary with fresh23:04UTC
snapshot and explicit probe-versus-whole-corpus distinction. All supporting
artifacts linked. No pending Site call. Background research skips browser
handoff; deployed URL returned to user. Research goal continues active.

### Continued turn23:07–23:29Z: stronger predictor and requested comparison table

Read full controlling objective this turn. Previous turn was progress; current
turn also made progress. Overall goal remainsACTIVE, unachieved, unblocked.
Full portfolio remains31,175,135 bytes,24th/322 equivalent. Source branch local
only; no Actions or GitHub push. The Site source repository is separately
explicitly authorized. Do not edit dependencies of any scored/live codec.

Adaptive joint regional98956 TERMINAL success. It initially ran all3 native
jobs onCPU0 despite0,18,22 affinity. Identity-checked worker+decoder threads
were explicitly pinned to separate0/18/22; no restart. Journal
`2026-09-28-joint-log-regional-affinity.json`. Future jobs need ONE CPU per
worker/manager, not a mixedP/E mask that Linux may concentrate on the P core.
Final new sizes69,251/95,214/96,515. Savings956/931/1,231 versus matched native,
580/582/670 versus memory-only,275/280/310 versus fixed joint. All3 new streams
restore. Collector `paq_joint_log_cohort_collect.py` checked12 previous frames,
source/input/backend hashes and transform inversion. Evidence
`2026-09-28-paq-joint-log-cohorts.json`. No adaptive-only regional arm; overlapping
exploratory cohorts, not held-out or full-file results.

Deterministic discounted native fork IMPLEMENTED and FROZEN:
`build_paq_joint_discount.py`, `paq_joint_discount_probe.py`,
`paq_joint_discount_qualify.py`, `register_discount_math.py`,
`native/CixDiscountLogMath.hpp`, `native/CixDiscountRegisterPrior.hpp`.
Old math/helper/forks unchanged. FrameCIXB1d. Memory opcode/base feedback active
for1/2/3;0disabled;1persistent;2retention31/32;3retention127/128. All equalpriors.
New native posterior adds explicit nearest-rounded discount to normalized
nonnegative log penalties. Identical-expert events skip update/discount.
Fork `paq8px-cix-joint-discount` binarySHA
7f8a4605eca962cd6015839922afb2f2f7dd669d597921c216919aaf620e8b5a.
Build12796 TERMINAL. Initial3 integer/helper tests80188 passed1.54s. Full9 tests
19403 passed41.25s, including block resets, long-regime adaptation, all native
modes restore, disablednative identity and persistentprevious-joint identity.

Integer screen55993 TERMINAL. New `paq_register_discount_table_screen.py`
reproduces preliminary float screen within0.000002 predictive byte. Retention
31/32 saves386.740541781 predictive bytes,81.662897217 beyond persistent;
127/128379.543441738 (+74.465797173). Evidence
`2026-09-28-register-discount-table-screen.json`. Shifts9/11 remain diagnostic
oracle cases; native profiles expose only5/7 andpersistent. No hard elimination.

Qualification66486 TERMINAL success. Modes1/2/3 =39,589/39,505/39,513 physical
bytes; all3 independently restored. Every underlying memory-aware PAQ p/y trace
identical byte for byte. Persistent PAQ payload exactly matches oldjointmode3.
Best saves84 versus persistent and581 versus matched structural/native40,086;
all13 outer framing bytes included. Bare transformed-native difference568.
`results/leaderboard/paq-joint-discount-qualified/complete.json`, compact
`2026-09-28-paq-joint-discount-qualified.json`. New pilot uses independent
ProcessPool workers with explicit single CPU per mode. Qualifier also checks
native provenance's generated source hashes, not just builder/binary.

Discount REGIONAL jobs LIVE, each mode2 only,jobs1, separate immutable manifest:
root`results/leaderboard/paq-joint-discount-cohorts`:
4274176→session95046,manager3530358,CPU0;
35383296→13817,manager3530360,CPU18;
47712256→8862,manager3530359,CPU22.
Started23:26Z; still live/no complete rows23:29Z. Never restart on polltimeout.
After all complete, compare exact frames to persistent-joint69,251/95,214/96,515
and retained matched native controls. Need NEW collector; not implemented yet.
If all improve, consider one full Mozilla level8 candidate onfreeP0. No full
native joint/log/discount trial has yet been launched. Compare with pending
full section4/native8 control as well as incumbent; all must fully restore.

User latest steering: wants Site TABLE, left column algorithm, top columns
ratio, compression speed, decompression speed; only best case per algorithm,
not many versions; wants to see where CIX fits. Delivered a prominent9-family
table and folded prior detailed experiments/per-file variants under a native
`details` section. Preserve this product direction on future Site changes.

Silesia source re-read withweb andindependently fetched23:18Z, exactly322 rows,
unchangedSHA78d29449a1036e1545d3665ccba9de65555f1b5afda78640c2e2b12dde946c86.
Snapshot `2026-09-28-silesia-comparison-source.json`. Published Silesia table has
NO speed columns; do not import enwik9/other-corpus timings into Silesia rows.
Families displayed:PAQ (branches grouped),cmix+Precomp,CIX,ZPAQ+Precomp,
LZMA/LZMA2 (7-Zip/plzip/XZ grouped),Brotli,Zstandard,bzip2,gzip. Explicitly a
selected-family comparison, not a new official rank. Best physical size wins;
any published best may have no matched speed. Never transfer speed from a
different/larger variant. Native publishedratio leaders13.13%,cmix13.33%,
CIX14.71%,ZPAQ17.27%. CIX is12.04% larger than publishedleadingbytes, remains24th
among322 configurations. No claim of official3rd from grouping.

New reference speed runner `silesia_speed_reference.py`, session91814,
manager3514049,CPU20 (singleE core), LIVE. Complete canonical Silesia, each
algorithm separately compresses12 files; every stored archive decoded3 times;
median per-file decode, one encode, decimal originalMB/s. IO included where
specified; comparisons/source reads excluded. Concurrent research workload,
not a uniform quiet-machine speed contest. Root
`results/leaderboard/silesia-speed-reference-20260928`. Source frozen.
Completed so far:
Python gzip9:67,643,417B,9.211749MB/s encode,160.321499decode (NOT selected).
bzip2:54,506,769B,8.256841encode,8.543460decode (tiespublishedbest,selectlocal).
zstd1.5.7level22:52,364,062B,1.038443encode,420.599148decode (betteroldpublished).
xz9extreme:48,456,004B,1.073114encode,57.730649decode (largerthanpublishedplzip
48,335,267; therefore NOT selected and MUST NOT lend its speed to plzip).
Brotli1.2.0q11lgwin24 is still running. Do not restart. On completion, collect
session91814 and regenerate comparison evidence+Site; it may improve the
published50,297,179-byte Brotli row or may remain unselected.

Separate GNUgzip-9-n-c runner1739 TERMINAL. Root
`results/leaderboard/silesia-gzip-speed-native-20260928`, all12×3decodesverified:
67,631,918B,8.394519encode,115.235087decode. Smaller than published67,631,990,
so select it instead of Pythonzlibgzip. Name/time metadata omitted, all format
headers/checksums counted. CPU24, CLI pipe+artifactIO included. Noapproximation.
No nativeplzip/lzip/7zz executable available. Do not fabricate missing speeds.

Evidence generator `benchmarks/silesia_comparison_evidence.py` checks all physical
local frames and corpus hashes, selects min complete output (tiesfavor timedlocal),
and verifies current CIX12frames. Current CIX compression is NOT timed endtoend;
researchcache bookkeeping zeros are NOT speed. CIXdecode≈0.008691689MB/s is
211,938,580 bytes divided by the sum of recorded12 per-file verification times.
Label historicalaggregate/mixedcores+load; not fresh uniform measurement.
Generator arguments `--cix` defaultportfolio19 andrequired`--output`.
Current generated evidence `/tmp/cix-family-comparison.json`, copied toSite.
After profilechanges, explicitly pass its newcomplete.json; do not retain19.
A final compact research comparison doc should be written after baselinebatch
completes; not yet done. Generator also stores unusedlocal candidates toshow
why their timings are notassigned to the bestpublishedrow.

Site renderer NEW `/home/user/src/cix-research-site/scripts/render-comparison.py`
accepts evidenceJSON; creates9unique algorithm rows,4requestedcolumns,
highlightsCIX, exposes methodology/settingsfold, updates timestamp/statusJSON.
Staticlinks/entry andtableuniqueness verified. No screenshot/browserQA requested.
Historical table nowhidden inside`details#research-history`; comparisonsection
marked`<!-- comparison:start -->...<!-- comparison:end -->` for updates.
The source includes newest regional anddiscountpilot proofs inresearchhistory.

LATEST SITE SUCCESS: sourcebc8b91b324d72561ad95a825ef6aab3a1ace4006,
deploymentappgdep_6abaf80231e48191b65569bb2f0a38f3,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_60fe48ca65588191b783f6e08e5f5cf9,
2026-09-28T23:28:18.032449Z. Cell947terminalcollected; no pending publication.
Credentialexpires23:36:27Z (toolstoreonly). Portable profileconfiguredthisturn.
Backgroundresearchskipsbrowserhandoff. Currenttablehasnumeric speeds for
zstd,bzip2,gzip andhistoricalCIXdecode; otherbestprofilesexplicitlyNotreported,
CIXencodeNottimed. This is deliberate evidence discipline, not estimated data.

Full v216Mozilla decoder3202350CPU8 remainslive,76.83%23:29Z; result.jsonabsent.
Do not project6,477,226-byte unfinished archive into rank. All originalfulljobs
continue. Once verifiedresult exists, qualifyportfolio20,refreshliveleader,
updateCLI/reproduction/sourcepackage AND newfamilytable plusSite; no source
workflow/GitHubActions. Overall objective is stillfirstverifiedtotal belowliveleader.


## Continuation 23:47Z — discounted regional completion and comparison speeds

Progress: all three new discounted-joint regional streams restore independently.
Physical sizes 69,154 / 95,137 / 96,388 bytes; improvements 97 / 77 / 127 over
persistent adaptive joint, 1,053 / 1,008 / 1,358 against matched native controls.
Collector `paq_joint_discount_collect.py` and compact proof
`2026-09-28-paq-joint-discount-cohorts.json` committed in befb436. These selected,
overlapping constructed regions are exploratory, not a new full-corpus score.

Launched ONE complete Mozilla discounted-joint mode2/native-8 candidate at
23:37:27Z, `paq_joint_discount_full.py`, session39592, manager3550731,
native3551095 CPU0. Root `results/leaderboard/paq-joint-discount-full8`;
status encode. Full source/transform/fork/decode closure FROZEN. No score or
rank until the permanent frame independently decodes and all bytes compare.
This run compares a strengthened predictor while retaining arithmetic coding;
it does not establish a same-information intrinsic advantage for ranks.

Added prospective `qualified_structural_paq.py`, `competitive_native_fields.py`
and `competitive_native_got.py`. Parent remains profile19. They accept only
complete full-frame proofs with current source/backend/input/frame identities,
recompute and invert the structural stage, and honestly reuse the original
exact independent full native decode; they never claim a fresh multi-hour
decode. New tests reject partial proofs and changed input/mode/backend/source/
frame, and independently restore both a real regional field stream and a
fresh small native GOT stream. Eight tests passed in36.83s onCPU24.
No profile promoted; no live/scored codec or dependency was modified.

The reference speed batch91814 TERMINAL, all five algorithms completed.
Brotli1.2.0q11lgwin24:49,564,563 physical bytes (23.386286% of canonical211,938,580),
compression0.325814636MB/s, decompression160.649716MB/s. All12 stored archives
decoded three times byte-exactly. This beats publishedBrotli50,297,179bytes,
so it now supplies both ratio and matching speeds in the Site comparison.
All measurements taken concurrently with research work, not quiet-machine
speed rankings. Existing same-result timing discipline preserved: published
plzip48,335,267 still beats localXZ48,456,004, so noXZ speed is assigned toplzip.
Final comparison evidence now `2026-09-28-silesia-algorithm-comparison.json`.
CIX remains31,175,135bytes,14.709514%,24th/322,3,349,624aboveleader. No uncached
end-to-end CIXencode timing exists; historicaldecode≈0.008691689MB/s explicitly
mixedCPU/load. Table has9selectedfamilies and4requestedcolumns. Latest new
regional evidence also added behind research-history. Sitepublication pending.

Critical full jobs revalidated23:43Z: nativev216decode3202350CPU8; fieldsdecode
3317410CPU10; GOTdecode3517578 onEcores; otherfullstructuraldecoders3289734CPU4,
3292069CPU2; priority9Lencoder2571939CPU12 andWebsterdecoder3351985CPU14;
12LWebsterencoder3416451CPU6; pointer/sectionencoders3007311/3049296 onEcores.
Memory8.6GiBavailable, noadditional large native concurrency launched.
First qualified full candidate may be integrated immediately; do not wait for
all full trials and do not count incomplete physical archives.


Site publication succeeded2026-09-28T23:47:47.304293Z. Source
c79731eaf7595da9711d718b36b206408ee772ec; deployment
appgdep_6abafc935de08191a518f20e88a645d0; version
appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_45fbdb35f4d08191aa4486d0b6e0b94d.
Cell971 collected terminal; no pending deployment. Site now has completed
Brotli ratio+matching speeds and all three discounted regional results behind
the research fold. Source scientific checkpoint90db287. Knownprivateaudience
preserved; onlySitespush, noGitHubActions. Credential toolstore expires23:55:44Z.
Backgroundresearch retains URL handoff without opening another browser tab.


## Broad-frontier continuation 2026-09-29T00:04:50.909828+00:00

User steered: investigate all opportunities for substantial compression changes,
all techniques needed to win. UpdatedAGENTS andnew
`2026-09-28-broad-opportunity-frontier.md`; earlierfocusnotexclusivearchitecture.
Nochange tolocal-only,sourceeligibility,exactroundtrip ornoActions constraints.

NEW CIXI2multiscalevolumeexperiment,source1a7b564. Eight tests pass0.36s.
Six completeMR/Xraystreams roundtrip; session92540terminal. Every nontrivial
pyramid loses. MRidentitycontrol1671099onlysaves2framingbytes relative1671101,
notamodelgain; preservedbutnotdefaultportfolio. Evidence
`2026-09-28-multiscale-volume-negative.json`. No rerun justified.

NEW directvisible-stateaffine/LCGscreen,scriptgenerative_rule_screen.py,
session60519terminal. Full99998parsedOSDBrows, offset-awarefit fromprefixthen
fullcountallrules: bestmatchingtransitions6/2/1062/10 forcolumns0/1/2/5 outof
99997. Theearlierpreliminaryzero-offsetscreenhad6/2/1000/3; useformalnewJSON
`2026-09-28-generative-rule-screen.json`. Noexactrecurrence, nobytesoranksclaimed;
hiddenstategeneratorsandshufflesremainopen. NaiveconditionalMIwithuniquevalues
wasoverfit, notcompressionevidence.

CMIXv21pristinesourcefromauthor731518BZIP SHA
8fd46731ed0125707021c2db4feb24179617b3993b735c335f2e0b3c00e5a0dc.
Build13812terminal; GCC13.3CPU22,-O3 -ffp-contract=off -fno-fast-math.
BinarySHA d4a5566fe3a58b8f8af722800963cbb7f3f88d5be8dbd8ffb579ed482f4fc558.
Build/source/licenseprovenance`2026-09-28-cmix-preprocessor-build.json`.
Preprocessing-only-s andstored-davoidlargePredictorallocation. FullneuralCMIX
needs~32GiBrecommended; currently~7GiBavailable, notstarted. GPUisGTX1650,4096MiB
with929MiBfree atinspection; don'tassumeunlimitedGPUcapacity. NNCPcurrentCuses
binaryLibNC, sourceeligibilityneedsreview; earlierPythonversionisanalternative.

NEWpaid_word_transform.py CIXB1e usesinput-learnedfrequencydictionary, CMIX-s
reversiblewordreplacement, andidenticalentropybackend. Entire dictionarytravels
insidecompressedpayload; noexternaldictionaryortrainingcache. Eight marker,
capitalization,arbitrarybinaryandemptyroundtrips passed0.20s. Sourcef37a3f5.
Six matchedPAQ-v215-4 regionalstreams (rawvsword onthreeexisting64KiBWebster
fixtures),runnerpaid_word_probe.py session37320LIVE,CPU20singleworker. First
rawcontrol12257Brestores. WholedependencyclosureFROZEN. Root
`results/leaderboard/paid-word-paq-regions`; collectallresults,discriminatebefore
consideringafullfile. Currentqualifiedscoreunchanged31,175,135B,24th/322.

Nativev216Mozilla decode3202350CPU8revalidated00:03Zat93.18%;result.jsonabsent.
Otherfullrunsstillalive. No projectedscore. Newfamilytablealreadypublished,
nowpublishingbroadscope+completednegativesintherearch-historyfold. No new
algorithmvariantsaddedtotheprimarytable.


LatestSitepublicationSUCCEEDED2026-09-29T00:06:34.447782Z:
source8fd471525ee880a0c6833886736b0ad862d7ad62,
deploymentappgdep_6abb00fa92fc8191bc63257fa67afbd9,
versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_42cbb95412988191883a6732f598a68f.
Cell1002terminalcollected. No pendingSitecall. Primary9-familytableunchanged;
newbroadscopeandimage/ruleevidencepublishedinsideresearchhistory.
Credentialtoolstoreexpires2026-09-29T00:14:48.699Z.
Paid-wordfirsttwo controls:12257->13264,12827->13831physicalB,loss1007/1004.
Allfourrestore. Thirdregionstillrunningatlastpoll. Whole-word-dictionarycost
mayamortizeatlargerscales; don'tinterpretregionalnegativeasproofagainstallWRT.
Needcollectsession37320androotcomplete.json beforedrawingbatchconclusion.
Fullnativejobscontinue; noadditionalhigh-memoryCMIXprocessstarted.


Correction afterterminalcollection: paid-word37320 COMPLETEDat00:07Z. Thirdpair
14387->15471,loss1084B. Allsixrestore,currentdependenciesandphysicalframehashes
checked. Rootcomplete.jsonpresent,compactproof
`2026-09-29-paid-word-regional-negative.json`. Nohypothesisoflarge-blockamortization
isdisproven; donotrunfullnativebasedonnegative64KiBbatchwithoutacheaperscalegate.
Sitewordstatusupdatedfromrunningtocompleted;publicationagainpending.


FINAL Site status for this continuation: source
c7d3840796228515a7dea769b62974dbdc799908; deployment
appgdep_6abb01bb2e808191b3447f464746e3b5; version
appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_a8b6b80c83148191b227439e3b84bc10;
succeeded2026-09-29T00:09:46.546664Z. Cell1009terminalcollected, nopendingSitecall.
All6paid-wordcontrolsnowdisplayedascomplete, all6imagecontrolscomplete, rule
screencomplete. Sourcecheckpoint2074712. Bothcheckoutsotherwiseclean. Primary
comparisonremainsonebestrowperfamily, CIX31,175,135B/24th withqualifiedspeeds.
Next priority: collectnativev216Mozilla fullproofwhenready(95.01%at00:07Z),
qualifycompleteportfolio,refreshliveleaderandcompleteallreproducibility/default
CLI/Siteupdatesbeforeclaiminganynewrank. Prospectivefields/GOTqualification
alsoavailable. Fullnewdiscountjoint39592stillrunningCPU0;sourcefrozen.
Broadexperimentalbranchesfinishednegative;largerWRTamortizationandstronger
neuralmodelsremainresearchoptions, notverifiedimprovements. Do notlaunch
32GiB-CMIXwhileonly~7GiBavailable orassume4GiBGPUentirelyfree.


## 2026-09-29: historical audit and first equivalent position

The user asked whether a previous #1 or better-than-24th result was discarded.
Audited all572 reachable source commits and refreshed origin refs,292 unique
historical documentation/result blobs,42 Site commits, saved memory and the
available local session. No earlier verified full-Silesia result above24th was
found. The27September generic-only policy did remove token/raster specializations;
no retained full-Silesia winning result accompanies them. The earlier
“Restore known baseline” commit removed benchmark automation, not codec code.
Detailed scope and evidence:2026-09-29-historical-rank-audit.md. Mobile transcript
before this local session is unavailable, so this does not rule out an earlier
unsubstantiated conversational claim.

During this audit, v216-8 Mozilla completed independent restoration at00:16:01Z.
Its6,477,226-byte archive restores all51,220,480 original bytes exactly. Qualified
portfolio20 totals26,402,526 bytes over all12 canonical independently compressed
files, saving4,772,609 from portfolio19. All unchanged frames, original bytes,
source/backend identities and restoration evidence were checked again. The
physical six-byte CIX header replacement reverses to the exact decoded PAQ
archive without size overhead. Full report:results/leaderboard/competitive-large-paq-v20/complete.json.

A fresh live leaderboard read at00:22:37Z remains322 entries, leader27,825,511.
The new total is1,422,985 bytes(5.113958%) below that leader: equivalent position1.
This is the first substantiated local #1-equivalent total, not a recovered older
win. It is a heterogeneous PAQ-backed CIX portfolio and does not establish
intrinsic enumerative-coder superiority. The default CLI now selects portfolio20;
9 relevant existing qualification/codec tests pass in0.82s. Public-source release
and official listing remain pending; private GitHub source was not published.
Compact proof:2026-09-29-competitive-large-paq-milestone.json. Source release
preparation and Site update follow, with all pending full-file research preserved.

The new full-member paid-WRT+Brotli scale experiment(session96615) also completed.
All4 frames restore: Dickens2,827,959→2,657,808 bytes(dictionary142,716);
Webster8,429,248→8,201,364(dictionary335,281). This shows dictionary amortization
can reverse the earlier64KiB negative, but both results remain larger than the
selected PAQ streams. No extra leaderboard saving or PAQ prediction is inferred.
Its frozen sources are in commitfba951e; results/leaderboard/paid-word-brotli-whole.

Portfolio20 source-only package prepared atresults/releases/cix-source-portfolio20-20260929.tar.gz,
3,147,164 bytes SHA256d53c5509318620249da31a2cf5299c2b6f5497a7043f7bcc7788021bc35c7637,
source6e704a3ae38a8438c3db441f3b1e212d8f089464. All1059 native source/provenance files
match the prior isolated source; all7 qualified rebuilt binaries are unchanged.
Fresh uncached portfolio20 CLI smoke encoded488→58 bytes and independently
restored exactly. No corpus/cache is in the isolated source directory or archive.
This does not repeat the full native Mozilla decode; its full restoration proof
was reused only after exact identities and inverse-wrapper equivalence.
Public source was not released and official submission was not sent.

Site source06bf39fb12cecd7ed850e11cea43e48504dc834e was pushed only to the
Sites source repository. Deploymentappgdep_6abb065c53d08191a520fdfaf22a5401
(versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_a3fb88cab1608191a4256e5ba9a2dcbd)
succeeded2026-09-29T00:29:36.646752Z at
https://cix-research-lab.matthewaldous.chatgpt.site/. The nine-family table now
shows CIX first,26,402,526 bytes,12.46%,5.11% below the published leader,
with official-listing/public-source caveats and the historical audit.
Static entrypoint, asset links, report totals and table ordering passed.
Background research update: no browser handoff or extra browser testing.

Goal-turn outcome: material progress, first equivalent numerical size achieved.
Do not mark the published-leaderboard objective complete while freely downloadable
public source and official listing remain pending. No source-repository visibility
change, public release, maintainer message or Actions job was made. Remaining
full-file trials remain untouched; revalidate their process state before resuming.
The history question is answered from available records; no older lost #1 was found.


## 2026-09-29: publication preparation and contribution audit

Previous goal turn: progress(first-equivalent full score, history audit, Sites).
Read the entire controlling attachment again. Current repository clean before
this turn. Revalidated all remaining native processes: v215-12L reference on
Webster; v215-9L Mozilla encode andWebsterdecode; complete-Mozilla ordinary,
structural-fields andshared-symbol decoders; pointer/section encoders; discounted
joint full encoder. All live and CPU-active at00:30Z; no restarts or source edits.

Read-only GitHub confirms research source remains private; proposed standalone
maldous/cix-silesia repository does not exist. Prepared an exact maintainer
submission draft from the actual12 sizes, model attribution, source hash,
build/measurement limitations and publication plan. Recipient comes from the
maintainer's own website. No message was sent. Asked the user asynchronously
for explicit permission to publish only the prepared source in a NEW public
repository and/or send the prepared submission. Existing private research history
would remain private and no workflow files/Actions would be used. Permission
is pending; elapsed time is not approval. This is not yet a three-turn blocker:
independent qualification and running experiments continue to make progress.

Completed24-stream selected/control contribution audit: nativePAQv216-8 total
28,803,779; CIX26,402,526; saving2,401,253(8.34%). MR saves149,560; NCI361,713;
OSDB319,094; SAO1,570,886. Eight files retain nativePAQpayloads. NCI/OSDB use
v215 in their transformed pipelines, so these are whole-pipeline comparisons,
not isolated-transform ablations. Exact author v215-12L comparisons stay separate
from incomplete local high-effort reference reproduction.

An additional source-isolation audit passed: traced CLI smoke decode had zero
original source/corpus/cache reads and no network connections; renamed-input
level8 native archives were byte-identical. The source archive's1477 members
contain no workflows, binaries or saved benchmark streams. The trace and scoped
evidence are in2026-09-29-portfolio20-isolation-audit.json. These are extra small
reproduction checks, not substitutes for the existing full-member proofs.
Completion audit/contribution files explicitly preserve every incomplete item,
including public source, official listing, full v215-12L reference and exhaustive
per-model ablations. No goal-complete claim is made.

Site source44a5c70383701a1a758d4dbd56bd283add1bbafd was published privately,
deploymentappgdep_6abb08bb59f081918526d5448f0b3e8c
(versionappgprj_6aba005773a08191ae8a7978a687b3cb~appgver_900ed91a1dd881919bb60e1e9633dbdc),
succeeded2026-09-29T00:39:40.094594Z. It now explains the four full-file
contributions and links the isolation audit. No browser handoff for this
background goal update. Source code has not been published publicly.
All18 explicitly tracked native/managerPIDs were revalidated live again;
see2026-09-29-local-jobs-0040.json. The publication/contact decision is still
unanswered. Currentturn outcome: progress(contribution audit, source-isolation
evidence, concrete submission draft and Sites). Goal remains active; no
completion or blocked threshold claimed.


## 2026-09-29: guard the winning parent during future qualification

Previous turn was progress: release isolation, contribution audit, submission
preparation and Sites. Read the full objective again. Revalidated the eighteen
tracked native/manager processes live; the new field/GOT/stronger-Webster results
still have no completed certificates. The public-source/contact question remains
unanswered. No permission was inferred and no publication/submission attempted.

Prepared a prospective field successor that extends portfolio 20 rather than the
older portfolio 19 used by the earlier prepared wrappers. A new successor runner
rejects incomplete or mismatched parent policies before invoking the existing
strict physical/source/restoration verifier. Eight tests passed in 0.22s. Four
independent compatibility decodes passed: full MR (9,970,564 original bytes), full
SAO (7,251,944), an existing 73,728-byte regional field frame, and a 488-byte native
PAQ smoke. No complete new field score is inferred. Default remains portfolio 20.
Commands and scope: 2026-09-29-next-structural-qualification.md; proof:
2026-09-29-native-fields-successor-check.json. Commit: d10bed7.

Moved the existing shared-symbol decode 3517578 and worker 2865490/manager 2865430
from efficiency cores to the free performance core 8. Exact process identities
and parent relationships were checked before mutation, and affinity read back.
No restart, source edit, archive edit or new high-memory process. The first guard
attempt failed before mutation because the worker's command is multiprocessing
spawn; the corrected guard verified that exact command and PPID. Its measured
runtime now spans CPU placements, explicitly recorded in the reassignment proof.

Portfolio 20 source dependencies and total were checked again using .venv Python.
An initial system-Python check failed to import imagecodecs before making any
changes; that environment error does not affect the qualified result. The prepared
3,147,164-byte publication archive remains byte-identical at SHA256
 d53c5509318620249da31a2cf5299c2b6f5497a7043f7bcc7788021bc35c7637.
The Site remains at the latest first-equivalent result; no new size milestone
justifies another deployment. Current turn is progress (successor qualification
and actual compute reassignment), not completion. Publication/contact remains a
pending user decision; continued live local work means no blocked state is set.


## 2026-09-29: publication decision blocks the official-listing goal

Read the full controlling attachment. Previous turn was progress; this turn
revalidated the winning twelve physical frames, frozen dependencies and source
archive, confirmed the source repository is still PRIVATE, and re-read the live
leaderboard: no CIX listing, leader still 27,825,511 bytes. The prepared result
remains 26,402,526 bytes and all twelve complete restoration proofs are intact.

The explicit publication/contact question has remained unanswered for three
consecutive goal turns: submission preparation, successor safeguarding, and this
revalidation. Required preparation is complete and reviewable. More compression
refinement does not resolve public-source eligibility or authorize contacting
the maintainer. The goal is therefore being marked blocked on that decision,
not complete or paused. No additional permission question is sent.

Existing local jobs are preserved and can finish without further interaction.
The pointer encoder 3007311 completed normally; its existing worker 3007055 now
has live decoder 3676928. Other tracked managers/native workers remain live;
GOT decoder 3517578 remains on CPU8. No process was restarted or cancelled.
No partial output is scored. Existing high-effort reference and model trials
remain incomplete; do not imply an exhaustive research programme is finished.

On resumption, inspect current processes/artifacts and the user's exact decision
before publishing anything. The reviewed source package remains the frozen
portfolio20 release candidate; later prospective profiles are not that package.
The latest Site remains deployment appgdep_6abb08bb59f081918526d5448f0b3e8c,
source44a5c70383701a1a758d4dbd56bd283add1bbafd. No Site update is needed for a
publication-permission wait. Full audit:2026-09-29-publication-blocker-audit.json.


## 2026-09-29: user renewed research for a greater lead; portfolio 21 qualified

The user explicitly requested continued local research/experiments for a greater
lead and ongoing Site updates. This renews research work independently of the
still-unanswered public-source/contact decision. Do not treat that publication
question as blocking further compression experiments. No source release or
maintainer contact has been authorized by this message.

The completed full Mozilla fields worker restored all 51,220,480 source bytes
from 5,956,286 physical bytes. Parent-aligned portfolio 21 qualification passed
all input/frame/source/backend checks, recomputed and inverted the transform,
and preserved the exact completed full-decode certificate. The other eleven
streams remain unchanged. New total 25,881,586; first equivalent among 322
published rows; 1,943,925 bytes (6.9861%) below the live 27,825,511-byte leader.
Live page fetched byte-identically before claiming. Default CLI now uses v21.
Eight successor tests pass; prior independent v21 decoder compatibility proof
is retained. Compact milestone and five-replacement contribution reports are
2026-09-29-competitive-native-fields-milestone.json and
2026-09-29-portfolio21-contributions.json. Native v216 -8 total 28,803,779;
CIX saves 2,922,193, across five whole-pipeline replacements.

Newly completed same-version/level full controls: ordinary v215 -8 Mozilla
6,477,271; basic structural mode 3 6,043,629; field prediction 5,956,286.
All complete physical frames restore. Field prediction saves 520,985 bytes
against ordinary native PAQ, including added wrapper costs. This is a structural
model gain, not an intrinsic enumerative-vs-arithmetic advantage.

Site publication succeeded 2026-09-29T01:54:31.018286Z, source
403f0f8d391831146b3300120fa197fd238e0144, deployment
appgdep_6abb1a462144819184a2c5d55b549845. The nine-family/four-column table,
scorecards, full-member table, contribution evidence and new controls show v21.
Previous portfolio20 source archive is preserved unchanged and explicitly
historical on the Site; it does not certify a new v21 isolated package.

Research continues: existing pointer decode 3676928 moved to free P core2,
section decode3716867 to free P core4 after PID/PPID/command validation. Neither
restarted; source/frame artifacts unchanged, timing spans CPU placement.
New grid_backend_probe uses a separate frozen frame CIXB1e. Eighteen matched
128KiB-ish full-frame probes cover three disjoint source regions, modes ordinary
PAQ, grid feedback, bounded ranks, same-constraint arithmetic, fixed bits and
bounded-rank Brotli. All bounds/framing are counted. Process session66941,
root results/leaderboard/grid-backend-regions-20260929, three workers permitted
CPUs10/16/18. Regional results do not change rank. Qualify the whole member only
after the complete-byte frame restores; no projections.

Prospective competitive_native_got_v22 extends current21 and uses the same
strict successor-parent guard. The original native GOT whole-file worker must
complete its independent restoration before qualifying any22 result. If another
profile wins first, create a new aligned successor; never score a different
encoder parent. Existing full PAQ, shared-symbol, pointer, section and discounted
joint experiments remain local and frozen. No GitHub Actions.


### Grid backend tournament complete; full-member experiment continues

All18 matched regional frames restore exactly. At offsets0/3625972/7120876,
bounded-grid PAQ-4 sizes40710/38034/43339 versus bounded-grid Brotli
42389/39736/44918: savings1679/1702/1579. Same-constraint arithmetic
40715/38037/43343 loses only5/3/4 bytes to ranks. Feedback-only PAQ
40869/38501/43309 wins the final region by30bytes but loses the first two.
Ordinary PAQ70532/70843/72631; all framing paid. Fifteen additional Brotli
invariant cases retain nonfinite floats, negative zero, nongrid values and tails;
each rejects a damaged header. Eighteen regional source/frame/backend proofs
verified again by collector; no regional result is scored.

Launched full SAO bounded-rank-PAQ8 then feedback-PAQ8 sequentially, one worker
onCPU10: results/leaderboard/grid-backend-full8-20260929. Seven GiB available
before launch; each native-8 run approximately4GiB, existing jobs preserved.
Compare full physical bytes to selectedSAO2159749 only after complete decoding.
The regional pilot initially sharedCPU10; a bounded process-tree controller
then pinned its three workers individually to10/16/18. No scored source edit or
restart. Its session36166 ends automatically when manager3801484 exits.

Portfolio21 isolated source candidate prepared from0caf14c,1481files;1076native
source/provenance files matched previous20. Reused seven previously qualified
native binaries, fresh uncached small CLI encode and independent decode pass.
Source-only archive3150348bytes SHA256
35509b2011b6aa98e5c6d11617bfa70c7bf76a512ed23cfe8407af5926130e3b.
No corpus, streams, binaries or workflows in archive. The first smoke mistakenly
resolved the virtualenv executable symlink to systemPython and failed at import;
correct virtualenv rerun passed before output. No publication authorized.


Latest Site publication succeeded2026-09-29T02:04:35.136159Z, exact source
53e0c53b3b16304a56149d056a185aa34781b33f, deployment
appgdep_6abb1ca26cc08191a5402adc50d66627. It includes all18 completed grid
regional trials, full-file follow-up status, current21 isolated package and
unchanged25,881,586-byte score. No usable open_in_codex tool is available for
handoff; successful production URL returned normally. Full-grid session73415
is live: manager3819431, worker3819440, native3819895 CPU10, encoding bounded
mode2 at-8; feedbackmode1 queued sequentially. Prior pilot66941 and bounded
pinning controller36166 both terminal (controller exited with its manager).

Two cheap full-corpus floating-grid arithmetic screens also completed. Alternative
pi multiplication/division orders and unit/hour/minute/second decomposition
failed to lower the measured feedback-residual entropy below the incumbent
on either64bit field;32bitfields were unchanged. These are diagnostics only,
not physical compressed results. Keep existing formula and avoid a costly full
trial on this negative screen. Reports:2026-09-29-grid-formula-screen.json and
2026-09-29-grid-units-formula-screen.json. Sources for all current scored21
policies were rechecked again and unchanged after these independent experiments.
Current live process inventory:2026-09-29-local-jobs-0205.json. No whole-file
GOT, pointer, section or stronger PAQ result has completed at this checkpoint;
no projected savings. Research remains authorized and active independently of
pending source-publication/contact approval. No Actions, public source push,
email or source-repository visibility change occurred.


## 2026-09-29 02:40 UTC: portfolio22 widens verified lead

User renewed research for a greater lead. Read controlling attachment and current
process/artifact reality. Full bounded-grid PAQ8 SAO completed02:25:21Z:
2,124,696 bytes; all7,251,944 original bytes restored. Encode732.706s,
decode725.022s; child peak2,489,600KiB. New qualified_grid_paq validates every
recorded source/backend, header length/mode/version/CRC, original and restored
hash, exact complete frame and current structural recomputation/inversion.
competitive_grid_paq_v22 extends actual21 and passed18 guard/selection tests.
Complete qualification session72209terminal:25,846,533 bytes, first equivalent,
35,053 saved;1,978,978 (7.1121%) below live27,825,511 leader. New full page fetch
matched prior SHA. Default CLI is22; unchanged eleven frames retain independent
exact full-decoding proofs. No multi-minute full decode was repeated needlessly.

New five-way whole-SAO correction-predictor test completed session57526:
last-coordinate2158855; modal-coordinate2163395; last+coarsefallback2165140;
modal+coarsefallback2165522; coarsecontextalone2181555. Every frame restores.
None beats currentPAQ2124696. Retain negative result. The895-ish byte control
shift versus earlierBrotli arises in a differently serialized header, not a new
predictor. All dynamic counts depend only on previously decoded corrections.
One shared model ID is paid; codec's initial docstring incorrectly says per-field.

Next physical hypothesis: split corrections into groups computable from decoded
coordinate magnitude/sign/lowbits, then compare raw symbols, paid conditional
multinomial ranks and same-count arithmetic. New grid_conditional_corrections
frameCIXB20 (not a change to any frozen codec). Sixty substream tests include
empty/singleton/1025-length/palette>256 fallback cases;12 complete framed
nonfinite/signed-zero/nongrid/tail cases allrestore. Eight full trials running
session28373, rootresults/leaderboard/grid-conditional-full-20260929, two workers
onCPUs20/22. All palette, count, partition and termination costs are paid.
This is not a score until complete physical restoration and parent integration.

Full feedback-only grid-PAQ8 remains in decode onCPU10, manager3819431,
worker3866054/native3892460 atinspection. Original structural/GOT/pointer and
high-effort PAQ runs remain live and frozen. Source publication/contact still
requires the earlier unanswered decision; this does not block local research.


### Eight full conditional controls complete; positive grouping, negative counts

All8 conditional-correction full frames restore. Context/coding sizes:
0/raw2159821; magnitude/raw2152480; magnitude+lowbits/raw2152532;
exact-coordinate/raw2144044; magnitude/ranks2158459;
magnitude/arithmetic2168964; lowbits/ranks2174106;
lowbits/arithmetic2167100. Exact-coordinate stable grouping saves15777 bytes
against same-wrapper ungrouped control, but none beats selectedPAQ2124696.
Paid counts/ranks do not beat raw grouped data; arithmetic beats ranks on the
finer partition and loses on the coarser one. Uncertainty accounting records
uniform palette cardinality, conditional class cardinality, actual correction
bytes and overhead; transmitted compositions are explicitly charged.
Full reports2026-09-29-grid-conditional-full.json and
2026-09-29-grid-conditional-uncertainty.json.

Started matched context0/context3 nativePAQ-4 controls on the same three disjoint
131068-byte regions, session62357, rootgrid-conditional-paq-regions-20260929,
two workers onCPUs16/18. First two complete pairs improve40705→40568 and
38024→37832, all independent restores. Wait for third pair before full launch;
no partial projection enters score. New wrapperMAGICCIXB21; sources frozen.


### Portfolio23: feedback-only full PAQ beats the bounded representation

Full feedback-onlyPAQ8 completed with2,117,731 bytes and exact restoration,
saving another6,965 versus22 and42,018 since the previous publishedSite21.
The regional preference for bounded ranks did not determine the whole-file
winner; exact physical selection did. competitive_grid_feedback_paq_v23
preserves every22 candidate and addsmode1. Qualification session27937terminal,
allcurrent dependency/input/frame hashes, header identity, structural rerun
and inversepassed. DefaultCLI23. Total25,839,568,firstequivalent,1,985,943
(7.1371%)below freshly rechecked27,825,511 leader. Full proof:
2026-09-29-competitive-grid-feedback-paq-milestone.json. Both measured alternatives
and timing:2026-09-29-grid-backend-full-paq.json. Session73415terminal.

Allsix grouped-PAQ regional streams now complete andrestore. Three matched
improvements40705→40568,38024→37832,43333→43210 (137/192/123 saved).
Full groupedPAQ8 session53530 launched, manager3914276,worker3914285,
native3914914. Afterfeedback completed, movedallthree fromEcore16 tofreePcore10
without restart orsource changes. Encodingtiming spans placements; no uniform
speedclaim. Proof2026-09-29-grouped-grid-core-reassignment.json. Root
results/leaderboard/grid-conditional-paq-full8-20260929. No projectedsize.

Broadened the next bounded screen to pristinePAQ text models: nativev215 flags
-4,-4A,-4L,-4LA on three disjoint131072-byte Dickens regions, one workerCPU22,
session32410. Upstreamsrc/paq8px.cpp explicitly definesA as adaptive CM-mixer
learning rate andL as addinganLSTM expert. No external dictionary,pretraining
snapshot or source changes. Every physicalarchive is extracted andcompared.
Reportrootresults/leaderboard/paq-text-adaptation-regions-20260929. Existingfull
higher-effort reference/structural research continues independently.

A portfolio22 source-only bundle also passedisolated uncachedCLI smoke before23
completed. Archive3156113bytesSHA256
790263c1bc0a123615bd88b3fa9848a36ee7191301241b28f8d14c2791322c02.
It is preserved asprevious evidence,not relabelledcurrent23. Source23 packaging
andSiteupdate follow. NativeGOTprospective22 still extends21: neverqualify against
current23 with thatwrapper. Createa parent-aligned successor whenproof completes.


### Published research checkpoint 03:01 UTC

Site publication SUCCEEDED2026-09-29T03:01:14.735605Z. Exactsource
4c69cdc2ebee38351c861966a10be764a3410814, deployment
appgdep_6abb29e86e708191a603a55401cfc436, version
appgprj_6aba005773a08191ae8a7978a687b3cb~appgver_367472f0a1c881919b5e6c77baa229c9.
Nine-family/four-column table, all12 members andscorecards consistently show
25,839,568 bytes,12.19%original,7.14% below published leader. Complete grid
controls,13 new full correction trials,6 matched PAQ regionals,uncertainty
accounting andcurrent23 source smoke are linked. Current source-only archive
3157035bytes,1491sourcefiles,SHA256
30d82fb95e952358a28d6695624cf6e014be546f664eeb0ecc69fcbed3a4419d;
1076native source/provenance files unchanged from22,seven prior qualifiednative
binaries reused aftermatching,andfreshuncachedsmallCLI encode/decode passed.
No current fullarchive decode was repeated within the smoke. No corpus,
benchmarkstreams,binaries orworkflows in sourcearchive. It remainsprivate.

Score23 frozen sources checkedagain at03:01UTC. Full grouped correctionPAQ
session53530 remainsrunning onCPU10; twelve text-adaptation controls session32410
run sequentiallyCPU22. First ordinary/adaptive-CM pair32352/32363B bothrestore;
thispartialpair isnot a cohortconclusion andnot ontheSite asan improvement.
DiscountedjointMozilla hasprogressed fromencode todecode, native3899792CPU0.
Otherstructural andhigher-effort referenceworkers remainlive; currentjobproof
2026-09-29-local-jobs-0300.json. No wholeGOT/pointer/section/strongerPAQ result
hascompleted inthischeckpoint. Preserve their sources and original streams.

Current public-source/contact question remainsunanswered; no newquestion, source
GitHubpush,visibilitychange ormaintainer message. Localresearch remains explicitly
authorized separately. NoActions. Goaltool stillreports oldofficial-listinggoal
blocked; no unsupportedresume orfalsecompletion was attempted. Furtherresearch
canproceed withavailablelocal evidence independently ofthat publication decision.


### 2026-09-29: portfolio24 and renewed larger-gain research

User explicitly renewed research: harder, better, very significant savings.
Four complete independent experiments qualified against actual portfolio23:
GOT+PAQ8 Mozilla5917452; pointer feedback+PAQ8 Mozilla5857527;
coordinate-grouped PAQ8 SAO2105875; nativev215 -9L Webster4423086.
Exact physical selection chooses pointer, grouped andLSTM, saving314427bytes.
Total25525141, twelvefull restored members, firstequivalent,2300370bytes
(8.2671%) below freshlyfetched published27825511. Source/backend/input/frame
identities checked, structural representations recomputed/inverted. Unchanged
nineframes preserve their original complete extraction proofs. No projected
archive was scored. Default competitive_cli now uses parent-aligned24. New
qualifier/header/routing/physicalselection tests plus existing guards:25passed.
Report2026-09-29-competitive-prediction-v24-milestone.json.

Twelve text-adaptation regionals allcomplete andrestore: LSTM saves95/113/111
bytes onthree disjointDickens regions; adaptiveCM learning loses6–11 versus
correspondingcontrols. Full nativev215 -9L Dickens thenReymont launchedCPU8,
session96400, rootpaq-v215-text9L-20260929. PointerresidualLSTM threecohort
followupCPU10, session18252, rootecoff-pointer-lstm-regions-20260929. Existing
Webster12L, Mozilla9L, sectionpointer anddiscountedjointdecodes preserved.

New opportunity: causalcopy-and-correctfunctiontemplates. An initial same-name
screenfound521104 repeatedfunctionbytes and289152bytes withless25% changed
words. Newecoff_function_templates expandsmatchingto opcode signatures across
allpdata-delimitedfunctions, retainingfourpreviouscandidates. Referenceindices,
selectionmetadata andallXOR/subtractioncorrections aretransmitted; decoderuses
onlypreviouslyrestoredfunctions. Sixinvariant/adversarialtests passed. Full
Brotli controls(plainparent/XOR/subtraction) launchedCPU14, session47615,
rootecoff-function-templates-brotli-full-20260929. This isunscoredresearch.
Publicsource/contact decisionremainspending; localresearchandprivateSitesupdates
authorizedindependently. NoActionsorpublicsourcepush.


Section/function alphabet fullPAQ8 completed5834880 bytes, allMozilla restored.
Parent-alignedportfolio25 now25502494, another22647saved,337074sinceSite23.
Publishedleader27825511 unchanged;lead2323017(8.3485%). Currentdefault25.
CompleteBrotlitemplates: control12881372;XOR12882441;subtraction12803097.
Allthreewholeframesrestore;subtraction saves78275 againstsamecontrol butdoesnot
beatselectedPAQ. NewmatchedPAQregionaltestsession72112CPU14, modes0and2.
Templatecoverage5170896rawbytes;226789changedwords. No projectedPAQgains.

Secondnewbranch: actualPAQ pathinventoryclassifiesXrayasdefault, withoutimage
models. paq_image_planes reversiblytransmits16bitpixelsastwo8bitPGMgrayscale
imageswithsplit4/6/8, plusalloriginalmetadataanddimensions. Native-0pathlog
confirms two8b-img-grayscale segments,width2230,142720byteseach forfirstcrop.
Twelve regional -4trialsrunningCPU2 session17955;36initialrawtransformroundtrips
pass,14 additional automatededge/overflowtests pass. Initialcrop results120042
controland119890split4bothrestore;notageneralorwhole-fileclaim.

Isolatedsource24 bundle1497files,3161368bytesSHA256
 d3dae6e35637d30c1ca6e4f190489c9d15132282fc9175ac9e20eb0661e2c7d0
passedfreshsmalluncachedCLIroundtripwithseven previouslyqualifiednativebinaries.
Preservedasprevioussourceproof;current25packaging follows.
