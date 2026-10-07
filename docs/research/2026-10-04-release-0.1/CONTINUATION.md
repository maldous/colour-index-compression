# CIX 0.1 autonomous completion handoff

The user explicitly authorized parallel research, source/release cleanup,
professional distribution artifacts, measurements over all valid local data,
and an owner-private Sites portal, completed without routine prompts. This is
still active work. Do not describe the benchmark or private deployment as
complete before checking their actual receipts.

## Scope and invariants

- Preserve the composition checkpoint `20e18503b` and incumbent `d3a2cd416`.
  The numeric structural-composition and predictive-mixer branches are closed.
  Do not reopen research or infer a universal compression limit.
- Keep the development repository private and Actions disabled. Do not create
  the eventual public GitHub repository. No corpus acquisition.
- Root alone schedules heavy jobs, commits, and pushes. Use this directory's
  `schedule.py` and the shared WaveScheduler. Aggregate limits: four physical
  cores, decimal 12 GB memory, decimal 4 GB temporary storage, no swap. Final
  benchmark cells use CPUs 8,10,12,14 and 10 GiB memory within those limits.
- Never duplicate an active timing cell or rerun a successful cell for a better
  timing. Preserve failed attempts and explicit unranked results.
- Do not stage the repository broadly: extensive unrelated historic dirty and
  untracked research exists. Stage only completed files owned by this release.

## Paths and frozen artifacts

Repository: `/home/user/src/colour-index-compression`, branch
`research/silesia-competitive`. This file's directory is called AREA below.

- Frozen measured binaries: `/home/user/src/cix-0.1-artifacts/final/bin`.
  `release-binary-freeze-final.json` records all hashes. Never rebuild, strip,
  or replace these while the final measurements run.
- Frozen measured source: `/home/user/src/cix-0.1-release`.
  Source manifest hash
  `bd28975a504abbeb011d2aaba36224af6b5c7f3fa844f491c224166750cab1e7`.
  Its incidental `target/` is excluded by the original tree manifest and source
  packager. Do not edit or remove frozen content.
- Shipping successor source: `/home/user/src/cix-0.1-distribution`.
  It adds Rust dependency notices and their install rules only. See
  `dependency-notices/amendment.json`: six changed documentation/packaging
  paths, 90 protected runtime/build files byte-identical. This amendment must
  be carried in the release manifest; it does not require repeating unchanged
  binary measurements.
- Shipping successor packages:
  `/home/user/src/cix-0.1-artifacts/distribution-v2/packages`.
  Use only after `notice-qualification-results-v2.json` and
  `raw/notice-qualification-v2/result.json` prove success.
- Historical pre-notice packages remain under `.../final/packages`; older
  pre-prune packages remain under `.../packages` and `.../packages-v2`.
  Preserve them, but do not present them as the shipping package after the
  documentation amendment passes.

## Current processes and next operations

The documentation amendment is COMPLETE: notice qualification v2 passed all
package/source-build/install/uninstall/notice-hash checks and the outer cgroup
receipt (34.53 seconds). V1's generated RPM spec omitted an install line; its
failure, partial packages and original harness copies are preserved. V2 fixes
only that private packaging harness issue. Binaries and export runtime code are
unchanged. Shipping packages are under `distribution-v2/packages`.

The final benchmark dispatcher PID 404708 was SIGCONTed after the package job
finished. It is now RUNNING. The intentional between-cell pause and resumption
are in `distribution-notices-pause.json`; no timing child was interrupted.
At this checkpoint 14 of 267 cells are verified, with zero failures.

Next operations:

1. Inspect actual task process and latest terminal receipts. Leave a healthy
   active queue alone; no duplicate run or publication while rows are pending.
2. Refresh tables/local portal only when useful with `python3 refresh_site.py`.
   It now selects qualified successor packages and both measured and amended
   source identities. Its last 37 local links checked with no missing files.
3. Resolve an actual terminal failure if one occurs, preserving all evidence.
4. Once all frozen cells are terminal, produce final terminal manifest/tables,
   update the report, checkpoint privately, and deploy the owner-private Site.

The final benchmark exec session is 46975. Do not assume these PIDs/sessions
remain valid: inspect task-owned process command lines before any signal. The
original dispatch command from repository root is:

