# Native-final v3 target preservation attempt v1

Date: 2026-10-05  
Scope: prepared only; no live v3 target member was hashed, archived, copied, or removed during preparation.

The whole retained-work measurement is 3,721,621,504 bytes. With the required 620,756,992-byte Sonar reservation and a 1 MiB margin, the final retained-work maximum is 3,378,194,432 bytes. Reclaiming the 454,594,560-byte v3 target can meet that ceiling only if the actual XZ archive, full manifest, and separately preserved optimized binaries fit the measured post-deletion calculation.

The prepared single-threaded XZ attempt has a 90,000,000-byte file cap, preset 9, a 4,000,000-byte full-manifest cap, four leased CPUs, a 12 GB memory limit, and a 900-second wall limit. It copies and verifies the three receipt-bound `release-lto` binaries (`cix`, `cixcat`, `uncix`) separately, and also includes them in the full archive. This preserves Cargo's existing `cix` hardlink to its dependency member. The full manifest and archive verification prove every target file byte, mode, symlink, and hardlink.

Before removal the recipe requires the v3 job receipt and outer raw result to report terminal pass, and validates the intentionally `running` in-work receipt only for its completed successful phase records. It also requires the actual alias receipt plus its stdout to prove exactly one successful `cli::policy_tests::program_name_normalization_is_platform_specific` test. Admission charges the 90 MB archive cap, all three binary copies, the full manifest cap, and metadata margin. It rejects active users, changed target members, external hardlinks, failed archive verification, missing binary identity, an over-cap archive/manifest, or insufficient measured post-delete capacity. Each failure keeps `target` intact and writes a failure receipt; any partial archive remains as evidence rather than being removed.
