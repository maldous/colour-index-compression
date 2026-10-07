# TrialState refactor parity receipt

## Scope

This packet qualifies the source-only `TrialState` extraction in
`rust/cix-native/src/portfolio_auto.rs` at candidate
`35642acb9840108c10e634accd497c76c1bad3b0` against its direct parent
`fb5f87f56cfa27e9c2bf4161cf5acdc12a8f5616`. The commit changes no selector
policy, candidate registry, package cost calculation, resource accounting, or
external-backend policy.

The hypothesis was that grouping the mutable native-trial arguments into
`TrialState` preserves the complete `cix --best --explain` result. Its exact
command and SHA-256 are in `raw/hypothesis*`.

## Method

Both detached source trees were built with the direct stable Rust toolchain as
release `cix` and `uncix` binaries, serialised to CPU 18. The fixed 512-byte
input is generated from a deterministic byte recipe; its SHA-256 is
`071c936bb9b537853739e4197ae73e90bf41a092d50aa278b49a7c79dd0e89c4`.

Each binary executed the same `--best --explain -f -o ARCHIVE INPUT` command
in a transient user service with `CPUAffinity=18`, `MemoryMax=1 GiB`, and
`MemorySwapMax=0`. The live cgroup receipts show the actual CPU affinity,
limits, peak resident CIX cgroup memory, and zero swap current/max. The
parent and candidate peak values were 98,713,600 and 98,672,640 bytes.

The 38,477-byte exploratory attempt was stopped before it emitted a valid
archive when the historical parent remained in CIXM6 search. It is retained
only as a cancellation record. It is not used for a result or performance
claim. The bounded 512-byte input is the complete parity case.

## Result

Both BEST searches evaluated 24 complete candidates and selected
`cixm6:native-auto:block=16384`, producing byte-identical 76-byte archives:

- archive SHA-256: `f7d85dc81c401f61cb7932269f347bf0b9b055b37eb37636bcd7e9a791746645`
- selected candidate and complete traces: `raw/*-selected-trace.raw`
- parent fresh-decoded the candidate archive and candidate fresh-decoded the
  parent archive; both outputs hash to the input hash.

This is a correctness parity receipt, not a compression or throughput result.
The full raw build output, binary hashes, cgroup readbacks, traces, cross-decode
outcome, and artifact hashes are retained under `raw/`.
