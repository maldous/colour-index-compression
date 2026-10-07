# CIX screening representation benefits — one-off matched-control audit

All six inputs are 16,384-byte screening slices, not full datasets. Previously held-out ranges are now exposed.

All forced representation trials used maximum effort: 65,536-byte blocks, no retained history, 4 s route wall budget, 512 MiB worker address-space cap. Current balanced and speed fast have no paired forced-route evaluations.

Legacy outer caps: 300 s, 2,000,000,000 B RSS, 250,000,000 B temporary. New extension: 60 s, same RSS, 100,000,000 B temporary. Different caps are not treated as matched, even if neither trial exhausted them.

One pinned physical core per process; equivalent lanes 16–19, aggregate four cores / 12 GB / 4 GB. Lane and thermal/cache differences plus one repetition make time deltas observations, not statistically verified speed claims.

CIX-only backend means per-stream raw/run/exact-rank portfolio with the same entropy gate, not every stream necessarily rank-coded. DEFLATE backend similarly retains raw/run alternatives. Hybrid adds both portfolios. Composition ignores requested hybrid backend and calls streams(original,cix); deflate forces streams(original,deflate).

Complete bytes include 13-byte file header, 41-byte block frame, 41-byte end frame, transforms, dictionaries, counts, descriptors, all payload and checksums. Accounting fields sum to archive bytes minus 54; framing_bytes includes the block frame.

TIE anchors compare an unchanged-input archive with itself and do not constitute independent experiments or representation benefits. NOT MEASURED also means comparison unavailable despite a verified candidate archive; reason and complete size are retained.

Peak RSS records the timed parent process and is not aggregate worker-tree peak. Cgroup sampled high-water is a lower bound. Incremental decoder/program packaging is not included in these archive-only comparisons; no full-submission claim.

PAQ v216 -8 vs transformed CIX uses a different backend; those pipeline comparisons cannot isolate representation gain. Six PAQ -12L/five-layer rows are memory exclusions, not failed runs. No other memory-excluded representation trial is recorded in these screening files.

Negative changes mean smaller complete archives. No missing delta is imputed as zero. Percent denominator is the matched compressed baseline, not original input size.

## Current / balanced — 6 × 11 supported-comparison matrix