```sh
python3 docs/research/2026-10-04-release-0.1/benchmark_driver.py run \
  --area /home/user/src/colour-index-compression/docs/research/2026-10-04-release-0.1/distribution-benchmark-final \
  --release-root /home/user/src/cix-0.1-artifacts/final/bin \
  --source-export /home/user/src/cix-0.1-release
```

Only resume this command if no dispatcher/active cell exists, source/binary/DSO
bindings still match, and all existing cell directories have inspected terminal
receipts. It skips valid terminal cells. An incomplete cell directory requires
inspection of its raw scheduler receipt; do not delete it or silently rerun.

The plan has 267 actual cells for 89 physical inputs / 90 logical corpus members.
The Canterbury/Calgary/Artificial gate comes first. All these gate cells must
verify before later datasets run. A resource-limited gate stops progression;
resolve a demonstrable protocol defect under a new identity or report the
explicit limit, never silently bypass the gate. Correctness failures stop work.

FAST/DEFAULT use their shipped defaults, BEST uses `--best`, all use `--threads
4 -f`. No memory override or constrained substitute. Fixed outer budgets scale
to 1800 seconds FAST/DEFAULT and 7200 seconds BEST; small BEST has at least 1800
seconds, above its native 900-second allowance. Budgets include fresh decoding.
Archives are hashed and deleted after fresh stdout restoration hashing, leaving
receipts rather than corpus bytes. See `benchmark_driver.py` and frozen plan.

The initial `distribution-benchmark-v1` incorrectly capped small BEST at 300
seconds. Its two timeouts and `STOP-REASON.json` are preserved. The corrected
final run uses different post-prune binary hashes and identities. Never merge
the initial timing rows into the final release table.

## Summary and validation rules

`summarize_release.py` reads metadata only, so it is safe while a heavy job runs.
It ranks a child VERIFIED only with raw scheduler exit 0, cgroup_verified true,
and no stop reason. A missing outer receipt remains pending; a failed one is
unranked. This fix passed independent review and a metadata self-check.

`python3 refresh_site.py` regenerates `distribution-summary-final` plus local
Site JSON/CSV/packages/docs. It does not measure or publish. Preserve its removal
of private nested command/path diagnostics; retain minimal resource receipts.

At completion, produce a separate terminal run manifest (leave frozen plan's
PREPARED_NOT_EXECUTED field untouched): counts, statuses, input/binary/source
and harness bindings, final resource policy, summary hashes and receipt hashes.
No pending rows may be presented as finished. A resource-limited row remains
explicitly unranked; no ratio or claimed record is derived from it. Corpus totals
require every member of that profile. Artificial has no aggregate. Canterbury
ptt5 and Calgary pic share one physical measurement but both logical labels.

Public-record context is frozen in `public-records.json` and `DATASETS.md`:
Silesia paq8px v217 -12L 27,682,006 bytes (different resources); enwik9 official
fx2-cmix-T 100,424,672-byte program+self-extracting total (not archive-only
comparable); enwik8 phda9 15,242,496 archive bytes plus 42,448 decompressor is a
historical 2017 prize result. Unknown exact records remain unknown.

## Completed substantive work

- CPI1 28-expert audit: fixed-share gain 0.5747%, material gate FAIL. Oracle gap
  28.911%, labelled HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY. Null controls,
  complementarity, marginal value and residual attribution retained.
- Omitted-signal screen on 49,152 held-out bytes: FixedMix v3 loses; Bayesian
  gain only 12.57 ideal bits / 0.0090%, gate FAIL. PPM held-out reachable-byte
  mass is one, not zero; separate treatment concerns global normalization on
  other states. Physical existing-substream cost checks also lose for v3.
- `OPPORTUNITIES.md`/JSON preserve 38 historical dispositions. No new codec.
- Portable opt3/fat-LTO/CGU1 chosen. PGO, alternative LTO/ISA/allocator settings
  and block/memory configurations have finite measured dispositions. Final
  one-variable G1 controls are complete.
- Accepted release-only improvements: discarded-histogram avoidance (T1) and
  exact append-only candidate-prefix pruning. Two matched controls preserve
  selected archive hashes; no general speedup claim from one observation.
