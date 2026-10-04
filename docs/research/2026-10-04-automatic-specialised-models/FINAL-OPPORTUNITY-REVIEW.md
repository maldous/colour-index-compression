# Final opportunity review — evidence boundary

**Review date:** 2026-10-04  
**Method:** bounded read-only review of retained research, release qualification,
historical certificates and the frozen integrated-Silesia direction. No codec,
build, scan, benchmark or corpus operation was run for this review.

## What this review can conclude

The retained evidence supports a finite release decision, not a universal claim.
It establishes which tested mechanisms failed their declared gates, which
previously policy-excluded specialised candidates must be considered in the
integrated candidate, and which resource/platform qualifications remain. It
cannot prove an entropy limit, a Kolmogorov limit, that every conceivable
lossless compressor has been considered, or that the frozen candidate is the
smallest possible archive.

The qualified product source revision is `5d93d9f1b`; its source/policy freeze
is recorded by commit `d026ee070`. The earlier generic
release closure, commit `f8dddd802`, remains valid only for its declared
generic/native-prediction scope. Automatic specialised admission corrects that
scope: format-aware, input-derived candidates were policy-excluded, not
empirically rejected. See [DIRECTIVE.md](DIRECTIVE.md), [PLAN.md](PLAN.md),
and [scope-reconciliation.json](scope-reconciliation.json).

## Compression evidence already closed

| Area | Evidence-supported result | Release implication |
| --- | --- | --- |
| Numeric structural composition | The fresh composition result at `20e18503b` saved 4 internal payload bytes but added 29 description bytes; the incumbent was 1,393 B versus 1,418 B. | Closed. Do not reopen numeric M6 composition, latent-layout composition, or equivalent description-cost variants. [Release report](../2026-10-04-release-0.1/RELEASE-REPORT.md). |
| Lanes, selective transforms, segmentation, history, exceptions and constraints | Synthetic/local wins did not survive stronger controls or frozen real-prefix qualification. Constraint/rank behaviour is established coding theory, not a demonstrated new CIX gain. | Scoped negative evidence, not a ban on input-derived supported-format candidates. [Opportunity ledger](../2026-10-04-release-0.1/OPPORTUNITIES.md). |
| Predictive mixture, CPI1 | The 28-expert pool did not meet its causal held-out gate. The hindsight oracle was large, but selects after seeing the byte. Duplicate, smoothing and noisy controls show oracle selection/calibration effects are not a codec opportunity. | **HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY.** No selector, route side channel, or neural mixer follows from it. [CPI1 report](../2026-10-04-predictive-information/REPORT.md), [null controls](../2026-10-04-predictive-information/null-controls.json), and [prior art](../2026-10-04-predictive-information/PRIOR-ART.md). |
| Corrected predictive follow-up | `RELEASE-PREDICTIVE-1` tested 49,152 held-out bytes. FixedMix v1 was best at 139,280.337288 ideal bits. Bayesian mixing improved it by 0.000256 bit/B, below the >0.05 bit/B and >1% gates. Recurrence-v3 N1/N2 lost by 0.006298/0.006361 bit/B. | Closed for v0.1. There is no physical mixed codec because the causal signal is immaterial before framing and finite precision. [Predictive results](../2026-10-04-release-0.1/PREDICTION-RESULTS.md). |
| PPM probability exposure | Raw and normalized held-out coding-path diagnostics both measure 155,099.386741 ideal bits; valid-mass correction is approximately zero on that range. CPI1 showed subprobability on other reachable states. | PPM remains separate until a decoder-compatible outcome-space contract exists. This does not say PPM cannot compress. [Release report](../2026-10-04-release-0.1/RELEASE-REPORT.md). |
| New generic coder/parser proposals | LZ-lazy, BWT-local, LZW/XPRESS, rANS/FSE, count headers and integer variants remain bounded unmeasured cells, not positive results. Some require a new frame or paid complete-frame comparison. | Not v0.1 candidates without qualified gain and compatibility protocol. This is finite consideration, not exhausted theory. [Opportunity ledger](../2026-10-04-release-0.1/OPPORTUNITIES.md). |

## Hindsight-oracle consequence review