| Slice | Raw storage | Run-only | Direct CIX composition | LZ separated streams | Causal prediction residuals | BWT → MTF → runs | Delta/XOR + byte planes | Input-derived phrase dictionary | Contextual PPM | Fixed-point predictor mixture | Original bytes → DEFLATE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MSG numerical data (`fcbench-msg`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| MHD simulation (`fcbench-mhd`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| GitHub events · prefix (`golf`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| PT simulation · held-out range (`fcbench-pt-heldout`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| RSim · near-constant held-out range (`fcbench-rsim-heldout`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| GitHub events · held-out range (`golf-heldout`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |

## Speed / fast — 6 × 11 supported-comparison matrix

| Slice | Raw storage | Run-only | Direct CIX composition | LZ separated streams | Causal prediction residuals | BWT → MTF → runs | Delta/XOR + byte planes | Input-derived phrase dictionary | Contextual PPM | Fixed-point predictor mixture | Original bytes → DEFLATE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MSG numerical data (`fcbench-msg`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| MHD simulation (`fcbench-mhd`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| GitHub events · prefix (`golf`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| PT simulation · held-out range (`fcbench-pt-heldout`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| RSim · near-constant held-out range (`fcbench-rsim-heldout`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |
| GitHub events · held-out range (`golf-heldout`) | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED | — B / — % · NOT MEASURED |

## Size / maximum — 6 × 11 supported-comparison matrix

| Slice | Raw storage | Run-only | Direct CIX composition | LZ separated streams | Causal prediction residuals | BWT → MTF → runs | Delta/XOR + byte planes | Input-derived phrase dictionary | Contextual PPM | Fixed-point predictor mixture | Original bytes → DEFLATE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MSG numerical data (`fcbench-msg`) | +0 B (+0.00%) · TIE · raw | +14,786 B (+89.73%) · LOSS · raw | +0 B (+0.00%) · TIE · cix | -381 B (-2.45%) · WIN · cix | +965 B (+6.22%) · LOSS · cix | +272 B (+1.75%) · LOSS · cix | -1,591 B (-10.25%) · WIN · cix | — B / — % · NOT MEASURED; archive 12,746 B | +0 B (+0.00%) · TIE · ppm | — B / — % · UNQUALIFIED | +0 B (+0.00%) · TIE · deflate |
| MHD simulation (`fcbench-mhd`) | +0 B (+0.00%) · TIE · raw | -3,260 B (-19.78%) · WIN · raw | +0 B (+0.00%) · TIE · cix | -2,758 B (-84.65%) · WIN · cix | -850 B (-26.09%) · WIN · cix | -2,663 B (-81.74%) · WIN · cix | -1,790 B (-54.94%) · WIN · cix | — B / — % · NOT MEASURED; archive 584 B | +0 B (+0.00%) · TIE · ppm | — B / — % · UNQUALIFIED | +0 B (+0.00%) · TIE · deflate |
| GitHub events · prefix (`golf`) | +0 B (+0.00%) · TIE · raw | +15,276 B (+92.70%) · LOSS · raw | +0 B (+0.00%) · TIE · cix | -8,263 B (-73.07%) · WIN · cix | -3,945 B (-34.89%) · WIN · cix | -8,143 B (-72.01%) · WIN · cix | +1,852 B (+16.38%) · LOSS · cix | — B / — % · NOT MEASURED; archive 3,849 B | +0 B (+0.00%) · TIE · ppm | — B / — % · UNQUALIFIED | +0 B (+0.00%) · TIE · deflate |
| PT simulation · held-out range (`fcbench-pt-heldout`) | +0 B (+0.00%) · TIE · raw | +16,260 B (+98.67%) · LOSS · raw | +0 B (+0.00%) · TIE · cix | — B / — % · NOT MEASURED; archive 15,795 B | — B / — % · NOT MEASURED; archive 16,443 B | — B / — % · NOT MEASURED; archive 16,428 B | — B / — % · NOT MEASURED; archive 12,749 B | — B / — % · NOT MEASURED; archive 14,629 B | +0 B (+0.00%) · TIE · ppm | — B / — % · UNQUALIFIED | +0 B (+0.00%) · TIE · deflate |
| RSim · near-constant held-out range (`fcbench-rsim-heldout`) | +0 B (+0.00%) · TIE · raw | -16,376 B (-99.37%) · WIN · raw | +0 B (+0.00%) · TIE · cix | — B / — % · NOT MEASURED; archive 147 B | — B / — % · NOT MEASURED; archive 117 B | — B / — % · NOT MEASURED; archive 137 B | — B / — % · NOT MEASURED; archive 116 B | — B / — % · NOT MEASURED; archive 139 B | +0 B (+0.00%) · TIE · ppm | — B / — % · UNQUALIFIED | +0 B (+0.00%) · TIE · deflate |
| GitHub events · held-out range (`golf-heldout`) | +0 B (+0.00%) · TIE · raw | +15,584 B (+94.57%) · LOSS · raw | +0 B (+0.00%) · TIE · cix | — B / — % · NOT MEASURED; archive 2,932 B | — B / — % · NOT MEASURED; archive 5,318 B | — B / — % · NOT MEASURED; archive 2,931 B | — B / — % · NOT MEASURED; archive 7,150 B | — B / — % · NOT MEASURED; archive 3,812 B | +0 B (+0.00%) · TIE · ppm | — B / — % · UNQUALIFIED | +0 B (+0.00%) · TIE · deflate |

## Verified matched representation benefits and observed timing

| Slice | Representation / backend | Control → complete B | Change B / % | Encode s (control → candidate) | Decode s | Observed tradeoff |
|---|---|---|---|---|---|---|
| fcbench-msg | LZ separated streams / cix | 15,524 → 15,143 | -381 / -2.454% | 0.19 → 0.23 | 0.26 → 0.25 | size/speed trade-off |
| fcbench-msg | Delta/XOR + byte planes / cix | 15,524 → 13,933 | -1,591 / -10.249% | 0.19 → 0.13 | 0.26 → 0.08 | size + observed speed |
| fcbench-mhd | Run-only / raw | 16,479 → 13,219 | -3,260 / -19.783% | 0.10 → 0.11 | 0.06 → 0.07 | size/speed trade-off |
| fcbench-mhd | LZ separated streams / cix | 3,258 → 500 | -2,758 / -84.653% | 0.13 → 0.13 | 0.11 → 0.07 | size + observed speed |
| fcbench-mhd | Causal prediction residuals / cix | 3,258 → 2,408 | -850 / -26.090% | 0.13 → 0.15 | 0.11 → 0.13 | size/speed trade-off |
| fcbench-mhd | BWT → MTF → runs / cix | 3,258 → 595 | -2,663 / -81.737% | 0.13 → 0.20 | 0.11 → 0.07 | size/speed trade-off |
| fcbench-mhd | Delta/XOR + byte planes / cix | 3,258 → 1,468 | -1,790 / -54.942% | 0.13 → 0.14 | 0.11 → 0.07 | size/speed trade-off |
| golf | LZ separated streams / cix | 11,308 → 3,045 | -8,263 / -73.072% | 0.16 → 0.14 | 0.15 → 0.10 | size + observed speed |
| golf | Causal prediction residuals / cix | 11,308 → 7,363 | -3,945 / -34.887% | 0.16 → 0.18 | 0.15 → 0.15 | size/speed trade-off |
| golf | BWT → MTF → runs / cix | 11,308 → 3,165 | -8,143 / -72.011% | 0.16 → 0.20 | 0.15 → 0.11 | size/speed trade-off |
| fcbench-rsim-heldout | Run-only / raw | 16,479 → 103 | -16,376 / -99.375% | 0.10 → 0.10 | 0.06 → 0.06 | size; observed times tie |

## One summary per slice

### fcbench-msg — MSG numerical data

Verified gains: LZ separated streams / cix, Delta/XOR + byte planes / cix.

Strongest matched benefit: Delta/XOR + byte planes / cix, 15,524 → 13,933 B (-1,591 B, -10.249%). Encode 0.19 → 0.13 s (-0.06); decode 0.26 → 0.08 s (-0.18).

- Current / balanced selected 12,746 B, phrases, encode/decode 0.49/0.06 s; n=1.
- Speed / fast selected 14,832 B, deflate, encode/decode 0.23/0.05 s; n=3.
- Size / maximum selected 12,746 B, phrases, encode/decode 5.35/0.07 s; n=3.

The CIX-only stride gain loses to the 12,746 B hybrid phrase archive. Separately, a matched CURRENT selector ablation proves phrases improve its overall selection by 328 B (13,074 → 12,746), although the missing original hybrid control prevents isolating the phrase transform itself. All other CURRENT route ablations tie. Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.

### fcbench-mhd — MHD simulation

Verified gains: Run-only / raw, LZ separated streams / cix, Causal prediction residuals / cix, BWT → MTF → runs / cix, Delta/XOR + byte planes / cix.

Strongest matched benefit: LZ separated streams / cix, 3,258 → 500 B (-2,758 B, -84.653%). Encode 0.13 → 0.13 s (+0.00); decode 0.11 → 0.07 s (-0.04).

- Current / balanced selected 500 B, lz, encode/decode 0.34/0.07 s; n=1.
- Speed / fast selected 500 B, lz, encode/decode 0.13/0.07 s; n=3.
- Size / maximum selected 500 B, lz, encode/decode 4.49/0.08 s; n=3.

LZ / CIX reaches the selected 500 B. A CURRENT matched selector ablation proves its incremental overall benefit is 42 B (without LZ 542 → 500), not the entire 2,758 B saving against composition. Other CURRENT ablations tie. Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.

### golf — GitHub events · prefix

Verified gains: LZ separated streams / cix, Causal prediction residuals / cix, BWT → MTF → runs / cix.

Strongest matched benefit: LZ separated streams / cix, 11,308 → 3,045 B (-8,263 B, -73.072%). Encode 0.16 → 0.14 s (-0.02); decode 0.15 → 0.10 s (-0.05).

- Current / balanced selected 2,853 B, deflate, encode/decode 0.45/0.06 s; n=1.
- Speed / fast selected 2,853 B, deflate, encode/decode 0.20/0.07 s; n=3.
- Size / maximum selected 2,853 B, deflate, encode/decode 4.64/0.07 s; n=3.

Original-byte DEFLATE at 2,853 B remains smaller than the strongest supported transformed CIX archive (LZ 3,045 B). None of the transformed route CURRENT ablations improves selection; removing original-byte DEFLATE costs 136 B (2,989 → 2,853). Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.

### fcbench-pt-heldout — PT simulation · held-out range

Verified gains: None established against a matching unchanged-input control.

Strongest isolated representation benefit / baseline / timing changes: unavailable. No matching positive comparison exists.

- Current / balanced selected 12,749 B, stride, encode/decode 0.37/0.06 s; n=1.
- Speed / fast selected 12,749 B, stride, encode/decode 0.17/0.07 s; n=3.
- Size / maximum selected 12,749 B, stride, encode/decode 5.08/0.06 s; n=3.

The verified 12,749 B hybrid stride archive is selected in all three profiles. Unchanged-input hybrid control is missing, so a representation-only delta and time change cannot be attributed. No held-out route ablation establishes an incremental selector contribution. Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.

### fcbench-rsim-heldout — RSim · near-constant held-out range

Verified gains: Run-only / raw.

Strongest matched benefit: Run-only / raw, 16,479 → 103 B (-16,376 B, -99.375%). Encode 0.10 → 0.10 s (+0.00); decode 0.06 → 0.06 s (+0.00).

- Current / balanced selected 103 B, runs, encode/decode 0.30/0.06 s; n=1.
- Speed / fast selected 103 B, runs, encode/decode 0.14/0.06 s; n=3.
- Size / maximum selected 103 B, runs, encode/decode 4.41/0.06 s; n=3.

Run-only / raw reaches the 103 B selected archive. It is 10 B smaller than the measured 113 B composition and original-DEFLATE anchors, but there is no matching CURRENT/FAST/SIZE selector-removal ablation on this range. The slice is 16,383 zero bytes and one byte 64; do not generalise to entire RSim. Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.

### golf-heldout — GitHub events · held-out range

Verified gains: None established against a matching unchanged-input control.

Strongest isolated representation benefit / baseline / timing changes: unavailable. No matching positive comparison exists.

- Current / balanced selected 2,770 B, deflate, encode/decode 0.44/0.06 s; n=1.
- Speed / fast selected 2,770 B, deflate, encode/decode 0.19/0.07 s; n=3.
- Size / maximum selected 2,770 B, deflate, encode/decode 4.65/0.07 s; n=3.

Original-byte DEFLATE is best at 2,770 B and is selected in all profiles. No matching transformed CIX/hybrid control is available; its transformed archives do not establish an attributable gain. No selector-removal ablation is available. Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.

## Unqualified and memory-excluded

Six fixed-point mixture trials exceeded 4 s route budgets and failed restoration. Their 13 B partial headers have no qualified size, percentage, rank or useful decode timing. All remain UNQUALIFIED.

PAQ maximum v216 -12L with five LSTM layers was not launched on any slice: approximately 29 GB plus LSTM state exceeds the aggregate 12 GB cap. These six RESOURCE_LIMIT exclusions remain outside representation rankings. Huffman and ANS/FSE are unimplemented, not memory exclusions.

## Final findings

1. Multiple-slice benefits: Run-only: fcbench-mhd, fcbench-rsim-heldout; LZ separated streams: fcbench-msg, fcbench-mhd, golf; Causal prediction residuals: fcbench-mhd, golf; BWT → MTF → runs: fcbench-mhd, golf; Delta/XOR + byte planes: fcbench-msg, fcbench-mhd.
2. Particular-slice limitations: Run-only wins on MHD and near-constant RSim, but loses on MSG, PT and both Golf ranges. CIX-only predictor/BWT win on MHD and Golf, lose on MSG; CIX-only planes win on MSG/MHD, lose on Golf. LZ wins on all three tested CIX-controlled development slices. No representation has a demonstrated win on exactly one slice.
3. No demonstrated benefit: Phrase dictionary: finished archives but no matching original hybrid control. Raw, composition, PPM and original-byte DEFLATE are unchanged-input anchors, not transformation gains. Mixer: six unqualified trials. This is not proof of absence of benefit.
4. Unresolved targeted follow-up: Need targeted unchanged-input hybrid and count-range controls; legacy DEFLATE control with identical 300 s / 250 MB caps; controlled forced routes under balanced and fast; transformed CIX trials on exposed held-out ranges; affordable mixer configuration and larger unexposed inputs. No new trials were run for this report.

## Reproduction and references

Run `python benchmarks/screening_representation_audit.py` from the private repository. It invokes no compressor or decoder; it recalculates matrices and rechecks retained physical artifacts, exact decoded bytes, SHA-256, full accounting, source/configuration identities and resource matches.

- [docs/research/2026-09-30-generic-pipeline/results.json](../2026-09-30-generic-pipeline/results.json), SHA-256 `8a0ce4d539c2720e4de5b958a3a50724115131bcb0dc48cd7e95ba2dc0c1aa97`.
- [docs/research/2026-09-30-representation-coverage/results.json](../2026-09-30-representation-coverage/results.json), SHA-256 `8c4dc57204b84158bcad562a2d452b6d0cb4014827b6b0f5d2461aa3e5941b2f`.
- [docs/research/2026-09-30-codec-profiles/results.json](../2026-09-30-codec-profiles/results.json), SHA-256 `284e1420db92fbd55d35c5a730a1c9bdd6c6bf51799cd3010ed67e738e2c2fe5`.

`matrix.json` carries both cell identities, raw commands, source hashes, budgets, accounting, independent-decode receipts and every observed candidate size. `backend-matrices.csv` enumerates all 3 × 7 × 6 × 11 backend cells. `matrix.csv` enumerates the 3 × 6 × 11 supported-comparison cells. No broad sweep or targeted experiment was launched.
