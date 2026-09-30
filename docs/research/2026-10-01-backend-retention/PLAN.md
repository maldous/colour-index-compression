# Integrated backend retention evidence

Status: harness implemented but not frozen or dispatched. The reviewed backend
implementation is private commit `ceb41d6442da8454c247fd3aed2b31d50c452ada`,
SHA-256 `62e4f571769805ac400edba3f90f1ccde7e8fe7a94b67a74c717a15cee4ba17a`.

The first stage has 36 cells: twelve exact 16 KiB inputs (six exposed screens
and the exact six replication ranges frozen by retention v2) crossed with
current, speed and size profiles. Each cell runs three independent portfolio
encodes and three independent selected-archive decodes. Repetition zero is the
predeclared physical result; other repetitions measure timing and stability.

Each encode keeps every attempted archive before selection. For an external
backend it additionally extracts and hashes the standalone reference payload,
then records the 47-byte CIXB1 framing cost. Native CIXG1 archives have zero
additional envelope bytes. The harness independently asserts that the selected
archive is the smallest complete `VERIFIED` framed attempt. It also reports the
standalone-payload best, framed best, selected route, discarded/search wall,
candidate-validation wall and total audit wall.

Exact codec settings come from the pinned profile policy. PAQ remains policy
excluded, PAQ maximum remains memory excluded, and current/size Brotli remains
excluded because its static dictionary conflicts with the generic policy.
These exclusions are visible rather than approximated. Previously measured
standalone payloads and retention-v2 adaptive cells are linked by identity when
available; no completed baseline is rerun merely to change its label.

The selected route is decoded in a separate bounded phase with the original
source and materialized source path inaccessible. Every qualified cell needs
three exact SHA-256 restorations. Each cell has one core, 2 GB RSS, 100 MB
temporary storage and 180 seconds. Waves share four cores, 12 GB RAM, 4 GB
temporary storage and zero swap.

The integrated size profile permits up to 60 seconds of aggregate candidate
search, while the frozen maximum CIX baseline permits 12 seconds. This is a
declared configuration/search-scope difference inside the same 180-second outer
cap. If three repetitions plus validation cannot finish inside that cap, the
cell remains budget-limited; the harness does not extend it silently.

After all 36 integrated cells verify, `prepare-counterfactuals` freezes two
evidence-driven cells per result: disable the selected candidate, then compare
native-only when an external backend won or external-only when CIX won. These
cells are never inferred or launched before the integrated readback exists.

Three other separately ranked stages are frozen with the implementation but
are not part of the first 36-cell launch:

- 36 optional native-recode cells use the already frozen retention leaf. They
  charge the 37-byte CIXR1 metadata and retain the unwrapped adaptive CIXG1
  archive unless the complete recode is strictly smaller.
- 24 fast-profile diagnostics measure the exact ranked bzip2 and XZ fast
  presets that the production fast plan shortlisted out. Each preserves its
  standalone payload and a paid 47-byte CIXB1 envelope; these measurements do
  not make the candidates production-eligible.
- Six pre-frozen 64 KiB regions receive current/size integrated portfolios (12
  cells) plus matched unchanged adaptive CIXG1 controls (12 cells). Integrated
  attempts already provide the eligible standalone payloads, so this stage does
  not repeat a broad route Cartesian product.

Commands after the backend implementation is final:

```sh
.venv/bin/python -m benchmarks.backend_retention_round snapshot-check
.venv/bin/python -m benchmarks.backend_retention_round prepare \
  --backend-sha256 62e4f571769805ac400edba3f90f1ccde7e8fe7a94b67a74c717a15cee4ba17a
.venv/bin/python -m benchmarks.backend_retention_round run \
  --stage integrated \
  --authorization docs/research/2026-10-01-backend-retention/authorization.json
.venv/bin/python -m benchmarks.backend_retention_round collect
.venv/bin/python -m benchmarks.backend_retention_round prepare-counterfactuals
```

Root alone creates dispatch authorization and launches cells. This harness has
no network, GitHub Actions, publication or full-corpus path.
