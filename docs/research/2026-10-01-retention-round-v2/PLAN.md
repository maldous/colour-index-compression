# Corrected v2 execution plan

The experiment matrix, profile policies and resource limits remain those in
the preserved v1 plan. V2 changes only the immutable execution dependency
closure and experiment identities.

- Baseline CIX source remains commit `1302bd7bec130c3105181e6a23ee82c6f2a04838`.
- The source closure includes tracked CIX modules, the retention harness,
  bounded runner, scheduler, generic adapter, profile implementation and the
  two frozen policy/input registries.
- A copied-snapshot `inventory` execution must pass before v2 manifests exist.
- V1 replication inputs are imported and physically rehashed; no range is
  reselected.
- V1 claims, manifests and failure logs stay immutable and are excluded from
  v2 execution.
- V2 cells retain one core, 2 GB RSS, 100 MB temporary space and 180 seconds;
  waves retain four cores, 12 GB RAM, 4 GB temporary space and zero swap.
- Three startup-inclusive encodes and three source-inaccessible decodes remain
  required for qualification.
- Unexpected command or restoration failures stop the next wave. Declared
  route timeouts and resource exclusions remain visible as unqualified results.

The matrix is 864 exposed-slice cells plus 306 fresh-replication cells. Scaling
remains a later frozen-shortlist stage. No GitHub Actions, network access,
publication or full-corpus work is part of this harness.
