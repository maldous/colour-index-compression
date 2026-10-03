# Equality components and composition counting: prior-art boundary

**Status:** theory and literature audit only.  No algorithm was implemented,
run, or claimed novel.  The question is whether an input-derived equality
partition plus an exact composition dynamic program (DP) would be new enough
to justify a compression claim.  The answer from this non-exhaustive primary
source review is **no such claim is presently supported**.

## The proposed object, stated precisely

Let byte positions be partitioned into equality components
\(E_1,\ldots,E_q\), where all positions in component \(j\) must hold the same
symbol and \(w_j=|E_j|\).  Given an alphabet \(A\) and target histogram
\((n_a)_{a\in A}\), the number of satisfying assignments is the coefficient

\[
 [\prod_{a\in A}x_a^{n_a}]
 \prod_{j=1}^{q}\left(\sum_{a\in A}x_a^{w_j}\right).
\]

For a fixed, externally supplied partition this is an exact constrained-set
count.  It is neither a proof that the partition is cheap to describe nor a
physical codec.  If the partition is inferred from the input, a complete
archive must describe it, or derive it from information already decoded by a
fixed rule.  A decoder must then reproduce the partition before it can use the
count or a member index.

## Closest established lines of work

| Line of work | Direct primary source | What it already establishes | Limit for this use |
| --- | --- | --- | --- |
| Enumerative coding of a constrained finite set | T. Cover, [“Enumerative source encoding”](https://doi.org/10.1109/TIT.1973.1054929), *IEEE TIT* 19(1), 73–77 (1973). | A constrained set can be described by an enumeration/index construction. | It does not supply a byte-level format for an input-derived equality partition. |
| Multiset-permutation enumeration | B. Vasić and O. Milenković, [“Permutation (d,k) codes: efficient enumerative coding and phrase length distribution shaping”](https://doi.org/10.1109/18.887880), *IEEE TIT* 46(7), 2671–2675 (2000). | Uses enumeration of multiset permutations in an enumerative encoder. | This is fixed-composition enumeration; it does not solve weighted equality components. |
| Exact weighted counting by DP | J. M. Dudek, V. H. N. Phan and M. Y. Vardi, [“DPMC: Weighted Model Counting by Dynamic Programming on Project-Join Trees”](https://arxiv.org/abs/2008.08748), CP 2020. | Computes exact literal-weighted CNF model counts by planning a project-join tree then applying DP with joins and projections. | It is a general counter, not a rank/unrank coder or an archive design.  Its tractability depends on the decomposed instance. |
| Constraint acquisition by solution counts | C. Coulombe and C.-G. Quimper, [“Constraint Acquisition Based on Solution Counting”](https://doi.org/10.4230/LIPIcs.CP.2022.15), CP 2022. | Selects a CSP from positive examples using a candidate Meta-CSP, branch and bound, and model counting. | It acquires a solver model; it does not encode the input bytes or provide member ranking. |
| Factorised deterministic representations | D. Olteanu, [“Factorized Databases: A Knowledge Compilation Perspective”](https://www.cs.ox.ac.uk/dan.olteanu/papers/o-beyondnp16.pdf), BeyondNP 2016. | In deterministic decomposable representations, products become multiplication and unions summation for one-pass counting; the paper also discusses compact representation and enumeration. | The objects are query answers.  No byte archive, equality-partition codec, or canonical rank/unrank follows automatically. |
| Equality/partition constraints in relations | S. S. Cosmadakis, P. C. Kanellakis and N. Spyratos, [“Partition semantics for relations”](https://doi.org/10.1016/0022-0000(86)90019-X), *JCSS* 33(2), 203–233 (1986). | Develops partition semantics for relations and dependencies, including functional determination. | It is database dependency theory, not a composition-coded byte representation. |
| Relational column dependency compression | J. Abou Assali, J. S. Vitter and M. J. Zaki, [“Compressing table data with column dependency”](https://doi.org/10.1016/j.tcs.2007.07.016), *TCS* 387, 273–283 (2007). | Formalises column dependency and uses it for table compression. | It is strong prior art for exploiting derived equality/dependency structure in relational data, but its model is not this DP. |
| Degree-constrained ensemble MDL | L. Hébert-Dufresne *et al.*, [“Network compression with configuration models and the minimum description length”](https://doi.org/10.1103/PhysRevE.110.034305), *Physical Review E* 110, 034305 (2024). | Charges model description plus the size/probability of graph ensembles constrained by degree features. | It uses approximate ensemble sizes; it does not offer exact ranking of arbitrary degree-constrained graphs. |

The earlier URPILS audit is relevant direct prior art for *MDL-guided
constraint selection*: it is analysed in
[urpils-reconstruction.md](urpils-reconstruction.md).  It is not evidence that
its estimated score yields a physical exact codec.

## What can be counted exactly in the simplest equality case

For \(|A|=2\), choose the number \(h\) of positions assigned symbol 1.  The
count is the coefficient

\[
 [z^h]\prod_{j=1}^{q}(1+z^{w_j}).
\]

A coefficient DP over components and partial weight is exact.  It has
\(O(qh)\) arithmetic-table updates for a target \(h\), ignoring the growing
integer bit cost.  A suffix version of the same table supports a canonical
branch decision for each equality component and hence could support rank or
unrank once a symbol/component order is fixed.  This is a routine generating-
function/weighted-model-counting construction, closest in broad algorithmic
form to the exact DP framework of Dudek–Phan–Vardi above; it is not identified
here as a new method.

The qualifier on the complexity matters.  When \(w_j\) are unary in the
expanded input, \(h\leq\sum_jw_j\) and the pseudo-polynomial table is
polynomial in that expanded size.  When weights are binary-encoded numeric
input, the same \(O(qh)\) recurrence is pseudo-polynomial, not polynomial in
the encoding length.  Equality components extracted from a byte block have
unary sizes bounded by the block length, but a transformed or grammar-derived
model must not silently inherit that property.

For the 256-symbol byte alphabet the natural DP state is a residual histogram
\((r_0,\ldots,r_{255})\) and the generating function is the one at the top of
this document.  Its naive state universe has

\[
\prod_{a=0}^{255}(n_a+1)
\]

states.  The fact that 256 is a fixed constant does not make this practical;
the exponent is enormous.  If alphabet size is treated as part of the input it
is exponential in that dimension.  Component-size equality alone does not
remove this state explosion.  Sparsity, independently decomposable symbol
groups, a bounded active alphabet, or a proved alternative representation would
be an additional assumption that must be charged and tested.

## Specific ideas, only where a close antecedent exists

1. **Compile only a proved decomposable equality instance.**  The closest
   antecedent is factorised deterministic representation and project-join-tree
   DP.  A proposed archive could use component products only when component
   choices are independent after every shared histogram/state constraint has
   been conditioned on.  Otherwise multiplying counts is unsound.  The stored
   constraint graph/partition and the compilation order would be part of the
   model description.
2. **Use an exact DP only as an encoder-side accounting/ranking primitive.**
   DPMC supports the general precedent for exact weighted counting by DP; Cover
   supports enumeration of a known finite set.  Neither eliminates the need to
   specify canonical branch order, rank/unrank, big-integer width, stored model
   fields, and fallback.  A score estimate must never stand in for this count.
3. **Treat degree and relational freedom as separate models.**  The closest
   antecedent is configuration-model MDL and relational dependency compression.
   A degree sequence or equality partition may lower an ensemble description,
   but exact reconstruction still needs an exact member code.  Approximate
   ensemble cardinality is useful for selection research, not for a byte-exact
   payload length.

These are scoped engineering directions, not proposals of new algorithms.

## Novelty-falsification and open boundary

The following claims are already falsified as novelty claims by the sources
above: using equality/partition structure as a constraint; selecting constraints
with solution/model counting; two-part MDL accounting; enumerating a known
finite constrained set; multiset composition coding; and DP over decomposable
weighted constraints.

The review did **not** locate a primary paper that exactly matches all of:

* an input-derived equality partition of arbitrary byte positions;
* an exact 256-symbol histogram-constrained count and canonical rank/unrank;
* a stored decoder-complete model; and
* selection by complete physical archive size.

That is an **open literature-search boundary**, not a novelty conclusion.  The
combination may have direct prior art outside this limited search, and even a
new combination would require proof of exact reconstruction and measured
complete-byte savings before it is an implementation contribution.

## Minimum proof obligations before a codec claim

* Define exactly how the equality partition is represented or causally
  reconstructed, including any input-derived discovery instructions.
* Prove that the DP's counted set equals the decoder's accepted set.  In
  particular, do not multiply component counts across a shared composition,
  transition, degree, or residual constraint without conditioning it away.
* Specify canonical rank/unrank or a finite arithmetic code and all
  termination, length, checksum, and padding fields.
* Compare full archives against a fixed-composition control with the same
  partition/model description policy.  A DP count or MDL estimate alone is not
  a saved byte.