The reviewed oracle experiments did not establish a material causal win. Their per-symbol choice
depends on the target byte, unavailable to a decoder assigning coding
probabilities. Its controls matter: redundancy, smoothing and perturbed
forecasts can create apparent oracle gaps without new causal information.
Neither the gap nor a post-hoc model-winner map identifies recoverable bytes.

The original CPI1 review identified only corrected recurrence-v3 and PPM's
outcome-space ambiguity as consequential omissions. `RELEASE-PREDICTIVE-1`
subsequently addressed both: v3 loses to v1 and PPM has no held-out
normalization gain. This closes the released predictive set without asserting
that every predictor has been invented or measured.

## Valid remaining compression opportunity: automatic specialised admission

The remaining opportunity is the corrected product scope: automatically select
complete, self-decoding, input-derived specialist and generic candidates under
the same physical-cost comparison. Its evidence is historical and
candidate-specific; it becomes current only after confirmation.

* Portfolio26 is a 25,481,891-B historical 12-member regression baseline with
  certificates, not a fresh result. [Regression baseline](regression-baseline.md).
* Dickens has a provenance-recorded PAQ v215 `-9L` archive of 1,862,182 B,
  40,163 B below its portfolio member. Its prior exclusion was an input-size
  bucket, not input-schema logic. It must be completed or explicitly omitted
  under the current resource policy.
* MR has a 1,671,099-B CIXI result, 2 B below the portfolio CIXV envelope,
  with recorded identical JPEG XL payload. This is a framing candidate, not a
  separate modelling gain; payload sharing is valid only when current bytes and
  options establish equivalence.
* Webster PAQ `-12L` is 32,514 B below the portfolio member but its recorded
  22.8–23.6 million KiB RSS exceeds the frozen decimal-12-GB/no-swap bound. It
  remains a resource-excluded reference.

[Known-better candidates](known-better-candidates.md) records the provenance.
These results must not be summed into a hypothetical total or called a public
record.

## Throughput and implementation opportunity review

Two source-level improvements have adequate exactness evidence: T1 avoids an
M6 histogram scan that would be discarded, and the native append-only prefix
rule stops only after an irreversible serialized prefix exceeds the strict
incumbent. Equality still completes. The portable B0 build remains selected;
single-observation PGO/ThinLTO/host-native differences and jemalloc do not
support a portable release change. The bounded M6 screen timed out and is
unranked, not negative evidence.

[Performance results](../2026-10-04-release-0.1/PERFORMANCE-RESULTS.md) and
[performance carry-forward](performance-carry-forward.md) define the scope.
Existing timings do not establish a general speedup or parallel decode.

## Remaining qualifications and trade-offs

1. **Silesia confirmation.** Run one fresh encode and independent archive-only
   decode for each FAST, DEFAULT and BEST mode across the canonical 12 members:
   36 cells, four physical cores, decimal 12 GB RAM, decimal 4 GB temporary
   storage and no swap. Record full selection CPU/wall, peak memory, bytes,
   candidate coverage, decode timing and exact restoration.
2. **Runtime safety and portability.** Each admitted archive needs a decoder and
   bounded expansion/resource enforcement. Python/imagecodecs/JXL and external
   PAQ paths carry platform packaging and resource implications; estimates are
   not enforcement. [Runtime review](runtime-review.md) and
   [runtime dependencies](runtime-dependencies.md).
3. **Corpus independence.** Recognition, boundaries and admission must come
   from input bytes or validated standard format structure. No filenames,
   hashes, saved archives, member offsets or benchmark buckets may select a
   route. Unsupported structure must safely fall back. [Acceptance](ACCEPTANCE.md).
4. **Heterogeneous input.** The finite registry must preserve unknown bytes and
   compete complete mixed output with whole-file generic candidates. It does not
   promise universal semantic recognition. [Mixed-content audit](mixed-content-audit.md).
5. **Public comparison.** Later public material must distinguish historical
   baselines, current results, resource-excluded references and incomparable
   public records. No rank may be inferred from unlike archive rules.

## Decision

There is no evidence-supported reason to reopen a closed compression branch or
add a codec/mixer before confirmation. The sole evidence-selected next step is
the already authorized frozen Silesia FAST/DEFAULT/BEST confirmation with
independent decode. It will determine whether automatic specialist admission
has a measurable current improvement within disclosed resource and portability
bounds; it cannot establish a universal compression limit.
