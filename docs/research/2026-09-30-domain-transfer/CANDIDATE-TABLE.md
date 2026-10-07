# All domain candidates before selection

Control: PAQ v216 `-4 -simd AVX2`, one CPU, identical input bytes and paid outer framing. Every row includes all physical archive bytes. Negative Δ means smaller. All figures apply only to the named input. JXL is a backend change, not evidence for a CIX rank coder. Timing is one exploratory measured command per phase.

| Input / candidate | PAQ B | Complete B | Δ B | Encode / decode s | Peak RSS MiB encode / decode | Verification |
|---|---:|---:|---:|---:|---:|---|
| uci-adult-first2048-nonblank.data / original | 12098 | 12098 | 0 | 23.42 / 20.95 | 466.0 / 465.8 | SHA256_MATCHED_REHASHED |
| uci-adult-first2048-nonblank.data / dictionary_remaining | 12098 | 13709 | 1611 | 6.09 / 6.06 | 637.2 / 637.2 | SHA256_MATCHED_REHASHED |
| uci-adult-first2048-nonblank.data / literal | 12098 | 12108 | 10 | 24.93 / 24.08 | 466.0 / 466.0 | SHA256_MATCHED_REHASHED |
| strip-0d980587ada7.bin / original | 41016 | 41016 | 0 | 31.22 / 29.33 | 772.8 / 772.5 | SHA256_MATCHED_REHASHED |
| strip-0d980587ada7.bin / address | 41016 | 41072 | 56 | 31.48 / 31.09 | 772.5 / 772.2 | SHA256_MATCHED_REHASHED |
| strip-0d980587ada7.bin / address-packed | 41016 | 41168 | 152 | 30.70 / 30.35 | 772.8 / 772.2 | SHA256_MATCHED_REHASHED |
| strip-0d980587ada7.bin / raw | 41016 | 41015 | -1 | 31.13 / 29.18 | 772.5 / 772.2 | SHA256_MATCHED_REHASHED |
| pubchem-2d-cids-176-180-239-280-6276-6322-784-887.sdf / original | 1536 | 1536 | 0 | 2.31 / 2.25 | 450.8 / 450.5 | SHA256_MATCHED_REHASHED |
| pubchem-2d-cids-176-180-239-280-6276-6322-784-887.sdf / hydrogen_slots_v1 | 1536 | 1462 | -74 | 2.06 / 2.05 | 449.5 / 449.2 | SHA256_MATCHED_REHASHED |
| pubchem-2d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf / original | 2219 | 2219 | 0 | 3.08 / 2.99 | 454.5 / 454.2 | SHA256_MATCHED_REHASHED |
| pubchem-2d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf / hydrogen_slots_v1 | 2219 | 2056 | -163 | 2.66 / 2.64 | 453.5 / 453.5 | SHA256_MATCHED_REHASHED |
| pubchem-3d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf / original | 3993 | 3993 | 0 | 3.06 / 2.98 | 455.2 / 455.0 | SHA256_MATCHED_REHASHED |
| pubchem-3d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf / hydrogen_slots_v1 | 3993 | 3997 | 4 | 2.78 / 2.73 | 455.2 / 455.0 | SHA256_MATCHED_REHASHED |
| noaa-water-level-202401-seattle.csv / original | 9936 | 9936 | 0 | 19.57 / 18.01 | 460.0 / 459.5 | SHA256_MATCHED_REHASHED |
| noaa-water-level-202401-seattle.csv / numeric-delta-columns-v1 | 9936 | 8988 | -948 | 8.88 / 8.14 | 761.8 / 761.2 | SHA256_MATCHED_REHASHED |
| noaa-water-level-202401.csv / original | 11709 | 11709 | 0 | 23.33 / 20.67 | 461.5 / 461.2 | SHA256_MATCHED_REHASHED |
| noaa-water-level-202401.csv / numeric-delta-columns-packed-meta-v1 | 11709 | 25761 | 14052 | 7.35 / 7.41 | 759.2 / 759.0 | SHA256_MATCHED_REHASHED |
| noaa-water-level-202401.csv / numeric-delta-columns-v1 | 11709 | 11493 | -216 | 9.96 / 9.70 | 761.5 / 761.2 | SHA256_MATCHED_REHASHED |
| nibabel-example4d.nii / original | 223738 | 223738 | 0 | 132.66 / 121.74 | 651.8 / 651.5 | SHA256_MATCHED_REHASHED |
| nibabel-example4d.nii / delta-z | 223738 | 233045 | 9307 | 131.68 / 132.18 | 652.2 / 652.0 | SHA256_MATCHED_REHASHED |
| nibabel-example4d.nii / jxl-planar3-e10 | 223738 | 226074 | 2336 | 4.95 / 0.14 | 84.5 / 45.7 | SHA256_MATCHED_REHASHED |
| nibabel-example4d.nii / plane-stack | 223738 | 223767 | 29 | 134.35 / 136.49 | 652.0 / 651.5 | SHA256_MATCHED_REHASHED |

Machine-readable `results.csv` and `results.json` include exact hashes, cell identities, payload/metadata costs and receipt paths. GNU-time Max RSS is the maximum recorded for a command or its children, not simultaneous process-tree RSS. Sampled cgroup memory and disk are separate. Decoder/runtime package size is not an archive-size claim. There is no portfolio selector or cross-dataset leaderboard in this report.
