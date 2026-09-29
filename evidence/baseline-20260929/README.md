# CIX Compression Evidence Baseline — 2026-09-29 / v1

**Preparation in progress. This is not a completed benchmark or publication.**

Frozen CIX implementation: `f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6`.
Interface: `python -m benchmarks.competitive_cli encode INPUT OUTPUT` and
`decode ARCHIVE OUTPUT`; portfolio 25, default configuration, no cached trials.
The normal encoder includes its own full restoration before writing its output;
external wall-clock compression timing includes that work and normal I/O.

Research checkpoint: `research-checkpoint/pre-evidence-20260929-p25` at
`100762c35485928b31218b13edd687fd4185dc81`. The research worktree and selected
physical artifacts are preserved separately; see `manifests/research-preservation.json`
and `../../docs/checkpoints/2026-09-29-evidence-handover.md`.

This evidence area is distinct from the existing research Site and score history.
Historical cached Silesia trials are not fresh controlled timing measurements.
No CIX implementation changes are permitted during this baseline. No GitHub
Actions are used. Discovery resumes only after the requested frozen publication
has passed its evidence gates.

Required scope: canonical Silesia; the latest complete English Wikipedia
pages/articles XML dump; all 28 NNLCB definitions and 19 metrics; deterministic
synthetic size series through 10 GiB. Required local compressors: gzip, bzip2,
Zstandard, XZ/LZMA2, Brotli, ZPAQ, paq8px and CIX.

Authoritative external material is under `sources/`, with retrieval hashes.
No unpublished, unmeasured or nonexact value may be presented as a completed
NNLCB-compatible result. Published third-party times and local times belong in
separate tables. Missing datasets and failed/resource-limited runs remain visible.

The advertised NNLCB `results.xlsx` at pinned upstream commit
`91eeea5094a49bd1e60fa9ee4bf3a8e50891da63` contains placeholders rather than
the numeric benchmark. Reference imports therefore use the upstream README
aggregate table and the official paper's supplementary PDF tables.

Large reacquirable inputs belong outside Git. Acquisition logs, commands,
SHA-256 digests, generator definitions and measured results belong in Git.
Do not publish a Wikipedia compression headline before actual full-input
measurements and independent reconstruction exist.
