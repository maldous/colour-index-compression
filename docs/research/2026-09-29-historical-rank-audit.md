# Historical CIX rank audit

The user asked whether an earlier #1 result, or a Silesia result better than
24th, had been lost during a rework.

**Finding:** no earlier verified full-Silesia result better than 24th was found
in the available evidence. There was an architectural rework, but no retained
winning Silesia measurement associated with the removed implementation.

## Scope checked

- All 572 reachable source commits, including every local branch and 36
  `origin` refs (including the symbolic HEAD). The authenticated read-only fetch
  completed without adding commits. No GitHub Actions or remote writes used.
- Every historical version of the relevant committed documentation and result
  text: 292 unique Markdown/JSON/text/CSV/HTML blobs. All commit subjects,
  deletion history and local reflogs were also inspected. `git fsck` reported
  no unreachable history to recover.
- All 42 Site commits, from its creation through `c7d3840`.
- The available local conversation record from 2026-09-28 onward, including
  assistant final answers and progress messages. It contains no earlier #1
  claim. The saved memory files, rollout summaries and their Git history have
  no CIX/Silesia entry. The context-trace search service is uninitialized.
- Existing complete benchmark artifacts. Before the new result described below,
  the best complete portfolio was 19 at 31,175,135 bytes.

This does not establish what an unavailable earlier mobile conversation may
have claimed. Its complete transcript and its old `/mnt/data/cix-local` runtime
are not present here; the pasted mobile notes contain small generated probes,
not a complete independently measured Silesia total.

## What really was reworked

- `f685e3e` (26 September), “Restore known baseline and park workflows,” removed
  benchmark automation and a metrics harness. Its diff did not revert a codec.
- `96d296a` / `3f78e1e` (27 September) changed the stated architecture from an
  expert portfolio to a universal, format-agnostic codec. Subsequent commits
  removed content-specific code: `985b2ff` removed `cix/tokens.py` and `2cf73ba`
  removed `cix/raster.py`; related probes/tests were removed too. Those sources
  remain recoverable from Git. No full-Silesia #1 measurement accompanies them.
- `76d783b` (28 September) restored the competitive scope, allowing PAQ-backed
  ensembles and format-specific modelling. Current structural/PAQ results use
  this expanded scope.
- Early `benchmarks/expert_portfolio.py` measured Canterbury and charged an
  estimated 24-byte frame overhead. Such a result is neither a full Silesia
  run nor a historical physical Silesia #1 result.

## Retained complete milestones

| Result | Physical Silesia bytes | Equivalent position | Evidence commit |
| --- | ---: | ---: | --- |
| Original CIXM6 | 57,321,752 | 201 | `eacb96f` |
| Bounded PPM | 54,535,913 | 195 | `6bad1fd` |
| Joint portfolio | 52,036,355 | 172 | `555b552` |
| Competitive spatial portfolio | 50,770,960 | 159 | Site `1f0ab7a` |
| PAQ / structural portfolio | 39,607,610 | 66 | Site `4825864` |
| Executable structural portfolio | 36,937,786 | 54 | Site `07022c4` |
| Shared procedure/symbol portfolio | 32,659,222 | 25 | Site `66a80ac` |
| Filtered portfolio 19 | 31,175,135 | 24 | Site `a04ebba` |

The Site records intermediate improvements at 135th, 124th and 84th as well.
It contains no prior rank better than 24th. A selected-family comparison table
is a different comparison from insertion among all 322 published configurations.

## New result discovered during this audit

The pending native PAQ8px v216 `-8` Mozilla run finished independent restoration
at **2026-09-29 00:16:01 UTC**, after this user question. The 6,477,226-byte
archive restores the exact 51,220,480-byte canonical member. Qualification into
the existing portfolio replaces its 11,249,835-byte Mozilla stream; the other
eleven verified streams are unchanged.

Portfolio 20 totals **26,402,526 physical bytes**, **1,422,985 bytes below** the
live published leader's 27,825,511 bytes. Its equivalent numerical position is
**1**, verified against a fresh leaderboard read. This is a newly completed
result, not a recovered older win. It is a PAQ-backed heterogeneous CIX portfolio;
it does not establish standalone combinatorial coding superiority.

All twelve physical artifacts, source/backend identities and independent full
restoration evidence were checked. See
`2026-09-29-competitive-large-paq-milestone.json` and
`results/leaderboard/competitive-large-paq-v20/complete.json`.
Public source release and an official leaderboard listing remain pending.
