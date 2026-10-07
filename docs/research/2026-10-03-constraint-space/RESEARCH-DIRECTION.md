# Six theory redirection and resource-constrained objective

Controlling direction: the user's exact-intersection redirection and complete
archive objective. Ordinary CIX optimisation stays paused. “Exact Intersection
Coding” is a provisional internal question, not a public invention claim.

## Objective and claim rule

For input x choose a decoder-complete candidate a=(C,T,E,theta), with
`Decode(Archive_a(x)) = x` exactly. Minimise the actual serialized archive:

`L(C)+L(T)+L(theta)+L(metadata)+L(exceptions)+L(payload)+L(framing)`.

These terms must form a disjoint accounting partition, not double-count shared
fields. Constraint outcome labels are included: for a statistic f, the decoder
needs both its definition and the observed label v to reconstruct f^-1(v).
It cannot evaluate f(x) before reconstructing x. Any stored counting circuit,
variable order, initial model state, integer convention, dictionary or residual
also belongs in the partition.

Subject to declared encode time TE, decode time TD, peak memory Mmax and,
where applicable, temporary storage and streaming constraints. Discovery,
discarded trials and compilation count toward encoder resources. No unrestricted
minimum over all programs is claimed; the actually explored family and search
budget must be reported. FAST/DEFAULT/BEST change those budgets and search
policies, not the definition of size or correctness. This is a theory contract,
not a change to production CLI settings.

For exact uniform set coding, actual marginal improvement is

`w(N_C)-w(N_Cc) - delta L(description) - delta L(aux,framing,padding)`,

where `w(N)=ceil(log2 N)`. Ideal log-volume differences are analytical tools;
acceptance uses final archive bytes. Approximate probability coding can be
exactly lossless but must report its actual cost rather than a dense-rank cost.

For a declared reference set R, define
`Delta = min_{b in R feasible} L_b(x) - L_Six(x)` and
`gain_percent = 100*Delta / min_{b in R feasible} L_b(x)`.
Record exact versions/settings/inputs/resource limits and all decoder assets.
“Best established compressor” means best measured in R, not all existing or
possible compression methods. A positive Delta is a result on that input and
budget, not a new theory or universal superiority. There is no measured positive
Delta against an established compressor in this checkpoint.

## What prior art destroys

URPILS already selects automatically discovered conjunctions by model cost
plus an admissible-space/noise description. Its specific scoring procedure
uses approximate counts/errors and is not a physical codec. That gap does not
make exact indexing new: enumerative coding and decision-diagram ranking
already provide it. See the full-paper reconstruction in
`urpils-reconstruction.md` and the compilation boundary in `exact-ir-boundary.md`.

BDD ranking/unranking is explicit prior art, including skipped variables and
complemented edges; it is not merely an inference we draw from model counting.
[Symbolic and Explicit Search Hybrid Through Perfect Hash Functions](https://cdn.aaai.org/ojs/13637/13637-40-17155-1-2-20201228.pdf).

Nor is constraint interaction itself an overlooked invention: CABSC already
evaluates interacting constraints with solution counters.
[Constraint Acquisition Based on Solution Counting](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2022.15).

## Mathematical boundary: the unrestricted target is impossible as stated

If a proposed algebra includes arbitrary Boolean clauses, permits arbitrary
conjunction, always produces a polynomial-size representation in polynomial
time, and counts it in polynomial time, then it counts arbitrary CNF formulas
in polynomial time. Each clause is individually trivial; their conjunction is
#SAT. Such a claim entails FP=#P. This is a conditional complexity obstruction,
not a proof that FP differs from #P.

A credible restriction must bound representation size, frontier width,
variable order, component interaction, constraint language or compilation cost.
“Each operand is easy” is insufficient. Pairwise Apply may be polynomial in
operand sizes while repeatedly composed output grows exponentially.

### Count-to-rank reduction

If a representation permits polynomial-time conditioning on prefixes and exact
counting of the conditioned representations without prohibitive blowup, then
lexicographic ranking/unranking takes at most n*|Sigma| count queries, plus
big-integer arithmetic. At each position sum counts of smaller-value branches;
for unrank choose the branch interval containing r and subtract its offset.
Induction on prefix length proves both are inverses. A total count alone is
not this oracle. Complexity must include the integer bit lengths and compiled
representation size. This is the known enumerative completion-count method,
not a new theorem claim.

## The remaining empirical question, not an asserted unsolved theorem

The narrowed target is **compact, automatically discovered, decoder-complete
descriptions with affordable exact indexing**, compared with practical existing
descriptions. None of this checkpoint proves that this entire target is absent
from prior work. The priority is to identify a specific restricted algorithmic
problem before labelling it open or new.

Candidate restrictions worth examining, currently unqualified:

1. Equality/affine component reduction plus histogram allocation, with explicit
   state-space caps and coefficient-DP indexing.
2. A fixed-order diagram or bounded-frontier certificate whose complete bytes
   beat both its predicate source and ordinary model coding.
3. Joint constraint discovery that survives a direct-model control: a short
   conjunction is uninteresting if a shorter single known relation describes
   the same set.

“Degrees of freedom” is not automatically distinct from entropy or MDL.
For affine systems it is ordinary matrix rank/nullity. For nonlinear finite
sets log-cardinality is not a coordinate dimension, and a low-dimensional
description can still have high label, precision or computational cost.

## Phase status and next decisions

* Phase1 prior-art destruction: URPILS main paper and appendix reconstructed;
  enumerative/MDL, acquisition and compiled exact indexing overlap established.
  Search is targeted and not certified exhaustive.
* Phase2 mathematical boundary: precise #SAT closure obstruction, conditioning
  requirement and approximate-count versus actual-code distinction documented.
* Phase3 tractable exact intersection: known families mapped; binary equality
  plus histogram DP derived. No new family established.
* Phase4 synergy: analytical examples and negative physical toy results retained;
  a generic finite automated search is being qualified separately.
* Phase5 new abstraction: none survives as a new formulation yet.
* Phase6 proof: elementary known consequences proved; no new theorem claimed.
* Phase7 tiny implementation: CSP1 isolated Rust prototype, 25 exact archives;
  no production integration.
* Phase8 conventional comparison: ideal same-information equivalence established;
  matched practical reference experiments remain pending, not wins.
* Phase9 integration: not justified and not started.

Recommendation: **modify and continue the restricted computational question;
abandon the claim of a new general constraint-space compression principle**.
Do not return to ordinary optimisation or package an unqualified theory route.
