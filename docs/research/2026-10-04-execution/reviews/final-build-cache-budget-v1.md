# Final-build cache budget v1

Date: 2026-10-05
Scope: read-only inventory of `benchmark-work/native-rc-check-v1`; no cache was removed and no build was run.

`target/debug` remains an evidence-preservation candidate only. Ongoing analysis references it, so it is not available for removal or build headroom until root explicitly schedules the final build.

The retained work occupies **3,335,245,824 bytes** against the shared 4,000,000,000-byte limit. That leaves **664,754,176 bytes** (633.9 MiB). Reserving a new 700 MiB build needs 734,003,200 bytes, so the current state is short by **69,249,024 bytes**.

The smallest observed single cache directory that covers that shortfall is [target/debug](/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/target/debug): **125,628,416 allocated bytes**. It is shared Cargo debug build output: build scripts, fingerprints, dependency objects, and debug executables. Pruning it would leave 3,209,617,408 bytes retained and **790,382,592 bytes** of headroom (753.8 MiB), sufficient for the requested reservation with roughly 53.8 MiB margin.

This selection deliberately leaves these protected categories intact:

- `distribution-engineering-v4/{stage,source-output,target}`: the installed distribution, exported source, and optimized release-LTO products. The release static library is hardlinked to the stage and SDK prefix.
- Preserved SDK and consumer artifact archives, result receipts, source trees, installed provider prefixes, and pinned codec archives.
- The Go module cache and Python host SDK, because removing them would create an unplanned dependency reacquisition or provider rebuild.

The root `target/debug` subtree has no observed hardlinks to another retained subtree. Its multi-link files are paired Cargo build-script names within that directory. A prune job must nevertheless verify this immediately before deletion.

The smallest safe action is a dedicated, hash-recorded cache-prune job that only selects `target/debug`. It must first require an idle scheduler and no active final-build output there, then write a deterministic manifest of each selected regular file (relative path, blocks, logical size, SHA-256, device/inode, and link count). It must refuse changed files, paths outside the selected subtree, or any inode with a link outside that subtree. After deletion it must record the aggregate retained-work size and refuse success unless measured headroom is at least 734,003,200 bytes.

The machine-readable inventory and arithmetic are in [final-build-cache-budget-v1.json](final-build-cache-budget-v1.json).
