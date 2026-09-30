# Backend-retention evidence entry point

`PLAN.md` defines the bounded integration and counterfactual stages.
`benchmarks/backend_retention_round.py` prepares immutable manifests only after
the final backend implementation hash is supplied and its copied-snapshot
inventory succeeds. Preparation performs no compression; dispatch requires a
separate root authorization tied to the source-freeze identity.

Generated evidence will include the source freeze, 120-cell staged registry, manifests,
three-repetition reports, all candidate archives, extracted standalone payloads,
raw GNU timings, bounded-runner receipts, selected-route decode receipts and
`results.json`. Counterfactual identities are added only after complete baseline
integration readback.
