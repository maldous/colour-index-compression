# CIX local Silesia research

The current user-authorized objective is first place by total physical compressed
bytes on https://mattmahoney.net/dc/silesia.html under the same effective rules and
freedoms as the existing competitors. Read the full controlling objective in
`docs/research/2026-09-28-competitive-objective.txt`.

- The earlier universal-only constraint is superseded. Format, language, ISA,
  corpus-informed and per-file/per-region specialization are explicitly allowed.
  PAQ-backed and heterogeneous CIX ensembles are allowed. Attribute reused work;
  preserve upstream licensing and reproducibility. No architectural purity rule.
- Run computation locally. Never trigger, depend on or consume GitHub Actions.
  Do not create or modify workflow files to start CI; source pushes must not
  trigger CI. Read-only source downloads are permitted.
- Optimize the sum across the 12 canonical Silesia files compressed independently.
  Count actual physical bytes, including selection metadata, framing and checksums.
  Verify byte-for-byte restoration. A per-file regression is acceptable if the
  total improves. Keep recoverable incumbent artifacts for comparisons.
- Canterbury, canonical Calgary 14 and Artificial are secondary validation and
  regression evidence, not mandatory gates against legitimate Silesia gains.
  Preserve Canterbury Large, enwik8/9, Pizza & Chili Repetitive and modern-corpus
  evidence for later generality assessment. Never label prefix probes as full runs.
- Study PAQ8px v215 -12L, reproduce reference results locally where practical,
  inventory its models/transforms, measure ablations and marginal gains, and build
  stronger CIX combinations. Do not stop at imitation or parity.
- Record input/output hashes, exact per-file and total sizes, round trips, encoder
  and decoder time, peak memory, options, source revisions and binary hashes.
  The published per-file values are truncated KB: do not fabricate exact deficits.
- Use `.venv/bin/python`; keep local parallelism within actual CPU/memory capacity.
  `OMP_NUM_THREADS=1` is appropriate for small BWT jobs. Run relevant tests with
  `-m pytest -q --timeout=45` and verify real codec invariants.
- First-place claims require all 12 locally encoded/decoded/restored physical
  streams and a total strictly below the live leader. Refresh the leaderboard
  before claiming success. An equivalent numerical position is not an official
  listing. Published eligibility requires freely downloadable public source.
- Consult `docs/research/` and current process/artifact state; stale logs or a prior
  session summary do not establish a process is still running.
