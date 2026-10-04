# Silesia specialised-restoration regression baseline

## Status and purpose

This is a read-only baseline and scope ledger for the approved one-pass specialised restoration.  It does **not** report a new CIX result.  The historical portfolio result is a regression target only; a result may be called current only after the integrated runtime produces fresh complete archives and an independent archive-only decoder restores them.

The canonical local Silesia input set contains 12 members and 211,938,580 bytes.  Its member names, byte counts, and SHA-256 values are pinned in [`silesia-plan.json`](../../2026-10-01-rust-native/silesia-plan.json) and reproduced in the machine-readable companion.  The plan names local files for the test harness; production admission must never use names, paths, hashes, corpus identity, or retained archives.

## Historical complete-archive target

The retained `portfolio26` receipt is [`results/leaderboard/competitive-joint-discount-v26/complete.json`](../../../../results/leaderboard/competitive-joint-discount-v26/complete.json), SHA-256 `9f1f30482d89bebd303c4017fcee6e6bc2a87c2b4fcd543b1fac39476d3d5fc7`.  Its policy is **CIX competitive joint-discount and section-constrained portfolio 26**.  The receipt is an approximately 8 MB nested research artifact; this ledger intentionally uses only the shallow, already-extracted certificate fields in [`historical-baseline.json`](historical-baseline.json), rather than parsing its nested trial/cache history.

| Member | Input bytes | Historical complete bytes | Selected historical setting | Certificate |
|---|---:|---:|---|---|
| dickens | 10,192,446 | 1,902,345 | `paq-v216-8-under-12MiB-nondatabase` | input/frame/restored SHA-256; round trip |
| mozilla | 51,220,480 | 5,814,277 | `joint-discount-paq-v215-8-mode2` | input/frame/restored SHA-256; round trip |
| mr | 9,970,564 | 1,671,101 | `volume-0-3-10` | input/frame/restored SHA-256; round trip |
| nci | 33,553,445 | 447,748 | `geometry-hydrogen-slots-paq-v215-8` | input/frame/restored SHA-256; round trip |
| ooffice | 6,152,192 | 1,267,529 | `paq-v216-8-under-12MiB-nondatabase` | input/frame/restored SHA-256; round trip |
| osdb | 10,085,684 | 1,698,992 | `database-remaining-count-paq-v215-8` | input/frame/restored SHA-256; round trip |
| reymont | 6,627,202 | 746,894 | `paq-v216-8-under-12MiB-nondatabase` | input/frame/restored SHA-256; round trip |
| samba | 21,606,400 | 1,625,132 | `paq-v216-8-12to24MiB-nondatabase` | input/frame/restored SHA-256; round trip |
| sao | 7,251,944 | 2,105,875 | `grouped-prediction-paq-v215-8` | input/frame/restored SHA-256; round trip |
| webster | 41,458,703 | 4,423,086 | `lstm-prediction-paq-v215-9L` | input/frame/restored SHA-256; round trip |
| x-ray | 8,474,240 | 3,531,428 | `paq-v216-8-under-12MiB-nondatabase` | input/frame/restored SHA-256; round trip |
| xml | 5,345,280 | 247,484 | `paq-v216-8-under-12MiB-nondatabase` | input/frame/restored SHA-256; round trip |
| **Total** | **211,938,580** | **25,481,891** | per-member complete-archive portfolio | all 12 certified |

The accompanying JSON carries the exact input, frame, and restoration SHA-256 certificates for every row.  It makes no claim that the historical streams are admissible for a fresh run.

### Historical source map

The historical portfolio dispatcher was [`benchmarks/competitive_joint_discount_v26.py`](../../../../benchmarks/competitive_joint_discount_v26.py).  This is traceability for restoration, not a proposal to ship the benchmark harness.  Its winner-family implementations were: `competitive_small_paq.py` (the under-12 MiB PAQ selections), `competitive_medium_paq.py` (the 12–24 MiB PAQ selection), `competitive_joint_discount_v26.py` plus its PAQ joint builder (Mozilla), `volume_image_codec.py` (mr), `competitive_hydrogen.py` and `sdf_hydrogen.py` (nci), `competitive_fixed_database.py`/`competitive_database_portfolio.py` (osdb), `competitive_grid_paq_v22.py` and `competitive_grid_feedback_paq_v23.py` (sao), and `competitive_prediction_v24.py` (Webster).  The exact historical selected setting and input/frame/restoration certificate remains the per-row record above and in JSON.

