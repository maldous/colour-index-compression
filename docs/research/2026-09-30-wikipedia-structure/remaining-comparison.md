# Remaining structural screening results

Completed bounded screening, 2026-09-30. Every candidate is reported before portfolio selection. These are small-region research measurements, not full-enwik9 or Hutter qualification results.

All candidates use pinned PAQ8px v216, -4 -simd AVX2. Raw identities, exact commands, immutable source snapshots, input hashes, timings and independent restoration receipts accompany remaining-comparison.json.

| Input | Candidate | Complete bytes | PAQ payload | Outer metadata | Outer framing | Difference from original | Encode s | Decode s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dev100M | original | 9487 | 9421 | 37 | 29 | +0 | 3.172344 | 3.195249 |
| dev100M | B | 9623 | 9430 | 164 | 29 | +136 | 3.213278 | 3.166721 |
| dev100M | C | 9668 | 9514 | 125 | 29 | +181 | 3.311652 | 3.322931 |
| dev100M | D | 9751 | 9542 | 180 | 29 | +264 | 3.315686 | 3.322695 |
| dev400M | original | 8402 | 8336 | 37 | 29 | +0 | 3.123093 | 3.143743 |
| dev400M | B | 8534 | 8340 | 165 | 29 | +132 | 3.073498 | 3.061519 |
| dev400M | C | 8663 | 8506 | 128 | 29 | +261 | 3.425846 | 3.382685 |
| dev400M | D | 8879 | 8666 | 184 | 29 | +477 | 3.450915 | 3.398568 |
| synthetic | original | 258 | 192 | 37 | 29 | +0 | 2.249303 | 2.294413 |
| synthetic | B | 387 | 192 | 166 | 29 | +129 | 2.012149 | 2.046283 |
| synthetic | C | 397 | 238 | 130 | 29 | +139 | 2.672111 | 2.678715 |
| synthetic | D | 440 | 226 | 185 | 29 | +182 | 2.315951 | 2.274227 |

Original = unchanged input; B = order-preserving stack prediction; C = shared typed streams; D = shared page skeletons and values. Each transformation is measured directly; this table does not substitute a portfolio fallback for a losing candidate.

All 12 archives passed independent archive-only decoding with original input inaccessible to the decoder. At commit preparation, archive sizes, archive SHA-256 and restored SHA-256 were rechecked against raw files. All outer size components sum exactly. Inner descriptors, rules, boundaries, values and exceptions are already inside the PAQ payload; their pre-compression breakdown is retained in transform_accounting and must not be added a second time.

The Wikipedia inputs are 32,768-byte regions starting at offsets 100,000,000 and 400,000,000. The deterministic synthetic source is defined in benchmarks/hutter_structure_batch.py. Exact hashes are in each manifest and result.

All three structural candidates lose to original-byte PAQ on both regions and the synthetic case. No holdout promotion is justified by these measurements. The 600M/900M structural holdouts remain unevaluated by this batch.

Limitations: one measured repetition; research timing, not qualification timing; memory values are sampled cgroup lower bounds, not true peak RSS. The transmitted diagnostic JSON is charged in full, although it is not a minimal reconstruction format. Program/runtime footprint is separately inventoried and is not a complete Hutter package size.

The earlier first-comparison.json remains an immutable historical trial. Its original-mode metadata was 51 bytes, versus 37 in this frozen batch. Do not merge it into a same-format aggregate without an actual matched-format confirmation run. No earlier evidence has been rewritten.
