# Rust full catalog: frozen-plan protocol

This directory receives immutable native CIX FAST, DEFAULT and BEST catalog
plans. The catalog source is the existing Squash-site manifest. Its 28 entries
contain 11 Canterbury, 12 Silesia and five explicitly authorized fixture
inputs: `enwik8`, `fireworks.jpeg`, `geo.protodata`, `paper-100k.pdf`, and
`urls.10K`. Preparation requires `acquisition-extension.json`, which binds
the five fixture hashes and provenance before a plan is frozen. It does not
acquire inputs itself.

Every plan freezes a copy of the supplied native artifacts under
`benchmark-work/cix-full-catalog/<identity>/final` before manifest creation.
This adapter is pinned to the reviewed `d66739120c40fc409f2bf011b165389fc1062c2b`
release and its recorded `cix`/`uncix` hashes; a different build requires a
new study adapter rather than being mixed into this plan.
The frozen manifests also hash [host-runtime.json](host-runtime.json), which
records the dynamic-library identities used by this host build.
It records all 150 cells: 33 Canterbury/Calgary/Artificial gate inputs across
FAST/DEFAULT/BEST, followed by 17 remaining catalog inputs across the same
profiles.
Canterbury is present in both the gate and catalog but appears once per
profile. Every cell is fresh for the study; previous-study evidence remains a
control and is never relabelled as a d667 result. Resume only reuses an
identical completed cell from this frozen study through its scheduler terminal
and rehashed manifest/build identity.

Use:

```bash
python3 benchmarks/cix_full_catalog.py --id rust-catalog-v1 \
  --artifacts benchmark-work/cix-fast-release/d66739120c/final --prepare

python3 benchmarks/cix_full_catalog.py --id rust-catalog-v1 \
  --artifacts benchmark-work/cix-fast-release/d66739120c/final --run
```

Cells are serial so each one owns CPUs 16–19. FAST and DEFAULT have an 1,800
second wall budget; BEST has 7,200 seconds. Each has a 3 GB RSS and 1 GB
temporary-space cap. WaveScheduler retains the aggregate four-core, 12 GB RAM,
4 GB temporary-space, no-swap limit. A fresh native decoder verifies every
archive. Any verification mismatch stops dispatch; budget failures stay in the
ledger as non-ranked terminal outcomes. The results ledger records complete
archive bytes and SHA-256, input and binary identities, GNU Time wall time,
user CPU, system CPU, their sum, and RSS for each phase. Catalog work cannot
start until every CCA profile cell is verified.

BEST retains its normal native whole-archive search bound of 900 seconds. The
outer cell wall budget does not silently extend that bound. Verbose selector
stderr retains the selected package, native-search budget, and omitted/trial
or budget-skip reporting. No format, backend, route, block, history, memory,
or thread override is passed. Named inputs retain the normal BEST
whole-archive eligibility; large inputs may legally select normal streaming
CIXG2, and selector stderr records that choice.
