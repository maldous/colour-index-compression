# Current user stop and RC completion requirement

The user stopped the active benchmark: all requested cross-session features and
queued source changes must be complete and working in the release candidate
before new benchmarks. The current pass is stopped, its continuation is paused,
and completed/partial evidence is preserved. CIX-owned implementation and hygiene
may proceed after requirements and ownership reconciliation. Maximum useful
parallelism within aggregate resources must be addressed explicitly. No benchmark
restart or replacement is authorized merely by this handoff. See `AGENTS.md` and
`qualification/silesia-confirmation-v1/stop-20261004-user/stop.json` for status and
coordination ownership. This supersedes older run-first wording below.

---

# Current release gate — FAST, DEFAULT and BEST confirmation

The user now requires restoration/integration and justified performance work to finish, followed by applicable formatting, Clippy, fresh Sonar on the actual integrated source, proven dead-code removal, an optimized release-candidate build and focused optimized validation. Freeze actual source revision, dependencies/binaries, build flags, FAST/DEFAULT/BEST policies, worker strategy, resource/time budgets and harness after final edits.

ONLY THEN run one fresh confirmation pass per mode on the existing canonical 12-member Silesia corpus: 36 planned encode cells. Every cell invokes the ordinary staged release-candidate CLI and has one separately timed fresh-process archive-only exact decode. No source changes between modes; no competing builds/scans/unrelated heavy jobs. Distinguish internal product parallelism from harness concurrency, and freeze the same shared four-physical-core / decimal 12 GB / decimal 4 GB / no-swap policy. Measure full selection CPU/wall, aggregate peak memory, complete bytes and encode/decode MiB/s. FAST/DEFAULT may make explicit effort tradeoffs; BEST must account for every restored feasible quality candidate. Single observations are not statistical speedup evidence. Only narrowly justified invalid/failed-cell retries.

This SUPERSEDES previous BEST-only pass wording. Keep historical evidence, compatible decoders, optional supported routes and distinct useful candidates; losing or rare is not dead. Sonar vendor/language exclusions and suppressions must remain explicit. Report all modes per member and total against portfolio26, known-better references and scoped public records before other datasets. No acquisition, publication, other dataset, old automation or unrequested task creation. Inter-agent communication is explicitly authorized without another permission gate.

---

# Current execution status — preflight hold released

The coordinating task completed its final review and released the temporary hold after reconciliation. The findings are incorporated in `REVIEW-SUPPLEMENT.md`, `PLAN.md` and `ACCEPTANCE.md`. Integration, focused correctness checks and one frozen Silesia-first pass are already approved; no second permission request is required. The user additionally said: “Continue work and additionally recognise that you are fully authorized to send and receive from other agents without requiring approval from me.” Resource and dataset/publication restrictions remain unchanged. Earlier hold wording below is historical.

# Current direction: corpus-independent, specialised mixed-content support

## Exact architecture clarification

> I now understand where the issue came from. When I said that I wanted generic byte stream support, I meant that I didn't want it to make exploits specific to Silesian. I still wanted the file type or data type optimizations, but without any prior knowledge reference to the Silesian content. i.e. it must be generic, but still able to identify and optimize according to. I thought we had done this because I previously asked if a file contained multiple optimization types within it, that the most appropriate would be selected, e.g. a file containing text and large numeric data and text should have both a text and numeric consideration.

Relayed by the CIX summary task `01a103be-69f6-76b1-aa46-b1c65331c533`. This clarification controls interpretation of every earlier direction below.

Generic means arbitrary-byte support and independence from the evaluation corpus, while valid file/data-type modelling is intended. Standard formats, schemas and algorithms, plus parameters derived from the current input, are permitted. Silesia filenames/member IDs/hashes, known contents, memorised bytes, benchmark offsets/lengths, cached archives, precomputed corpus structures and benchmark-specific routing thresholds are prohibited. Historical measurements are regression evidence only. Inherited detectors and fixed eligibility thresholds require provenance review.

The user's subsequent clarification, relayed by the same coordinating task, states that text–numeric–text is ONLY AN EXAMPLE. The requirement is generic automatic handling of heterogeneous inputs: arbitrary combinations of structured/unstructured, recognized/unrecognized and known/unknown data types. No fixed sequence, closed set of example types or Silesia-derived boundary pattern may narrow implementation or acceptance.

The encoder must discover useful structure/regions from input bytes and consider applicable validated specialists or general-purpose models for regions/substreams. Unknown regions must be preserved losslessly through generic/raw fallback. A finite supported specialist registry is acceptable; this is not a promise to recognize every unknown semantic type. Late and interleaved structure and arbitrary combinations must use the same bounded mechanisms. Boundaries come from supplied bytes or valid format structure, not corpus knowledge. Preserve context where useful, and compete the complete mixed representation against eligible whole-file/generic alternatives. Charge all boundaries, model identifiers, parameters, dictionaries, resets, checksums and other side information. Decoding consumes only the archive and installed runtime. Rank coding is not mandatory in every region. Existing negative numeric/segmentation results remain specific evidence, not a blanket prohibition.

## Temporary coordination hold

