# Native CLI and installed binding checkpoint

The ordinary CLI now reaches native whole-input selection, mixed-content
competition, and historical full-engine decoding. Automatic whole-input
selection currently applies to unconstrained regular files of at most 128 MiB
when the resource budget admits the complete selection baseline. Explicit
selection controls, streams and larger inputs retain their existing paths;
their full specialist coverage remains open. This is a focused implementation
checkpoint, not release acceptance or a benchmark result.

## Passing evidence

The immutable job receipts in `cli-bindings-evidence.json` identify the source
snapshots, commands, failures, and scope of each passing check. Across the
recorded scopes, 59 Rust tests passed, followed by eight Python and three Go
installed-library tests. Some Rust test targets intentionally contain duplicate
legacy scenarios; this count is not a count of independent behaviours.

The focused checks establish:

- Automatic named-file selection and fresh exact CLI restoration, including
  retained native BEST candidate reporting and complete archive comparison.
- Full-engine I/O bounds, fragmented readers, exact archive limits, cancellation,
  malformed/trailing data rejection, and native/raw decoding without unrelated
  image providers or HOME discovery.
- Safe stream-ABI option/output pointer validation, clustered CLI flags, and
  low-budget fallback before whole-input allocation.
- Python and Go consumers using the relocated shared SDK. Python also tests
  dictionary persistence and standard-format calls. Bindings remain optional
  consumers; standalone CIX has no Python requirement.
- A relocated native-only runtime with one physical `cix` executable and
  `uncix`/`cixcat` symlink aliases, all restoring exactly. Full-engine installer
  configuration without explicit bridges fails as intended.

The final binding checks reused the product compiled by `cli-bindings-v5`;
`cli-bindings-v8/reused-build.json` binds the unchanged compiled inputs and
binary hashes. Only consumer fixtures changed after that build. The new job
command adapter was not registered in that build, so these results do not
qualify the job command or subsequently added language/host adapters.

## Preserved failed attempts

`v1` found compile errors. `v2` found an undersized job fixture budget. `v3`
exposed missing clustered short flags, which were implemented. `v4` exposed a
legacy assertion that assumed a particular container even when another valid
archive won. `v5` and `v6` failed a standard-format binding fixture whose output
cap did not cover its conservative admission bound. `v7` was prepared but not
dispatched after that same insufficient bound was caught in review. Corrected
consumer-only `v8` passed. Passing substeps do not turn those failed jobs into
overall passes.

## Remaining release work

The job command requires its own source-bound checks. Expert-control parity,
full-engine streaming, multi-file CLI, useful parallelism, heavy BEST budget
policy, complete runtime dependency closure, additional adapters and platforms,
SquashFS, Sonar/dead-code closure, and final optimized qualification remain
open. Native-only staging is not full-engine package qualification. The
coordinator owns acceptance of RC requirements; benchmark and publication HOLD
remain unchanged.
