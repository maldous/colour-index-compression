# Constraint-space coding: theory-first investigation

Status: first investigation, not a novelty certification. Production CIX and
its optimisation queue are unchanged. Tiny prototype qualification is recorded
separately; proposed experiments are not evidence of practical improvement.

## 1. Verdict and strongest abstraction

Current evidence supports **A for the central coding principle**, and **B for
an explicit constraint-discovery/counting architecture**. No result currently
supports D or E. A new practical algorithm (C) would require an actually new
tractable search/count/rank procedure and matched evidence, not a new name.

Verdict labels: A = existing theory under different terminology;
B = interesting integration of established theory; C = new practical algorithm
within established theory; D = potentially new theoretical formulation;
E = substantive new compression theory supported by distinction and evidence.

The strongest useful object is a **resource-bounded, executable finite-set
description**, not an isolated predicate. For length n over alphabet Sigma,
let U=Sigma^n, M=|U|. An archive description d reconstructs a nonempty set
S_d subset U and specifies an order. Its contract includes:

* a prefix-decodable description, including length, alphabet, parameters,
  latent grouping, exception rules and decoder version;
* membership and conditional completion counting, or a certified alternative;
* mutually inverse rank/unrank procedures;
* explicit time, integer-precision and memory bounds.

The code is d followed by a rank in [0,|S_d|). Description length is
`ell(d)+ceil(log2 |S_d|)+framing+padding`. The input must belong to S_d.
Singletons need zero rank bits, but describing the singleton can cost the
entire original. Decoder software is the declared common machine, not a place
to hide instance-specific constants. A new dictionary or learned model must
be in the archive or explicitly counted as an external asset.