- Final runtime source: release build, 115 library + 4 CLI + 7 streaming tests,
  warnings-denied Clippy and Sonar v2 PASS; zero current Rust issues, gate OK.
  Vendored C++ is outside that Sonar scope. Decoder compatibility preserved.
- Pre-notice package qualification PASS: source build/install/uninstall,
  Debian/RPM extraction and exact binary hashes/roundtrips, DSC shape, callback
  ABI, streaming before EOF, standard Zstd SquashFS transport.
- Rust notice bundle now covers 32 locked crates and upstream texts. Shipping
  source/project MIT is still a private proposal pending owner confirmation
  before public release, not a public grant made by this task.
- Linux artifacts are host-qualified Ubuntu24.04/glibc2.39 x86_64. RPM built on
  Ubuntu does not establish Fedora/RHEL runtime compatibility. Mac/Windows
  source recipes are unqualified; no invented platform binaries.
- Standard SquashFS transport is qualified. There is no native CIX SquashFS
  kernel codec. QuixDB Squash 0.8 SDK/runtime is absent; optional plugin loader
  unqualified. `squash-plugin-review` records that boundary and a gated future
  test. Do not substitute local unbuilt Squash0.7 as 0.8 evidence.

Update `RELEASE-REPORT.md`, `PLAN.md`, and `QUALITY-CLOSURE.md` at final closure.
Keep exactly one evidence-selected next action: private candidate review of
the finished package/evidence, without reopening compression branches.

## Private Site

Owner checkout: `/home/user/src/cix-release-review-site`, plain static `dist/`.
Site project ID: `appgprj_6ac14b92a8b48191a38ab421e7a5910d`.
Registered exactly once, owner-private, NOT YET DEPLOYED. Do not register again,
change audience, touch the older cix-benchmark-site or present the expected URL
as live. No public GitHub link exists.

The portal has responsive light/dark themes, original SVG architecture/oracle
graphics, dataset/profile/search/sort controls, complete-size percentages,
wall/CPU/RSS evidence, record-scope columns, downloads, source docs/manuals,
platform/SquashFS limits. Local QA passed mobile no-horizontal-page overflow,
themes, command copy, filters, external record labels and no JS errors. Temporary
viewport was reset. In-app browser tab2 is the local preview on port8871; use CUA
only for UI and restore its documentation after compaction. Do not publish until
the final data is ready. Packaging-only notices must be copied into downloads.

For deployment, read Sites hosting skill and use its workflow exactly:
`/home/user/.codex/plugins/cache/openai-curated-remote/sites/0.1.75/skills/sites-hosting/SKILL.md`.
Obtain a fresh native source repository write credential for the existing
project ID, keep it in session memory only, run bundled `site-workflow.mjs`
with tty, feed hidden JSON stdin including credential and archivePath, retain
verified commit/archive, then call native `sites_save_version_and_deploy_private`.
Poll native deployment status to succeeded with URL. Do not fetch/navigate the
deployed URL merely to verify publishing. Open it for the user with
`open_in_codex`, return the literal successful URL. No further permission is
needed for this expressly authorized private deployment.

## Private checkpoint / heartbeat

Last pushed checkpoint when writing:
`f8dddd802ea3cd59a2ad81e0a9be63ab8217d7c2`.
Before each push verify with `gh api` repository `maldous/colour-index-compression`
has `.private == true` and Actions permissions `.enabled == false`.
Default Git credentials fail here; push using:
`git -c credential.helper='!gh auth git-credential' push origin research/silesia-competitive`.
Verify remote SHA after push. Stage completed own evidence only, exclude active
cell trees, corpus/archive bytes, tokens, pycache, and unrelated changes.
The successor source archive is backed up at
`source-candidate/docs-amended/cix-0.1.0.tar.gz`; preserve the historical archive.
`site-candidate/` backs up authored portal files without its generated downloads.

An hourly task heartbeat is ACTIVE:
`complete-cix-0-1-release-qualification`, attached to this task. It exists to
finish this finite authorized job, not to create ongoing research. Healthy
unchanged queue checks stay quiet. When all deliverables and private deployment
are complete, provide final links and pause the heartbeat using the native
automation tool, preserving its other fields. Inspect its TOML for the full
saved configuration when updating. Do not archive the user task.