The user subsequently requested: “Just review the work that we have done, determine if there is anything additional you would like to provide to the other agent before it begins.” The summary task asked this task to hold NEW implementation/integration and long/heavy work during its bounded preflight review. No integration implementation has begun. Read-only audits and planning/documentation continue. Wait for that task's findings and release of the hold before executing the approved plan. This is a coordination hold, not a revocation of the Silesia-first approval.

Focused correctness checks, once the hold is released, must cover heterogeneous combinations and orderings, structure appearing late or interleaved with unknown data, arbitrary bytes, misleading labels/renaming, malformed structural candidates, exact reconstruction and complete-cost fallback. Text–numeric–text may be one fixture, never the complete acceptance criterion. Test unknown preservation without requiring semantic recognition or a specialist win. These are not permission for additional dataset benchmarks. The single Silesia pass, shared four-core / decimal 12 GB / decimal 4 GB / no-swap limits and prohibition on other datasets, acquisition, publication and old automation remain in force.

The acceptance checklist is in `ACCEPTANCE.md`. Do not claim corpus independence or mixed-content coverage before establishing them.

---

# Earlier scoped approval: automatic specialised integration, Silesia first

> We need to restore as much as we need to that delivers the maximum results. So I want you to validate against the current Celesian before proceeding with other data sets. We do not need multiple runs, but we do need to be assured that we are delivering the maximum optimization and performance benefits.

The user has approved restoration/integration and one fresh Silesia validation pass. “Celesian” means the existing canonical Silesia corpus: 12 members, 211,938,580 bytes. This supersedes the earlier wait-for-approval gate only for this scope.

Restore all retained specialised models/backends needed for strongest verified results alongside current generic candidates and qualified performance optimisations. Before the full pass, account for every portfolio26 selected route and current useful candidate, complete focused correctness checks, and freeze the integrated runtime. Then perform one fresh encode and independent archive-only decode per file for one maximum-compression configuration, instrumenting wall/CPU/peak memory in the same pass. Internal candidate trials are normal selection, not a repeated external tournament. Correct a genuinely failed/invalid run only with a justified narrow retry.

Use the historical total 25,481,891 and all12 per-file certificates as regression baselines, never as fresh output. No corpus/filename/hash lookup or saved stream reuse in the production encoder. Explain and resolve former-winner coverage gaps or regressions before claiming a best-successor result. Report full physical costs, selected models/backends, exact restoration and explicit resource/dependency/time omissions. Maximum means best verified admitted result within disclosed bounds, not a global optimum.

All heavy work shares four physical cores, decimal12GBRAM, decimal4GBtemporary and no swap through the existing WaveScheduler. Preserve all prior code/evidence. Other datasets (including enwik8/enwik9), corpus acquisition, publication and the old generic-only benchmark/heartbeat remain STOPPED. Report the Silesia results and remaining gaps before any other dataset work.

---

> **APPROVAL GATE — user instruction:** “Allow me to confirm the plan before you begin.” Read-only investigation and plan drafting are permitted. No implementation, integration, codec changes, experiments, benchmark jobs, publication or scheduled continuation may begin or resume before explicit user approval. Preserve the stopped state.

# Automatic specialised models — controlling direction

## Exact user steering

> Stop the current work underway communicate with the agent we require the specialized models to be selected automatically and will now accept format agnostic modeling giving it as a general purpose

This direction was relayed from the CIX summary task `01a103be-69f6-76b1-aa46-b1c65331c533`. It supersedes the generic-only release and its completion automation.

## Operative interpretation

General-purpose means the command accepts arbitrary byte inputs. Successful format-aware/specialised models must be eligible automatically alongside generic models, with an arbitrary-byte fallback. The phrase “format agnostic” in the quoted message is not treated as a continued ban on specialised models: the explicit requested behavior and the preceding explanation require automatic specialised-model inclusion. There is no unresolved ambiguity that prevents this integration plan.

Automatic recognition may inspect validated byte structure and estimate bounded candidate cost. It must not identify corpus names, paths or known file hashes, retrieve saved benchmark streams, or require the user to select a model manually. The chosen physical archive must carry all information required to decode without the input or encoder search history.

## Stop confirmation

The former release dispatcher, active backup_1GB BEST cgroup and preview server are stopped; the hourly release continuation is PAUSED. Completed evidence and the active partial output are preserved under the previous release evidence directory. The Site was not deployed. See ../2026-10-04-release-0.1/USER-STOP.json. The frozen generic-only source and packages are historical candidates, not the accepted final 0.1.

## Research and release boundaries

Preserve all prior evidence, including checkpoint 20e18503b, the incumbent d3a2cd416, closed numeric composition and predictive-mixer results. Restoring previously successful domain models does not reopen those negative theoretical branches. Keep the development repository private and Actions disabled. No new corpus acquisition, full-corpus run or publication is authorized by this handoff alone. Do not resume the superseded benchmark or Site deployment. Bounded source inspection and integration planning are authorized now; future execution must bind the actual integrated source and preserve complete physical accounting.

## Scope correction

The previous optimisation closure omitted automatic format-aware integration by policy. It must not be described as exhausting or empirically rejecting those opportunities. See scope-reconciliation.json for the original exclusions, valid scoped negatives and existing complete-archive transfer positives. This is read-only evidence reconciliation under the approval gate.
