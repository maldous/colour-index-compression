# Verification journal

## Superseded contaminated attempt

The prior worktree must not support acceptance evidence. It had six unrelated
modified Rust files. Its 1 GiB streaming unit scope OOMed, and a CIXZ1 magic
assertion was placed in a shell pipeline without `set -e`; the produced archive
was CIXG2. Those outcomes are failures, not passes. The old zero-byte `tee`
logs are retained only as invalid run artifacts.

## Clean rerun

This worktree is detached at the approved source revision and has exactly two
tracked source modifications: `rust/cix-native/src/streaming_backend.rs` and
the one caller construction in `rust/cix-native/src/main.rs`. All commands use
CPU 28, `MemoryMax=2G`, `MemorySwapMax=0`, and one cargo job. Command status is
recorded directly from the systemd unit, without a shell pipeline.

The clean release unit rerun, clean release `streaming_pipe` rerun, and clean
Clippy run each exited zero. The first strict clean attempt used a 1 GiB encoder budget. The encoder
exited zero and selected a valid CIXG2 archive; the subsequent strict CIXZ1
magic assertion exited one. This was an assertion failure, not an encoder
admission failure. At a 2 GiB
encoder admission, the strict producer and decoder pipeline exited zero,
produced CIXZ1, and restored exact bytes.

Resource limits for successful collected units are declared launch settings;
no retained per-binary membership or live limit readback is claimed. Journals
corroborate command completion and zero swap usage.
