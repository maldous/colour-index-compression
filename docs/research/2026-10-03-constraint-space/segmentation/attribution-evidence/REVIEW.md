# Independent attribution evidence review — 2026-10-03

Read-only review of `REPORT.md`, `results.json`, `freeze.json`,
`input-freeze.json`, raw receipts, the earlier mask results, and the
support-evidence closure. No codec, build, or archive operation was run.

## Verdict

**PASS — no blocker found.** The attribution report is consistent with its
physical archive and accounting evidence, and the support closure has the
limited applicability stated below.

## New-cell and restoration audit

The stated 59 new complete ZSC1v2 cells reconcile as:

| Component | Cells |
|---|---:|
| fixed literal BSS widths 2–8, seven fixtures | 49 |
| literal at the native-inferred non-unit width | 5 |
| all-residual at that same non-unit width | 5 |
| **total** | **59** |

The two fixtures whose inferred width is one reuse their literal/all-residual
identity archive. The selected-mask Zstd arm also reuses the pre-existing
matching archive for every fixture. It is therefore correctly excluded from
the new-cell count.

All 59 new archive paths under
`benchmark-work/segmentation-attribution/archives/` exist and their on-disk
SHA-256 values equal `results.json`. Every one records a successful fresh
restore whose SHA-256 equals the fixture input SHA-256. In each case the
stored complete byte count equals the stored metadata plus payload count.

The seven reused native/matched records remain separately labelled reused.
The support diagnostic's twelve recorded hashes each match the corresponding
existing native-mask archive hash; all twelve reconcile as
`17 header + 9 per lane + opaque payload`, and all are marked
`new_archive: false`.

## Attribution checks

The report's table matches `results.json`, including the retained negatives:

* For fresh widths 3/4/5, literal BSS at the native width is
  `1053/1172/1244`, all-residual is `1051/826/692`, selected residual is
  `597/484/416`, and native is `710/640/622` bytes.
* Literal BSS changes versus original Zstd are `+53/-78/-231` bytes; this
  preserves the fact that byte separation alone loses at widths 4 and 5.
* All-residual improvements are `2/346/552` bytes, and selective residual
  improvements over all-residual are `454/342/276` bytes. These are matched,
  sequential differences and are not presented as universal additive gains.
* The report's native-to-same-layout-Zstd differences reconcile exactly:
  `113/156/206 = (90/124/165 payload) + (23/32/41 outer framing/metadata)`.
  The native accounting is `17 + 9w + payload`; ZSC is `21 + payload`.
  This supports the explicit backend/framing attribution and does not give
  native modelling credit for either component.
* A–B–A and absent-structure rows retain their counterexamples. In particular,
  the best fixed width-2 BSS A–B–A archive is 774 B while the inferred native
  geometry is width 1, and every Zstd mapping on the absent case is 1522 B.

The attribution rows retain the already exposed inputs from the earlier
evidence chain, including the three `fresh-held-mask` fixtures. The input
paths and fixture hashes are inherited and recorded; this is an attribution
matrix, not a new-held-out generation or replication claim.

## Support-closure scope

The twelve-archive inspection establishes a narrow fact about the **current
lane-mask format**: source length, stride, mask, positions and counts are
already either paid once globally or derived from that paid global state; the
inspection did not find a repeated transmitted support object. It therefore
supports closing the proposed shared-support experiment at its applicability
gate. It does **not** prove that no future format, altered coder payload, or
new model-sharing representation could create a shareable object or a saving.
The report makes this distinction and does not claim a mathematical
impossibility result.

## Lance wording

The associated prior-art note should remain scoped to the reviewed material:
the inspected Lance statistics source exposes a byte-position entropy
suitability signal, while the reviewed encoding-configuration issue describes
automatic table-statistics selection/compaction as a proposed later step. That
supports “not established by the reviewed primary materials,” not a global
claim that no Lance version, branch, or future implementation can perform
automatic BSS selection.
