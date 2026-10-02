# Legacy LZ warning remediation

## Scope

Frozen source: `a628bda23e09bb43cceefa2d9e29009fbcc1df67`.

Only `rust/cix-native/src/legacy_lz.rs` changed.  The patch resolves the four
reported findings without lint suppression:

* `manual_contains` at the composition validation uses `parts.contains(&0)`.
* `type_complexity` names the integer-class return components.
* `if_same_then_else` merges the two zero-emission conditions.  `one == 0` is
  still evaluated before `decoder.target(remaining)`, so the original
  short-circuit and arithmetic-decoder call order remain intact.
* `too_many_arguments` groups reconstruction metadata in
  `ReconstructionContext`.

No encoder choice, payload layout, or decoder policy changed.

## Durable receipt

`receipt-manifest.json` indexes the immutable input fields, source and patch
digests, worktree state, tool identities, binary digests, resource-control
readback, exact focused-test command, raw test output, exit status, payload
comparison, actual Clippy exits, and the failed unqualified manual decoder
attempt.  Interpret the raw exit records directly; this README makes no
additional test or whole-crate-lint claim.
