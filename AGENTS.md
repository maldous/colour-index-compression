# CIX local research

- Run all tests, profiling, algorithm tournaments and corpus benchmarks locally.
  Do not trigger, dispatch, rerun or otherwise consume GitHub Actions. Do not
  create or modify workflow files to start CI. Source pushes must not trigger CI.
- Preserve universal, reversible byte-only modelling. Never select or tune using
  filenames, formats, MIME, corpus identity, language or ISA. Benchmark labels
  belong in reports, never encoder input or model selection.
- Select by complete physical bytes, including selectors, metadata, framing and
  checksums. Verify exact restoration before accepting any size result. Keep
  incumbents in the portfolio; measure CPU as well as size.
- Evidence order: Canterbury + Calgary + Artificial; Silesia; Canterbury Large;
  enwik8; enwik9; Pizza & Chili Repetitive; frozen modern CIX corpus. Prefix probes
  and generated tournaments are diagnostic, never complete-corpus scores.
- Calgary's current official comparison set has 14 members. The archive also
  includes paper3 through paper6; report those only as supplemental evidence.
  Report Artificial and Large per member, without aggregate leaderboard claims.
- Use `.venv/bin/python`; set `OMP_NUM_THREADS=1` for small BWT jobs and bounded
  local process parallelism. Run tests with `-m pytest -q --timeout=45`.
- Freeze source and settings for paired comparisons. Record corpus hashes,
  complete byte counts, encode/decode times, round trips and failures. Do not
  promote a prefix result or project a missing leaderboard rank.
- Consult `docs/research/` for the last verified checkpoint and remaining work.
