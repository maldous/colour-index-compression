# Final evidence review — 2026-10-03

Independent read-only review of `CHECKPOINT.md`, the five named reports,
their `results.json`/raw receipts, and the mask supplement. No codecs were
built or run, and no archive was regenerated.

## Result

**PASS — no evidence blocker found.** The checkpoint is suitably bounded and
its claims match the inspected evidence.

## Reconciled counts

| Evidence group | New complete archives | Malformed/CLI rejections |
|---|---:|---:|
| position descriptions | 49 | 9 |
| adaptive segmentation | 204 | 9 |
| decoded-prefix history | 116 | 8 |
| lanes v1 | 103 | 14 |
| lane masks v2 | 63 | 17 |
| **main total** | **535** | **57** |
| contiguous-control supplement | **12** | — |

Thus `535 = 49 + 204 + 116 + 103 + 63`, separately from the twelve
freshly encoded contiguous controls. The reported 44 v1 compatibility
restores are separate from the new-archive total, as are the sixteen
altered-history probes (13 history-dependent payload rejections and three
valid H0-compatible restores).

## Result and attribution checks

* The fresh mask rows in `mask-evidence/results.json` match the report:
  width 3 `710 / 597 / 911`, width 4 `640 / 484 / 772`, width 5
  `622 / 416 / 691` for native mask / same-mask Zstd / CIX BEST. Their
  stored restored SHA-256 values equal the fixture hashes.
* The supplemental physical archives are under
  `benchmark-work/mask-contiguous-controls/archives/`, distinct from the
  mask archives under `benchmark-work/segmentation-masks/archives/`.
  This supports the statement that the 12 controls were encoded separately.
* The six fresh mask archives (native and Zstd for widths 3–5) exist at the
  stored paths and their on-disk SHA-256 values match `results.json`.
* The reports consistently give Zstd the stronger same-representation result
  and attribute its additional size gain to the established backend. They do
  not describe this as a native-coder victory or a new theory.
* The reports expressly limit the inputs to a bounded synthetic family and
  deny claims of unseen real-data generalisation, streaming, incremental
  decoding, production integration, or arbitrary-length behaviour.

## Freeze and production checks

`failed-v1-freeze.json`, the preserved failed source/schedule/stderr, and
`freeze.json` consistently record the compile-only ZSC failure before input
generation. The correction is the typed inverse offset as `usize`; the final
freeze identifies a new build experiment and records reuse only of the
unchanged successful native-mask binary. The reports do not count a failed
compile as an archive cell or present it as a rerun.

`git diff --quiet d3a2cd416e49f93403d1dbd348a3e9a45db66ec6 -- cix rust/cix-native/src`
returned success in the inspected worktree. The experimental sources are kept
under `rust/cix-native/experiments/`; this supports the reports' statement
that the production paths stayed unchanged.

## Scope note

The review did not treat reused v1 archive references as v2 mask metrics.
This agrees with the v2 report's explicit basename-collision exclusion and
with the separate physical paths verified above. Existing unrelated dirty and
untracked workspace material was left untouched.
