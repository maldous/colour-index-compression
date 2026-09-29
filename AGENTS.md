# CIX Hutter Prize / enwik9 research

## Controlling directive — supersedes the historical text below

The current user-authorized objective is exclusively the Hutter Prize: build a
reproducible, self-contained compressor for canonical `enwik9` and surpass the
official threshold under the Prize rules. The Silesia, NNLCB, Wikipedia and
broad-evidence instructions below are historical records only. Do not start,
resume, optimize, or publish them as active work unless the user changes this
directive.

Read `docs/research/2026-09-29-hutter-prize-eligibility.md` and
`docs/research/2026-09-29-hutter-current-inventory.md` before work.

- Canonical enwik9 is exactly 1,000,000,000 bytes, SHA-256
  `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`.
  Never call a prefix, smoke test, enwik8, text8, or Silesia result an enwik9
  score.
- The archived official record is 110,793,128 bytes. At least one-percent
  saving permits an integer submission total of at most 109,685,196 bytes.
  Account for every program/archive/option byte under the documented rule.
- Enwik9-specific optimization is allowed. Preserve exact reconstruction,
  offline operation, one-core/no-GPU execution, the 10,000,000,000-byte RAM
  and 100,000,000,000-byte temporary-disk limits, and `70,000/T` time rule.
- A local candidate requires a full canonical encode/decode, SHA-256 proof,
  immutable receipts bound to program/archive/configuration hashes, actual
  package accounting, and audited public source/licensing evidence. It never
  constitutes official Prize approval.
- The 27-file / 71,104-byte stdlib draft and 2,100-byte smoke restoration are
  dependency/instrumentation prototypes, not score or submission accounting.
- The next active work is a strong Hutter-specific profile, then controlled
  full-enwik9 evidence. Do not run unbounded full encodes while the shared
  measurement boundary is occupied; use its exclusive lock for heavy work.
- Run locally only. Never trigger, depend on, or consume GitHub Actions. Do
  not create or modify workflow files. Preserve external-source licenses and
  do not invent a project license.

## Historical Silesia directive — superseded

The current user-authorized objective is first place by total physical compressed
bytes on https://mattmahoney.net/dc/silesia.html under the same effective rules and
freedoms as the existing competitors. Read the full controlling objective in
`docs/research/2026-09-28-competitive-objective.txt`.

The latest focused directive is prediction-constrained combinatorial research:
use actual PAQ-class modelling to shrink the residual arrangement space, then
test CIX representations against arithmetic coding with identical predictions.
Read `docs/research/2026-09-28-prediction-constrained-cix.md`. Continue existing
reference runs and publish verified milestones to the research Site; prioritize
this hypothesis within the broader search below.

Latest user steering: investigate all opportunities for substantial compression
changes and all technique families needed to win. Do not make the PAQ/CIX
hypothesis an exclusive architecture. Read
`docs/research/2026-09-28-broad-opportunity-frontier.md`; pursue discriminating
local experiments across representations, mathematical constraints, transforms,
grammar/dictionary/match models, neural predictors, mixtures and exact coding.
Keep the existing full-file trials running and allocate extra work within the
observed available memory/CPU/GPU capacity. Prefer material physical savings
over marginal tuning, while preserving every completed qualified improvement.

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
- Hutter Prize work is a separate, enwik9-specific eligibility track; it does
  not change the frozen evidence configuration or imply general-purpose merit.
  Follow `docs/research/2026-09-29-hutter-prize-eligibility.md`. A local gate
  must verify canonical 1,000,000,000-byte enwik9, the exact package formula,
  one-core/no-GPU whole-process resource evidence, and offline source/licensing
  evidence. A passing local gate is only a candidate: official approval belongs
  to the Prize reviewers. Do not create a license declaration on behalf of an
  upstream author or claim eligibility without the required public package.
- Consult `docs/research/` and current process/artifact state; stale logs or a prior
  session summary do not establish a process is still running.