## Scope ledger

| Evidence class | What it establishes | What it does not establish | Release consequence |
|---|---|---|---|
| Portfolio26 historical winners | Format-aware paths were once complete, decodable, and materially useful on the listed canonical inputs. | Current source compatibility, fresh selected sizes, or a current total. | Account for every winner family before freezing the integrated runtime. |
| Previous generic-only closure | Its tested generic routes and closed numeric/predictive branches retain their documented negative scope. | Rejection of semantic/format-aware selection: parser and specialised backend routing were policy-excluded. | Do not describe generic closure as exhaustion of specialised restoration. |
| Domain-transfer positives | Complete-archive PAQ-backed specialised encodings beat the matching PAQ control on two PubChem 2D panels (163 and 74 bytes) and two NOAA assets (216 and 948 bytes). | General improvement, a Silesia prediction, or a reason to select by filename. | Preserve content-validated chemical and numeric/grid candidates for automatic admission. |
| Domain-transfer negatives/trade-offs | The tested 3D chemistry, Adult, ELF packing, NIfTI neighbour-slice, mixed NOAA radial, and some ID-packing routes did not beat their stated controls; JXL NIfTI traded size for lower time/memory. | Failure of every validated representation of those domains. | Retain as scoped controls; do not promote them merely from the positives. |
| Native CIX screening | On Dickens only, the former Rust trial independently verified CIXG1 fast/current/size archives, then CIXM6 current/size hit the 300-second command budget and the other 66 cells were not run. | A full current native Silesia number or a specialised successor. | Do not infer a current aggregate from the partial screen. |

The formal reconciliation is [`scope-reconciliation.json`](scope-reconciliation.json); domain-transfer figures and scope are in [`FINDINGS.md`](../../2026-09-30-domain-transfer/FINDINGS.md).  These records require automatic recognition from supplied bytes and bounded resource policies, followed by complete physical archive comparison.  They do not authorize corpus lookup or saved-stream reuse.

## Available current identities, without a fabricated aggregate

* The stopped native screening was frozen at native commit `3a3b9885f8ca64e1170a9546df0d471e1b67455a`, with input-manifest SHA-256 `d808f6d65ca1172aa6c1bea3af1e3e9d38a1fc985e549e3ba1bd4668540ee4b8`; see [`environment.json`](../../2026-10-01-rust-native/silesia-rust-native-v2/environment.json).  It yielded no complete 12-member total.
* The frozen generic-only 0.1 candidate binary is `cix` SHA-256 `09434a7f34b62691d0e187a22bd1b77fbb48a4b7f3f7d3ceea3857ca4e8b16a2`, recorded by [`release-binary-freeze-final.json`](../2026-10-04-release-0.1/release-binary-freeze-final.json).  It predates the accepted specialised-restoration scope and is therefore not the claimed successor or a comparison total here.
* [`native-integration.json`](native-integration.json) is a source-inspection plan, explicitly not an implementation or run.  No integrated specialised source/binary identity or current Silesia total existed at this read-only checkpoint.

## Public comparator refresh

The primary [Silesia Corpus compression ranking](https://mattmahoney.net/dc/silesia.html) was checked on 2026-10-04.  The page says its program versions are current to 2026-09-29, requires open source, compresses the 12 files independently, and ranks by total compressed bytes.  Its first listed result is `paq8px_v217 -12L`, 27,682,006 bytes.  This establishes that publication scope and the public comparator changed since the retained local snapshot; it does not validate CIX, nor does it make the historical 25,481,891-byte research receipt an official comparable public result.

## Required regression readout for the one authorised pass

For each canonical member, record the frozen integrated source/binary identities; recognised candidate families; selected complete archive bytes; wall/CPU/peak memory; archive SHA-256; independent archive-only restoration SHA-256; candidate omissions and their reasons.  Compare the resulting total to 25,481,891 only as a historical regression reference.  Publish neither a rank nor a global-optimality claim from that comparison.
