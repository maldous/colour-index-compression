# CIX route-retention round

Status: harness implemented; experiment identities are **not frozen and no
compression has been dispatched**. Root must first review the harness and name
the canonical source commit. Dispatch then requires a separate root-authored
authorization file tied to that frozen source identity.

## Question

For each declared profile and input, does CIX retain the smallest complete,
verified archive among the candidates it actually evaluates? When a reversible
representation or an additional native CIX pass is tried, does its complete
physical result improve that set after all framing and decoder information?

This round does not assert a universal best result. Its scope is the frozen
candidate set, budgets, six exposed screening slices, six mechanically selected
replication slices, and later shortlisted 64 KiB scaling ranges.

## Frozen policies to compare

The public profile names map to the production effort policies without changing
their internal limits:

| Profile | Effort | Search / route / worker cap |
|---|---|---|
| current | balanced | 3.0 s / 1.0 s / 384 MiB |
| speed | fast | 0.75 s / 0.30 s / 256 MiB |
| size | maximum | 12.0 s / 4.0 s / 512 MiB |

Every new cell has the same outer cap: one physical core, 2,000,000,000 bytes
RSS, 100,000,000 bytes temporary storage, and 180 seconds for three encode and
three archive-only decode repetitions. Four cells share the established global
four-core, 12,000,000,000-byte RAM and 4,000,000,000-byte temporary limits.
Swap is disabled by the bounded runner. There is no warm-up; process startup,
profiling, all discarded trials, reads and writes are included.

## Candidate inventory

The 11 implemented representations are `raw`, `runs`, `composition`, `lz`,
`predictor`, `bwt`, `stride`, `phrases`, `ppm`, `mixture`, and `deflate`.
All are forced with the hybrid stream policy on six slices and three profiles
(198 cells). The unchanged-input `original` adapter produces an ordinary CIXG1
archive whose route-2 payload is `streams([input], backend)`; it supplies
hybrid, CIX, DEFLATE, same-count range and adaptive-range controls (90 cells).

LZ, predictor, BWT, stride and phrases are additionally crossed with the four
non-hybrid stream backends (360 cells). This isolates representation and stream
coder effects without pretending that PPM, mixture, raw or direct DEFLATE have
an arbitrary interchangeable backend. Eighteen adaptive-selector cells and 198
route-removal cells measure selected results and contribution; disabling raw is
retained and explicitly classified as a no-op check.

Total initial/exposed matrix: 864 cells. Each has three full encode repetitions
and three independent decodes. Historic mixer failures keep their old identity;
new mixer cells qualify only if all repetitions finish within the declared
profile and outer budgets.

The harness contains a bounded optional one-pass native CIX recode adapter for
a later, separately identified stage. It emits a CIXR1 result only if its full
37-byte wrapper and inner CIXG1 archive are smaller; otherwise it retains the
candidate CIXG1 archive byte-for-byte. This adapter is held out of the baseline
freeze so the unchanged commit-1302bd7 matrix remains the first comparison and
is not silently expanded by concurrent backend work.

## Generalisation

Before any evaluation, `prepare` freezes six new 16 KiB ranges and six disjoint
64 KiB ranges. Locations are selected from file size and occurrence ordinal,
aligned to 16 KiB, without reading content to choose an offset. Hashing then
records identity; it is not publisher verification. Existing Golf labels are
reconciled to “Compression Golf GitHub events” while retaining their legacy
registry aliases.

The fresh 16 KiB wave contains adaptive, all 11 forced hybrid routes, and all
five original-byte controls for all three profiles (306 cells). These ranges are replication evidence, not pristine
after their first wave. The 64 KiB ranges remain frozen for current/size adaptive
and shortlisted forced-route scaling after the initial results choose that
shortlist. No result may choose its own scaling range or settings.

## Evidence and stop rules

The primary physical result is predeclared as repetition zero. All repetition
sizes, hashes, commands, raw GNU timing files, codec reports, block selection
traces, cgroup measurements, budgets and metadata remain available. A candidate
is qualified only when all three archives independently restore the exact input;
the bounded runner separately verifies the primary archive while the source is
inaccessible. Budget failures, partial output and decode failures are unqualified.

Controls and candidates match on input identity, immutable build, effort,
backend where applicable, initial state, repetitions and outer limits. The final
audit must distinguish standalone reference size, equivalent framed size and
selected CIX size. Missing reference presets and PAQ maximum remain exclusions,
not implied candidates within CIX.

## Work classification

- Required now: immutable harness, original controls, all forced hybrid cells,
  backend-matched transforms, adaptive and removal cells, replication freeze,
  exact receipts and attribution tables.
- Hardening after initial evidence: frozen-shortlist 64 KiB scaling, timing
  dispersion interpretation, the separately identified optional recode stage,
  and any selector fix supported by a demonstrated wrong choice.
- Unrelated to this round: format-specific routing, acquisition, Hutter/full
  corpus runs, Sites implementation, GitHub Actions, and historical programme
  restarts.

## Commands

Planning is read-only:

```sh
python benchmarks/retention_round.py inventory
```

After root review, freeze exactly one source commit:

```sh
python benchmarks/retention_round.py prepare --source-commit <full-HEAD-SHA>
```

`run` will refuse to start without a separate JSON authorization whose
`authorized_by` is `/root`, whose `source_freeze` matches the frozen receipt,
and whose `authorized_stages` explicitly include every requested stage.
