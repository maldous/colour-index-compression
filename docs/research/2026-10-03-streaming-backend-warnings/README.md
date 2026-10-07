# Streaming backend warning remediation

This clean worktree starts at `a628bda23e09bb43cceefa2d9e29009fbcc1df67`.
It contains only the `streaming_backend.rs` request-context refactor and the
one caller wire in `main.rs` required to compile it.

`EncodeRequest` reduces `encode` from 12 arguments to three. `FinishRequest`
reduces `finish_stream` from 10 arguments to three. The refactor does not add
lint suppression or change codec choices, state ordering, pipe polling,
backpressure, partial-write handling, bounded payload checks, or footer and
truncation validation.

The 1 GiB script failure is a magic assertion after successful CIXG2 encoding,
not encoder admission failure. See corrected results.json and journal.md.
Resource limits of collected successful units are declared, not live-probed
per-binary limits. These are functional checks, not performance/RSS results.
