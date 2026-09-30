# CIX forward-domain research

| Domain / variant | Raw bytes | Complete bytes | Δ matched PAQ | Verification | Encode / decode s | Peak RSS KiB (encode/decode) | Cgroup lower bound |
|---|---:|---:|---:|---|---:|---:|---:|
| executable / original (paq) | 166568 | 41016 | — | SHA256_MATCHED_REHASHED | 31.22 / 29.33 | 791296 / 791040 | 822145024 |
| numeric / original (paq) | 288885 | 11709 | — | SHA256_MATCHED_REHASHED | 23.33 / 20.67 | 472576 / 472320 | 495493120 |
| volume / jxl-planar3-e10 (native) | 1180064 | 226074 | 2336 | SHA256_MATCHED_REHASHED | 4.95 / 0.14 | 86480 / 46792 | 68714496 |
| volume / original (paq) | 1180064 | 223738 | — | SHA256_MATCHED_REHASHED | 132.66 / 121.74 | 667392 / 667136 | 701485056 |
| volume / delta-z (paq) | 1180064 | — | — | NOT_RUN | — / — | — / — | — |
| database / original (paq) | 249655 | 12098 | — | SHA256_MATCHED_REHASHED | 23.42 / 20.95 | 477184 / 476928 | 500183040 |
| numeric / original (paq) | 288330 | — | — | NOT_RUN | — / — | — / — | — |
| executable / raw (paq) | 166568 | 41015 | -1 | SHA256_MATCHED_REHASHED | 31.13 / 29.18 | 791040 / 790784 | 822177792 |
| volume / plane-stack (paq) | 1180064 | — | — | NOT_RUN | — / — | — / — | — |
| molecular / hydrogen_slots_v1 (paq) | 29663 | 3997 | 4 | SHA256_MATCHED_REHASHED | 2.78 / 2.73 | 466176 / 465920 | 488603648 |
| executable / address (paq) | 166568 | 41072 | 56 | SHA256_MATCHED_REHASHED | 31.48 / 31.09 | 791040 / 790784 | 822050816 |
| molecular / original (paq) | 20204 | — | — | NOT_RUN | — / — | — / — | — |
| numeric / numeric-delta-columns-v1 (paq) | 288885 | 11493 | -216 | SHA256_MATCHED_REHASHED | 9.96 / 9.70 | 779776 / 779520 | 812425216 |
| molecular / hydrogen_slots_v1 (paq) | 20204 | — | — | NOT_RUN | — / — | — / — | — |
| numeric / numeric-delta-columns-packed-meta-v1 (paq) | 288885 | 25761 | 14052 | SHA256_MATCHED_REHASHED | 7.35 / 7.41 | 777472 / 777216 | 809975808 |
| molecular / original (paq) | 29088 | 2219 | — | SHA256_MATCHED_REHASHED | 3.08 / 2.99 | 465408 / 465152 | 487874560 |
| database / literal (paq) | 249655 | 12108 | 10 | SHA256_MATCHED_REHASHED | 24.93 / 24.08 | 477184 / 477184 | 500269056 |
| executable / address-packed (paq) | 166568 | 41168 | 152 | SHA256_MATCHED_REHASHED | 30.70 / 30.35 | 791296 / 790784 | 822042624 |
| database / dictionary_remaining (paq) | 249655 | 13709 | 1611 | SHA256_MATCHED_REHASHED | 6.09 / 6.06 | 652544 / 652544 | 682233856 |
| numeric / numeric-delta-columns-v1 (paq) | 288330 | — | — | NOT_RUN | — / — | — / — | — |
| molecular / original (paq) | 29663 | 3993 | — | SHA256_MATCHED_REHASHED | 3.06 / 2.98 | 466176 / 465920 | 488722432 |
| molecular / hydrogen_slots_v1 (paq) | 29088 | 2056 | -163 | SHA256_MATCHED_REHASHED | 2.66 / 2.64 | 464384 / 464384 | 486969344 |

Encode/decode time is GNU time's elapsed wall clock for the actual I/O command, shown to 0.01 s. Scheduler/runner supervisory elapsed time is retained separately in JSON and is not used as codec timing; this avoids treating launch/poll overhead as compression work on small assets.

Peak RSS is GNU time's Maximum resident set size for each encoder or decoder command and its children, not a simultaneous process-tree aggregate. Cgroup memory is retained as a separate sampled lower bound.

All first-domain candidates are required to independently decode, including size losses. Results are domain-specific forward-transfer evidence; they are not cross-dataset rankings or Hutter results.
