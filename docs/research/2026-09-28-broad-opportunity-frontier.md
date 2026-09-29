# Broad compression research frontier

Latest explicit user directive: consider all opportunities for substantial
changes in compression and all techniques needed to win Silesia. This broadens
the earlier focused PAQ/CIX hypothesis; that hypothesis remains an active branch,
not a restriction on architecture. Only local computation; no GitHub Actions.

The complete qualified baseline remains portfolio19: 31,175,135 physical bytes.
The live leaderboard was read again at 23:49Z on September28; the leader remains
27,825,511 bytes. Mozilla contributes a 5,155,241-byte deficit versus the leader's
author-reported member value. Existing completed advantages on SAO, NCI, OSDB
and MRI partly offset that deficit. No pending archive contributes to the score.

## Opportunity map and first discriminating tests

| Family | Mechanism worth testing | Evidence / next gate |
| --- | --- | --- |
| Program structure and cross-object reuse | Predict relocations, symbol identities, instructions and shared function structure, then encode exceptions | Highest immediate priority. Full native PAQ, field, shared-symbol, pointer and section trials already running; discounted joint model now has its own full trial. Qualify whichever complete result wins first. |
| Model induction | Replace mathematical or generated sequences with a transmitted rule, initial state and exact exceptions | Initial OSDB scan checks direct affine recurrences and field relations. A simple visible-state LCG is unsupported; hidden-state and permutation-generating models remain open. Model description costs must be counted. |
| Multiscale image and volume prediction | Interpolate fine samples from coarse samples in two or three dimensions; compress separate reversible residual bands | NEW full MR/X-ray tournament implemented, eight invariant/frame tests passed. Six full-frame candidates including zero-transform controls; two workers, single E core each. Generic metadata and all residuals transmitted. |
| Neural / context mixture alternatives | Online LSTM, Transformer, gated mixtures and independent learned experts; decoder repeats causal updates | Inspect CMIX and NNCP sources. Authoritative sources below. GPU is GTX1650 with4GiB total but only929MiB available at inspection, so no assumed large GPU capacity. CMIX recommends32GiB RAM; present free capacity is below that. Build/source exploration can proceed without launching a large-memory full run. |
| Grammar and token representation | Word replacement, inferred dictionaries, recursive phrase grammars, markup-aware residuals, long-distance copy-and-patch | Previous markup layouts and register-rank rewrites lost. Compare genuinely different reversible preprocessors against the same backend; CMIX's upstream dictionary/text transform is a concrete next independent candidate. |
| Numerical, scientific and relational structure | Exact quantization plus bit corrections, cross-field dependencies, bounded compositions, topology/geometry | Already material wins on SAO/NCI/OSDB. Explore remaining conditional relations rather than re-running rejected fixed columns or heavy-atom transforms unchanged. |
| Recursive containers and compressed streams | Reversible preprocessing of embedded streams, reconstruction parameters, region-aware model selection | PAQ filters are already useful. Study Precomp/CMIX transformations and their interactions; preserve original container bytes, padding and exact reconstruction side information. |
| Sorting, block and match representations | BWT/MTF, LZ parsing, long matches, block transforms and combinations with stronger prediction | Earlier generic probes exist. Revisit only when structural residuals expose a materially different distribution or a stronger predictive backend changes the comparison. |
| Exact uncertainty coding | Conditional counts, enumerative ranks, constrained walks, arithmetic/range/ANS comparisons with identical information | Earlier count and rank successes/negatives retained. Same-information rank coding has not established a general advantage over arithmetic. Use only when actual framing plus payload beats the control. |
| Portfolio and computation | Select total description length including every model, dictionary, selector and checksum; staged cheap tests before full runs | Generic recognition/physical selection, no filename or hash dispatch. Reuse unchanged complete verification only with exact identities. CPU placement and bounded concurrency preserve ongoing work. |

Research is an adaptive search, not a promise that every listed technique will
win. A screen chooses which expensive physical test is justified; it does not
create a leaderboard result. Start with multiple distinct explanations for a
large residual, reject weak ones cheaply, and measure interactions among winners.

## Primary reference sources

- https://mattmahoney.net/dc/silesia.html — complete size ranking, member identities,
  independent-file methodology and public-source requirement. Published per-member
  KB are truncated; do not derive exact byte deficits from them.
- https://www.byronknoll.com/cmix.html — preprocessing, model ensemble, online LSTM
  and context mixing; v21 source archive; memory recommendation. Its own per-file
  table currently conflicts with the leaderboard's Dickens entry, so verify
  source totals before treating that table as an exact coherent reference.
- https://github.com/byronknoll/cmix — public source, GPL, build instructions and
  floating-point reproducibility caveat. Prefer portable O3 with strict floating
  behavior; independently decode every resulting stream.
- https://www.bellard.org/nncp/ — Transformer-based NNCP and earlier open Python
  implementation. Current C release uses LibNC; inspect redistribution/source
  availability before claiming eligibility on the open-source leaderboard.
- https://www.bellard.org/libnc/ — deterministic tensor library, CPU/GPU support,
  binary download. A binary-only dependency is not automatically an eligible
  freely downloadable source release.

No messages to maintainers, source publication, or Actions jobs are authorized
by reading these references. All current work remains local research.


## First completed independent branch

`multiscale_volume_probe.py` finished six full frames; every frame independently
restores the full member. MR: identity1,671,099; z-nearest2,173,131;
z-interpolated2,127,219; xyz-interpolated2,045,886 bytes. X-ray: identity3,721,976;
xy-interpolated3,854,293. Current selected members: MR1,671,101 andX-ray3,531,428.
All nontrivial new transforms lose. The MR identity wrapper saves two framing
bytes only, retained as an optional future packaging improvement; no new model
advantage and no change to the default portfolio. Full evidence:
`2026-09-28-multiscale-volume-negative.json`. Session92540terminal.

The OSDB direct-LCG screen inspected99,998 parsed rows. For integer/key/date
columns0/1/2/5, gcds of consecutive difference determinants are all1. Candidate
moduli included observed range/cardinality,2^31-1,2^31 and2^32; fitting consecutive
triples produced at most6 matching next keys,2 matching next unique integers,
1,000 repeated small values (a constant predictor), and3 matching next dates
out of99,997. This rejects a direct visible-state affine recurrence as tested;
it does not disprove hidden-state generators or shuffled-generated sequences.
Naive cross-column empirical entropy reductions with unique values were
recognized as overfitting and were not counted as compression gains.

Downloaded pristine CMIXv21 from the author's website,731,518-byte ZIP,
SHA2568fd46731ed0125707021c2db4feb24179617b3993b735c335f2e0b3c00e5a0dc.
Stored at`benchmark-work/references/cmix-v21` withsource anddownloadprovenance.
Only source is read; no Actions or remotecompute. Buildsession13812 usesCPU22,
GCC with-O3 -ffp-contract=off -fno-fast-math. Source haspreprocessing-only-s and
matching-d; these avoid constructing the largePredictor. No fullCMIX run started
while availableRAMisbelowits requirement. Next small experiment can combine
its reversible dictionary transform with identical existingentropybackends.
