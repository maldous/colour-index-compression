# CIX-only Silesia temporary-space corrections

Only seven CIX cells previously failed during encoding because their cell-level temporary-space cap was 100,000,000 bytes. They were rerun with a 1,000,000,000-byte temporary-space allowance. Inputs, input hashes, CIX source snapshot, presets, per-cell RAM and wall budgets were held fixed. No other method or dataset was rerun. The original failed receipts remain in the parent Silesia v3 run records.

All seven new archives passed a separate archive hash/length check and archive-only decode with exact source SHA-256 equality. The retry archives, restored outputs, and immutable build directories remain local under `runs/`; large payloads are not committed. Receipts, configs, time logs and command logs are preserved here for review.

| Dataset | Profile | Complete archive bytes | Encode s | Decode s | Encode peak RSS MiB | Selected route | Restore |
|---|---:|---:|---:|---:|---:|---|---|
| mozilla | fast | 51,221,714 | 5.04 | 0.35 | 164.6 | `zstd:direct` | exact SHA-256 |
| mozilla | current | 18,505,246 | 17.89 | 0.33 | 700.6 | `zstd:direct` | exact SHA-256 |
| mozilla | size | 17,914,439 | 74.56 | 1.99 | 264.4 | `bzip2:direct` | exact SHA-256 |
| nci | fast | 4,022,819 | 4.69 | 0.21 | 116.0 | `brotli:direct` | exact SHA-256 |
| nci | current | 2,156,978 | 9.64 | 0.19 | 629.2 | `brotli:direct` | exact SHA-256 |
| nci | size | 2,988,060 | 70.66 | 0.22 | 194.3 | `gzip:direct` | exact SHA-256 |
| samba | fast | 6,170,022 | 4.45 | 0.19 | 79.9 | `brotli:direct` | exact SHA-256 |

Profile scope remains distinct. The maximum-size PAQ preset was already pre-excluded by its approximately 29 GB memory requirement; these temporary-space retries do not change that separate exclusion. This is still a stopped/incomplete matrix: untouched methods and cells retain their prior status.