This finite-set two-part formulation coincides with algorithmic statistics
and enumerative coding. Cover already gives general prefix-count ranking;
Kolmogorov structure functions explicitly minimise set cardinality under a
model-description budget. [Cover 1973](https://isl.stanford.edu/~cover/papers/transIT/0073cove.pdf),
[Vereshchagin–Vitányi 2004](https://homepages.cwi.nl/~paulv/papers/structure.pdf).

## 2. Algebra: intersections, partitions and quotients

Predicates define sets; conjunction is set intersection. Extentionally this
is associative, commutative and idempotent, with U as identity and empty set
as zero. **Serialized descriptions are not idempotent for free**: duplicated
predicates still cost bytes unless a canonical simplifier removes them.
Tractable representations need not remain tractable or compact under meet.
Two cheap individual constraints may have a hard joint counting problem.

An invariant f induces a partition into fibers f^-1(a). Encoding the fiber
label a and the index within its fiber is exact. Multiple invariants refine
the partition using the joint label. Quotienting alone loses information:
the selected class and the coordinate inside that class must both be coded.
Successive quotients are not well-defined unless later relations descend to
the earlier quotient; successive partition refinements always are.

For a group action, an orbit label plus a coset/orientation rank can be exact.
Stabilizers, a canonical representative and the action specification matter.
Canonicalization is itself potentially expensive. An orbit is not an excuse
to discard the original orientation.

An intersection protocol should distinguish **description syntax** from
**extensional space** and from **compiled counting certificate**. Store only
what the decoder needs. A proof/circuit can reduce decoder work but its
complete bytes must beat the alternative of recomputing from paid predicates.

## 3. Correct synergy and its limitation

For nonempty A, B and I=A intersect B, define ideal restrictions
`g(A)=log2(M/|A|)`. The interaction relative to independent event restrictions is

`s(A,B)=g(I)-g(A)-g(B)=log2(|A||B|/(M|I|))`.

Positive s means the actual intersection is smaller than uniform independence
would predict. Negative s means overlapping/redundant restrictions. This is
**negative pointwise mutual information**, not mutual information itself.
For k sets, replace the numerator by product |A_i| and denominator by
`M^(k-1)|intersection A_i|`. It does not isolate irreducible k-way interaction;
lower-order interactions also contribute. Conditional variants use the
current surviving universe instead of M.

Net gain must include joint description cost:

`G(A,B)=log2(M/|I|)-ell(A,B)`

and compared with separately paid restrictions it is

`G(A,B)-G(A)-G(B)=s(A,B)+ell(A)+ell(B)-ell(A,B)`.

Thus shared metadata is a distinct source of gain from cardinality interaction.
Finite rank rounding and differing framing must be added in actual archives.
The meaning of a constraint's cost depends on the frozen description language;
one cannot select arbitrary costs to manufacture a practical win.

If A and B are observed fiber labels of random X uniform on U, expected s
over their joint labels is `-I(A;B) <= 0`. Also
`H(A,B)+H(X|A,B)=log2 M`. Paying an optimal joint label code restores the
entropy balance. Individual inputs can compress; uniform data cannot enjoy a
universal average improvement. Searching many labels does not erase label cost.

### Concrete synergy, and the shorter conventional explanation

Take five nibbles, U={0,...,15}^5, A: every value <=7, B: every value >=7.
Counts are 16^5, 8^5, 9^5 and 1. With an explicitly fixed generic predicate
language costing six bits per threshold predicate, ideal separate savings
are 5 and approximately 4.150 bits, each less than six; joint savings are
20-12=8 bits before common framing. This demonstrates possible paid synergy
in that language, **not** that a complete archive beats an established code.
A direct constant-value description stores 7 once and beats the two-threshold
description. The entire conjunction is a known singleton enumerative model.
The prototype must report its real serialized costs, not this ideal example
as a measured win.

## 4. Proven elementary propositions (not novelty claims)

### Prefix-code validity

Let descriptions form a prefix code, and each rank have fixed width
`w_d=ceil(log2 N_d)`. Concatenation is prefix-decodable because d identifies
the exact suffix width. Kraft sum over all description/rank codewords is
`sum_d N_d*2^(-ell(d)-w_d) <= sum_d 2^-ell(d) <= 1`.
Unused ranks must be rejected. Multiple descriptions for one object do not
invalidate the code; selecting the shortest does not require search at decode.

### Exact marginal criterion

For a current S and refined T subset S containing x, refinement wins precisely
when `ell(new)-ell(old)+w(T)-w(S)+delta(framing,padding) < 0`.
Ignoring rounding this requires the restriction gain log2(|S|/|T|) to exceed
incremental description cost. Redundant constraints cannot win unless their
representation replaces a more expensive description. Contradictory sets
cannot encode any input. These statements require actual joint cost, not a
sum of independently estimated savings.

### Safe pruning, with the synergy warning

If every candidate in a search branch requires at least b description bits
and has at least a surviving objects, its complete cost is at least
`b+ceil(log2 a)+minimum framing`. Prune when this cannot beat the incumbent.
Without a certified lower bound on final cardinality, current cardinality is
NOT a valid lower bound: later constraints can shrink it to one. Rejecting
every individually unprofitable predicate can therefore miss profitable
combinations. A mere empirical gain threshold is heuristic, not a theorem.

### Frequency of savings

For any prefix code on U, at most M/2^t objects can have code length at most
log2 M-t (use Kraft). A search over many exact truths cannot circumvent this.
The cost of the selected structural truth or label supplies the missing bits.

### Equivalence to conditional probability coding

Let Z(p) count completions of prefix p in S. Define
`q(a|p)=Z(pa)/Z(p)` for feasible branches. Products telescope to 1/|S| for
every member. Ideal arithmetic information is exactly log2 |S|. Lexicographic
rank is the sum of counts of smaller sibling subtrees. Both exploit exactly
the same admissible information; integer arithmetic coding/termination have
implementation overhead. This does not imply all practical models discover
the same constraints or implement the same complexity tradeoff.

## 5. Tractability frontier and stronger research questions

General conjunction over Boolean variables includes #SAT. Exact general
counting is #P-hard; efficient ranking based on conditional counts inherits
that obstruction. Integer bit complexity must be counted. Membership alone
being cheap provides no efficient rank contract.

Useful known families include compositions, regular-language path counts,
bounded-frontier graph/CSP dynamic programs, linear systems over finite fields,
and deterministic decomposable circuits. Crucially, intersections can increase
treewidth or destroy decomposition. Compilation cost is not free.
[Darwiche–Marquis 2002](https://www.cs.cmu.edu/afs/cs.cmu.edu/project/jair/pub/volume17/darwiche02a.pdf).

Candidate investigations within established theory:

1. **Equality graph plus counts:** equality merges positions into components.
   Histograms constrain weighted assignments of symbols to those components.
   Count by coefficient extraction / DP on remaining count vectors. A new
   interaction can be real, but the state size can explode with alphabet and
   distinct component weights. Store the inferred partition cheaply or lose.
2. **Affine relations plus discrete composition:** Gaussian elimination counts
   affine solutions cheaply, but adding counts/inequalities may destroy that
   tractability. Find bounded-rank/frontier classes, not an arbitrary solver.
3. **Cross-scale conservation:** hierarchical region histograms constrain a
   contingency table or flow. Trees admit DP; arbitrary overlapping regions
   may create a hard counting instance. Partition description is paid.
4. **Broken symmetry:** code orbit skeleton plus sparse exceptions and exact
   orientation. Compare directly with grammar, dictionary and residual codes.
5. **Relationship graphs:** infer cheap edge rules, then count assignments with
   bounded frontier. Generic degrees alone do not reconstruct edges; edge
   structure and labels must remain in the residual rank or description.
6. **Computationally bounded structure function:** search descriptions subject
   to decoder time/memory as well as description cost. This is a research
   objective, not a proven new structure-function theory; resource-bounded
   algorithmic statistics already precedes it.

Exact counting is not mandatory for exact restoration. Certified integer
upper bounds can allocate intervals with holes; deterministic finite-precision
probability tables with positive support also give exact codes. Their rate is
then the implemented code's rate, not necessarily log2 |S|. Cover explicitly
discusses upper-bound enumerative coding. Uncertified approximate counts must
not silently become claimed dense ranks.

## 6. Mandatory counterarguments

* The core equation is finite-set MDL / algorithmic statistics, already known.
* Every intersection is one set: an established enumerative coder can encode it.
* The corresponding uniform conditional model gives the same ideal arithmetic
  cost. Gains versus a weaker predictor establish model discovery, not new
  information theory.
* Constraints learned from x can overfit. Describing x as its own constraint
  hides all information unless that description is charged.
* A rare intersection can look spectacular while its labels cost as much as
  the shrinkage. Positive pointwise synergy is not a uniform-source miracle.
* Efficient individual counting does not imply efficient intersection counting.
* Constraints can be expensive to discover, verify, compile and rank. A tiny
  rank can coexist with unusable decode time and huge working memory.
* Quotients, invariants and symmetry discard information unless fiber location
  and orientation are encoded. Reversible transforms preserve total cardinality.
* Synthetic threshold synergy often has a simpler constant/run explanation.
  No conventional-code superiority follows from a cardinality example.

## 6a. A concrete tractable intersection proposition

**Established combinatorial consequence, independently derived here; no
novelty claim.** Let a binary length-n object satisfy an arbitrary equality
graph on positions. Let its connected-component sizes be w_1,...,w_m. Also
require exactly h ones. The admissible cardinality is

`N = [z^h] product_j (1+z^(w_j))`.

Proof: every connected component must have one shared bit. Choosing bit one
contributes exactly w_j ones, and the generating-function product enumerates
each component assignment once. Suffix DP
`F(j,t)=F(j+1,t)+F(j+1,t-w_j)`, with `F(m,0)=1`, counts exactly.
Order components by their first position; comparing their assigned bits gives
the original byte/bit lexicographic order. Ranking sums the zero-branch
completion counts whenever the selected component bit is one; unranking
chooses the branch containing the residual rank. This is a bijection.

With unary weights arising from position counts, O(m*h) big-integer additions
suffice, and counts need at most m+1 bits. Full suffix tables use O(m*h*m)
bits in the crude worst case. Graph discovery and the complete graph/partition
description remain separate paid costs. Arbitrary binary-encoded weights are
a different complexity problem; this does not solve general #subset-sum.

For n=4, constrain positions 0 and 1 equal and require two ones. Component
weights are (2,1,1): equality alone admits 8 objects; histogram alone admits
6; together admit 2 out of 16. Set-volume synergy is log2(1.5), about 0.585
bits. The two survivors are 0011 and 1100. This is a useful exact intersection
example without a probability estimator; its sub-bit synergy may be swamped
by graph/count metadata. It is not proof of archive savings.

For q symbols, the generating polynomial is
`product_j sum_a z_a^(w_j)` and the required histogram coefficient counts
assignments. The DP state can grow as the product of histogram dimensions;
binary tractability does not imply practical 256-symbol tractability. This
distinction is an explicit rejection of an overly broad theory claim.

## 6b. Novelty map

| Category | Finding | What remains |
|---|---|---|
| ESTABLISHED THEORY | Set description plus rank; two-part codes; uniform constrained arithmetic equivalence; finite-set structure functions | No new coding principle demonstrated |
| ESTABLISHED BUT POTENTIALLY UNDERUSED | Exact completion-count DP for relational structures; compiled model counting; generic paid intersections | Practical discovery and metadata costs must be measured |
| NEW COMBINATION | Proposed explicit discovery + tractability contract + complete-cost selector | Project proposal only; not established new relative to all prior systems |
| POTENTIALLY NEW FORMULATION | None substantiated | A resource-bounded constraint language alone does not justify this label |
| POTENTIALLY NEW THEORETICAL RESULT | None substantiated | Elementary propositions above are consequences of known coding/counting theory |
| DISPROVEN / REDISCOVERY | Free intersection savings; free quotienting; multiplying causal-context multinomials; treating smaller ranks as complete archive wins | Costs, fibers, path feasibility and complexity invalidate these arguments |

Contemporary work also weakens an algebraic-novelty claim: semiring model
counting already unifies constraints and inference, and recent work extends
its learning machinery. This supplies possible computational tools, not a
new source-coding bound. [Algebraic Model Counting](https://arxiv.org/abs/1211.4475),
[The Gradient of Algebraic Model Counting, 2025](https://arxiv.org/abs/2502.18406).

## 7. Evidence and remaining investigation

See `prior-theory.md`, `tractable-families.md`, `adversarial-math.md` and
`PROTOTYPE.md`. This is a documented literature investigation, not an
exhaustive proof of absence of prior work. Contemporary primary papers and
remaining families must be reviewed before any novelty claim.

The first tiny-universe prototype has now executed; see `evidence/REPORT.md`.
It verifies selected exact reconstructions and exhaustive cardinalities, but
every complete archive is larger than its bare original. Same-information
arithmetic implementation controls and a systematic direct-description search
remain unexecuted; the mathematical equivalence is proved, not benchmarked.

No corpus identities, downloads, source-specific dictionaries, production
format changes, performance tuning, or integration are part of this work.
Next evidence should extend independent rank verification, a same-information
coder baseline, and a generic direct-description baseline. Only after that should a
bounded tractable relational family be explored on arbitrary bytes.
