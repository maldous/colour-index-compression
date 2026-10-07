# First structural comparison — complete physical sizes

Input: canonical enwik9 bytes [0,32768), SHA-256 `de91bc4727fadadb7abfa3af752e8d7ac6cfb24c87b7cf4078858088dcd4e5c7`. PAQ8px v216 `-4 -simd AVX2`, identical `source.bin` names; CPU6, 3GiB cap, zero swap, 300-second per-trial budget.

| Candidate | Total bytes | PAQ payload | Outer metadata | Header/selector | Encode s | Decode s | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| A original PAQ | 8,792 | 8,712 | 51 | 29 | 3.153 | 3.147 | +0 |
| B order-stack | 8,901 | 8,708 | 164 | 29 | 3.145 | 3.128 | +109 |
| C typed streams | 9,023 | 8,867 | 127 | 29 | 3.411 | 3.381 | +231 |
| D page skeletons | 9,108 | 8,898 | 181 | 29 | 3.389 | 3.395 | +316 |

Every candidate independently decoded with source paths inaccessible and the exact SHA-256 restored. These are candidate totals before portfolio selection; original PAQ wins. B applied 96 local closing-tag predictions, removing 610 pre-PAQ bytes, but its PAQ payload saved only four bytes and total framing/metadata made it 109 bytes worse. C processes 406 tag/text records. D shares six complete pages with 955 raw dictionary bytes before PAQ and preserves 30,447 bytes as outside/partial-page literals. The raw inner representation costs are already included in the PAQ payload; do not add them to final bytes again.

Actual sampled cgroup memory high-water ranges 485–808 MB; these are lower bounds rather than true process peak RSS. Peak observed temporary storage is under 84 kB for these receipts. Concurrent research times are not Prize qualification. Native binary, interpreter/runtime and model/source footprints remain separate eventual package costs. No Hutter score is claimed.

The external fx2 full-canonical/global-order transform is not a valid matched regional control and was not run. The v215 auxiliary stack results remain separate. Holdout compression at offsets600M/900M has not occurred. The other development regions and synthetic structure cases are next with unchanged configuration. All per-candidate hashes, exact commands and frozen source snapshots are linked through `first-comparison.json`.
