# Retention evidence entry point

This directory is intentionally pre-execution. `PLAN.md` defines the accepted
matrix, budgets, attribution rules and gating. `benchmarks/retention_round.py`
creates immutable manifests only after root supplies the canonical commit, and
requires a second explicit authorization before dispatch.

Expected generated evidence after freeze includes `source-freeze.json`,
`replication-inputs.json`, `cells.json`, `plan-summary.json`, manifests, bounded
runner receipts, raw repetition timing/codec/trace files and `results.json`.
No GitHub Actions, network acquisition, external publication or full-corpus run
is reachable from this harness.
