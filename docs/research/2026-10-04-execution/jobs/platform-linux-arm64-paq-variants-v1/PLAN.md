# ARM64 remaining PAQ variants v1

This prepared successor covers the three CIX PAQ bridge variants not included in the passed ARM v215 exchange: `v216`, `joint_discount`, and `store_state`. These are the remaining bridge directories under `rust/cix-native/codecs/paq`; `v215` is intentionally excluded because its ARM ABI/archive exchange already passed.

For each variant, the runner verifies the full retained vendor hash map from its passed x64 qualification source receipt, verifies the passed x64 bridge/probe hashes, copies the current CIX wrapper into isolated work, and checks that the current `paq_bridge.rs` descriptor names its vendor source and C ABI process symbol. It does not build Rust or change the worker-only architecture gate.

It cross-builds each wrapper with the retained prefix named by the passing v3 toolchain receipt. Host CMake/compiler commands use only the receipt's scoped host library path and the required target-bin `-B` search path. QEMU receives an empty host library path, Cortex-A72, and the target-only `usr/aarch64-linux-gnu` runtime root. The ELF interpreter must resolve beneath that root.

Each direct-header ABI probe runs in fresh processes: ARM level-1 encode, ARM archive-only decode, qualified x64 decode of the ARM archive, and ARM decode of the x64 archive. The fixed 4,096-byte fixture must match every decoded output. This is archive compatibility and C ABI evidence only; it does not establish full-engine worker operation, native ARM performance, or an archive-byte equality requirement.

The recipe uses four physical cores (8, 10, 12, 14), up to 12 GB memory, and the existing 4 GB shared-work scheduler bound. It reserves 180 MB of new allocated work: three retained CMake trees, copied wrappers, three small probes/libraries, fixtures, and exact per-command logs. The passed x64 build trees measure about 7.5–7.9 MB each, which supports this cap; `run.py` admits only when shared allocation plus the reservation fits and rechecks after every variant. No download or execution has been performed.
