# CIX route-retention round v2

This is the corrected immutable-snapshot identity for the bounded retention
round. Version 1 remains preserved in `../2026-09-30-retention-round/`; its four
claimed cells failed before compression because the copied snapshot omitted
modules imported by the harness. Those cells are never restarted.

V2 adds the existing bounded runner, scheduler, profile policy and input
registry to the immutable dependency closure. Before manifests are written,
`prepare` copies the complete declared closure to a temporary directory and
successfully executes the copied harness's read-only `inventory` entrypoint.

The 12 v1 replication ranges are imported byte-for-byte after their offsets,
lengths and SHA-256 identities are rechecked. Selection is not repeated and no
new holdout locations are chosen.

No compression runs during preparation. Dispatch still requires a separate
root authorization bound to the v2 source-freeze identity.
