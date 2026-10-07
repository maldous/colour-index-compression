# Final independent evidence review — latent layout

Read-only review of the consolidated latent-layout report, synthetic and real
results/metrics, attribution evidence, freeze records, mechanism inverses,
malformed receipts, raw hashes, and source boundaries. No build, codec, test,
or archive operation was run.

## Verdict

**PASS — no evidence blocker found.** The report's counts, complete sizes,
restoration claims, resource rows, scope limits, and attribution are supported
by the inspected records.

## Physical evidence and counts

| Group | Verified physical archives / cells |
|---|---:|
| latent synthetic compression trials | 169 |
| frozen real-prefix compression trials | 40 |
| prior matched-attribution trials | 59 |
| consolidated compression-trial total | 268 |
| constructed raw-lane mechanism inverse archives | 1,344 |
| malformed/CLI/semantic rejection cases | 20 |

All 169 synthetic archive hashes under `benchmark-work/latent-layout/archives`
and all 40 real archive hashes under the real evidence archive path match their
recorded SHA-256 values. The 59 attribution archives were independently
verified in the preceding attribution review. All 1,344 mechanism archive
hashes match `mechanism-inverses.json`; every record reports exit 0. The 20
malformed cases each report the expected rejecting exit 1.

For result candidates, every stored restored SHA-256 equals its fixture input
SHA-256 and every candidate's recorded complete size reconciles to its stored
accounting. The totals above are experiment-accounting totals, not an aggregate
compression score, average, or ranking.

## Freeze, source, and resource checks

The synthetic freeze binds parent `f105a85fbedf212ea8745a7af58eb712669d71b5`,
the experimental source hash
`8611d8ef10279025d4b878d0340358b6b4c50f7317a15e63a08d55ace19e52b8`,
the current `/usr/include/zstd.h` FFI header hash, the sealed library/toolchain
hashes, and the bounded-runner hash. Current hashes of the experimental source,
FFI header, runner, and frozen layout binary match their receipts. The real
screen freeze binds the same experimental source and layout binary. `git diff
--quiet d3a2cd416e49f93403d1dbd348a3e9a45db66ec6 -- cix rust/cix-native/src`
returns success; the work is confined to the experimental source path.

Metrics contain all 169 synthetic and all 40 real cells, with encode/decode
wall/CPU/RSS entries. Their batch receipts match the report: synthetic
52.555 s wall / 51.113 s CPU, real 129.868 s wall / 129.275 s CPU, and the
reported sampled cgroup memory and temporary-space observations. The real
table's auto/CIX BEST size, wall/CPU (user plus system), and RSS values match
the per-cell metrics. These are single local observations and the report does
not convert them into averages or imported performance ranks.

## Results and attribution checks

The real-prefix size table matches `real-evidence/results.json`.

* Numeric auto is 1,357 B: 20 B below bzip2's 1,377 B and 280 B below its
  same-container ordinary mask, while incumbent CIX BEST is 1,231 B, a 126 B
  smaller archive.
* Text, binary, and compressed prefixes all lose to their current strongest
  declared controls, including CIX BEST. The binary result is a 41 B LLT
  container against a 22 B Zstd/CIX BEST control and is correctly retained as
  a paid-wrapper loss.
* Synthetic results retain the ordinary-control explanations. The only stated
  beyond-control result is changing-correlation at 463 B versus 465 B; it is
  not generalized beyond the bounded synthetic bank.
* Backend-aware rows are presented as packaging/context outcomes. Their ties
  are explicitly not called transform advantages or positive model evidence.
* The tiny oracle's zero observed regret is explicitly limited: raw wins at
  these tiny lengths, making the result weak evidence about useful
  larger-structure shortlist adequacy.

The report correctly separates the 59-cell matched Zstd attribution matrix:
the 113/156/206 B native-to-Zstd differences remain split into
90/124/165 B payload/backend and 23/32/41 B outer framing. It does not claim
the backend portion as native modelling.

## Scope and next action

The consolidated report denies aggregate score claims, new compression theory,
schema recovery, arbitrary-length streaming, incremental deployment, and
production promotion. It labels the synthetic bank as generator-family evidence
and the real inputs as fixed 4,096-byte prefixes, not full corpus or broad
real-data qualification. It also keeps the next action as a single queued
CIXM6 numeric-layout ablation; no receipt or result claims that this ablation
has executed.
