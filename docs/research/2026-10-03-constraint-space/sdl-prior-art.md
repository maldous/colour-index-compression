# SDL prior-art destruction before syntax

**Status:** literature and theory audit only. “SDL” is a working label, not a
claim to a new language or principle. This document does not specify syntax,
change an archive format, implement a route, or report an experiment.

**Decision:** do not design production syntax until the proposed facility is
split into its source description, compiled counting certificate, exact index,
and complete wire costs. Compact, compositional, countable, and indexable
representations already exist in several mature literatures. A CIX result can
still be useful engineering, but those adjectives do not establish novelty.

## The claim decomposes into established parts

An exact finite-set coder needs more than an expression which denotes a set.
The following are different capabilities and may have radically different
sizes:

1. a **source description** of the constraint;
2. a **compositional semantics** for combining descriptions;
3. a **shared representation** which stores repeated subexpressions once;
4. a **compiled certificate** on which exact counting is tractable;
5. an exact count and prefix-conditioned counts sufficient for rank/unrank;
6. a deterministic **wire representation** available to the decoder;
7. a paid choice among models and representations.

No reviewed source makes all Boolean descriptions compact and cheaply
countable. The recurring tradeoff is between source succinctness, compiled
size, and the operations guaranteed to be tractable. The knowledge-compilation
map makes that tradeoff explicit across target languages
([Darwiche and Marquis 2002](https://arxiv.org/abs/1106.1819)).

| Proposed SDL property | Direct antecedent | What is already established | Remaining CIX-specific question |
| --- | --- | --- | --- |
| Boolean composition with shared nodes | Boolean circuits and negation-normal-form DAGs | `AND`, `OR`, literals, and DAG sharing are standard. | Is a restricted operator/atom family smaller after its complete wire and index are paid? |
| Canonical ordered shared DAG | Reduced ordered binary decision diagrams (ROBDDs) | For a fixed variable order, reduction merges isomorphic nodes and removes redundant tests, giving a canonical representation; some functions still require exponentially many nodes ([Bryant 1986](https://people.eecs.berkeley.edu/~russell/classes/cs289/f04/readings/Bryant%3A1986.pdf)). | Which variable order is fixed or transmitted, and who pays order search and node references? |
| Sparse set-family DAG | Zero-suppressed decision diagrams (ZDDs) | A different reduction rule compactly represents many sparse combination families ([Minato 1993](https://doi.org/10.1145/157485.164890)). | Does an input-derived admissible set favor ZDD rather than BDD reduction, after serialization? |
| Exact count by local circuit evaluation | Deterministic decomposable NNF | Decomposability makes conjuncts independent; determinism makes disjunct model sets disjoint. With missing-variable accounting, models can be counted bottom-up ([Darwiche 2001](https://citeseerx.ist.psu.edu/document?doi=c1beb47fc0bdca63bc7c1cc4038072a7ed3fa758&repid=rep1&type=pdf)). | Can the proposed constraints be compiled into a small deterministic decomposable circuit under a bounded budget? |
| Structured canonical circuit | Sentential decision diagrams (SDDs) | SDDs combine structured decomposability and strong determinism; reduced, compressed forms are canonical relative to a fixed vtree, and OBDDs are a restricted case ([Darwiche 2011](https://ai.dmi.unibas.ch/research/reading_group/darwiche-ijcai2011.pdf)). | Is the vtree fixed, searched, or transmitted, and is its cost included? |
| Sequential constraints | Finite automata and dynamic programming | A DFA with a fixed remaining length can count accepted suffix paths by state and length. Ordered transitions plus those counts support enumerative rank/unrank. Intersections use product states and can grow multiplicatively. | Which state machine is guaranteed bounded, deterministic, and identical at encoder and decoder? |
| Model plus index in a constrained set | Enumerative source coding | Once the decoder knows an ordered finite set, its member can be represented by an index ([Cover 1973](https://isl.stanford.edu/~cover/papers/transIT/0073cove.pdf)). | Is the complete model description plus rounded index smaller than alternatives? |
| Reusable productions | Grammar-based compression | Grammar codes select and serialize production rules, then reconstruct the source from that grammar ([Kieffer and Yang 2000](https://www.mit.edu/~6.454/www_fall_2002/emin/kieffer_and_yang.pdf)). | Does an SDL graph add a distinct capability beyond a grammar/SLP representation on the same bytes? |
| Local factors and relational factorization | Factor graphs and factorized databases | Global functions can be expressed as products of local factors ([Kschischang, Frey and Loeliger 2001](https://web.stanford.edu/~montanar/TEACHING/Stat375/papers/sumprod.pdf)); unions/products and nested factorizations can represent query-result relations succinctly ([Olteanu and Závodný 2012](https://openproceedings.org/2012/conf/icdt/OlteanuZ12.pdf)). | Is exact counting tractable for the proposed factor graph, rather than only approximate on a loopy graph? |
| Shared relational subexpressions | DAG factorized representations | Later factorized-database work explicitly admits sharing of repeated subexpressions in d-representations ([Olteanu and Závodný 2015](https://doi.org/10.1145/2656335)). | What are the topological reference and symbol-table costs in the archive? |
| Paid model selection | Two-part shortest-description modeling | The model/parameters and the data described under the model are both part of the description ([Rissanen 1978](https://research.ibm.com/publications/modeling-by-shortest-data-description)). | What prefix-free choice code and parameter serialization are actually used? |
| Interning repeated structures | Hash-consing and common-subexpression elimination | Hash-consing is an established way to replace structurally equal records by shared representatives, with lookup and memory-management costs ([Appel and Gonçalves 1993](https://www.cs.princeton.edu/research/techreps/115)). | Does serialized sharing save more than IDs, table headers, and canonicalization cost? |

Canonicity is useful for equality checks, caches, and deterministic reuse, but
it is not free. Its interaction with compilation and transformation support is
itself an established knowledge-compilation tradeoff
([Van den Broeck and Darwiche 2015](https://arxiv.org/abs/1404.4089)).

## Source description, certificate, and wire cost are different

Let $e$ be a source expression, $K(e)$ a compiled exact-counting certificate,
$S_e \subseteq U$ its denoted set, and $x \in S_e$. A complete
archive has a cost of the form

\[
L = L_{\mathrm{frame}} + L_{\mathrm{choice}} + L(e)
  + L(K(e)\mid e) + L(\operatorname{rank}_{S_e}(x))
  + L_{\mathrm{integrity}}.
\]

Terms may be omitted only when the decoder can derive them uniquely from paid
information and the format. There are three materially different designs:

* **Source only:** transmit $e$, then compile at decode time. The certificate
  costs no archive bytes, but compilation time, peak memory, termination, and
  deterministic compiler/version semantics become part of the format contract.
* **Certificate only:** transmit a ROBDD, d-DNNF, SDD, automaton, or other
  countable target. Its nodes, ordering structure, roots, references, and
  integer counts or rules all cost bytes and require validation.
* **Source and certificate:** transmit both, usually to make validation or
  decoding cheaper. Both cost bytes unless one is normatively derivable and
  omitted.

A short formula can compile to an exponential ROBDD under an unfortunate
order. A small factor graph can have intractable exact inference at high
treewidth. A grammar can be compact while its language is ambiguous. Therefore
“compact and countable in principle” is not evidence for a bounded exact
decoder. Compilation is precisely the potentially expensive step which a
compiled language is intended to move or control.

If the archive contains only the source expression, an adversarial archive can
be a compilation resource bomb. A production format would need a normative
compiler, versioned semantics, hard node/operation/memory bounds, a defined
failure result, and no dependence on heuristic compilation order. If the
archive contains the certificate, the decoder needs hard limits before
allocation and must validate its structure rather than trusting stored counts.

## Shared DAGs are established, and their bytes must be paid

A shared DAG can save repeated syntax, but “use one node ID for a repeated
submodel” is already the basic representation used by BDDs, compiled logical
circuits, d-representations, grammar DAGs, and hash-consed terms. Two kinds of
sharing must not be conflated:

* **Syntactic hash-consing** merges structurally identical children and
  operators.
* **Semantic reduction** can merge different-looking source subexpressions
  which denote the same residual function, as in a canonical ROBDD for a fixed
  variable order.

Internal pointer sharing in an encoder does not become archive compression
unless each node is serialized once and later uses a paid reference. A complete
wire comparison must include:

* a node count and root count;
* operator, atom, and variable identifiers;
* topological node references and their integer code widths;
* variable order, vtree, automaton alphabet/order, or a fixed format rule;
* atom parameters, lengths, universe definition, and domain sizes;
* canonicalization/version information where semantics depend on it;
* model selection and framing.

Hash values cannot define correctness unless collision equality is checked.
Canonical IDs must be stable across processes and platforms. A decoder must
reject cycles, out-of-range references, invalid topological order, arithmetic
overflow, impossible domains, and allocation claims over its resource cap.
Rejecting structurally noncanonical but semantically valid certificates is a
format decision; accepting them must not permit stored counts to bypass
independent recomputation.

## Exact count does not automatically give a correct index

Exact model count is necessary but not always sufficient for rank/unrank.
Lexicographic ranking requires exact counts after each permitted prefix choice
under one fixed total order.

* An ROBDD supplies the branch structure directly, but skipped variables need
  their multiplicative domain factors.
* A deterministic, decomposable circuit supports bottom-up model count once
  absent variables are handled. Ranking can repeatedly condition on the next
  variable and count, provided conditioning preserves the required tractable
  representation and the order is fixed.
* An SDD has the same need for a fixed vtree/variable order and correct
  missing-variable accounting.
* A DFA can tabulate accepted suffix counts for every state and remaining
  length, then use ordered outgoing symbols for rank/unrank.
* A grammar which denotes a language may be ambiguous. Counting derivations is
  not counting distinct reconstructed strings. An exact coder needs an
  unambiguous representation or an explicit duplicate-elimination semantics.
* Sum-product is exact on trees and suitable bounded-width decompositions;
  loopy approximate beliefs cannot determine an exact lossless rank.

All counts and cumulative ranks must use arbitrary-precision integers. A
fixed-width saturation, floating estimate, or approximate model count is
unsuitable for a lossless index even if it is useful for candidate pruning.

## Conservative novelty scale

This is an evidence scale for internal claim hygiene, not a patent or
freedom-to-operate opinion.

| Level | Meaning | Current assessment |
| --- | --- | --- |
| 0 | Established identity, data structure, or standard implementation technique. | Boolean composition, shared DAGs, hash-consing, ROBDD/ZDD reduction, decomposable circuit counting, automaton DP, grammar reuse, and model-plus-rank coding. |
| 1 | Routine adaptation or combination of established techniques. | Compiling a small frozen CIX predicate grammar to an existing certificate language; using exact prefix counts to rank. |
| 2 | Potentially distinctive engineering artifact; novelty not established. | A versioned safe wire form, complete-cost selector, bounded compiler, and CIX integration if shown to improve measured archives. |
| 3 | Plausible algorithmic contribution after direct prior-art comparison. | A new restricted constraint family with a proved tractability or size result and a demonstrated advantage over ROBDD/d-DNNF/SDD/automata controls. None is shown yet. |
| 4 | Strong research contribution with independent validation and a clear distinction from the closest artifact and theorem. | No current SDL claim reaches this level. |
| 5 | Claimed foundational principle after broad expert literature and legal review. | “A general new compression principle” is unsupported and conflicts with direct antecedents in enumerative coding, knowledge compilation, and MDL. |

The most defensible current description is level 1 for the mathematical
combination and, at most, level 2 for a future bounded CIX implementation. The
name “SDL” cannot raise the level.

## Exact same-space controls

Every comparison must freeze the same universe $U$, denoted set $S$, member
$x$, object order, index termination, framing, and integrity fields. A change
in any of these is not a representation-only comparison.

For each source expression $e$, enumerate $S_e$ exactly in the bounded test
and compare:

1. the source expression as a tree;
2. the same expression as a structurally hash-consed DAG;
3. a canonical ROBDD under each predeclared variable order;
4. a ZDD when the object semantics are a family of subsets;
5. a deterministic decomposable or SDD certificate, if a pinned compiler is
   available;
6. a minimized DFA for genuinely sequential constraints, if applicable;
7. the explicit truth table/bitset;
8. a direct $N$-member subset description, including $N$ and
   \(\lceil\log_2 { |U| \choose N }\rceil\) bits for the subset among all
   equally sized subsets;
9. the shortest already available direct atom/model which denotes exactly the
   same set.

The member rank has the same ideal width

\[
\left\lceil\log_2 |S_e|\right\rceil
\]

for every exact uniform same-set representation. Any archive difference then
comes from model/certificate bytes, finite coding, or framing. Also run the
same prefix probabilities through one pinned arithmetic/range coder: uniform
rank and a uniform constrained probability model cannot be credited as two
different information gains.

Record separately:

* source bytes, certificate bytes, rank bytes, and total archive bytes;
* compilation and canonicalization time and peak memory;
* encoder search cost and every rejected representation;
* decoder time and peak memory in a fresh process;
* exact reconstructed object and a hash of the enumerated set;
* malformed cycle, reference, count, rank, truncation, and resource-cap cases.

Semantically equivalent expressions must be deduplicated by their exact set in
the bounded test. Otherwise a conjunction may appear to discover a gain which
an existing direct model already describes more cheaply. A direct-model
control is mandatory for `all zero`, fixed Hamming weight, equality classes,
runs, or any other set already expressible by one established atom.

## Smallest bounded falsification test

Use eight Boolean variables. The universe has only 256 objects, so every
denoted set fits in a 256-bit oracle and every count and rank can be checked by
exhaustive enumeration without a corpus or benchmark job.

Freeze a deliberately small grammar:

* atoms: `x[i] = 0`, `x[i] = 1`, `x[i] = x[j]`, and exact Hamming weight `k`;
* operators: `AND`, `OR`, and `NOT`;
* at most seven unique DAG nodes and depth at most three;
* topological node numbering and one fixed object order;
* two predeclared BDD variable orders rather than a post-result order search.

Enumerate the bounded grammar deterministically, evaluate every expression to
its 256-bit truth table, and retain one record per distinct set. For every set,
round-trip every member through rank/unrank and compare the complete encodings
listed above. Report expression-generation cost and semantic duplicates rather
than treating them as extra discoveries.

The suite needs at least these negative controls:

* a repeated subexpression where DAG sharing should win over a tree;
* an expression with no reuse where node IDs and table framing should lose;
* a function sensitive to BDD variable order;
* a short source expression with a larger compiled certificate;
* empty, full, singleton, and near-full sets;
* a conjunction whose result equals one direct atom;
* a malformed cyclic DAG and an otherwise valid DAG with a false stored count.

Promotion requires a complete-byte win against the shortest same-set control,
bounded deterministic compile/decode resources, and independent exact decode.
One winning toy does not justify a general compressor route; it only justifies
the next frozen, input-independent test.

## Questions that syntax cannot answer

Before a production grammar is designed, the architecture must fix:

1. the object universe and total order;
2. whether the wire carries source, certificate, or both;
3. the exact tractable target and its canonicality conditions;
4. variable order, vtree, state order, and alphabet order;
5. compiler version and hard time/node/memory bounds;
6. exact count, conditioning, rank, and integer semantics;
7. node/reference serialization and model-choice prefix code;
8. decoder validation and malformed-input behavior;
9. raw fallback and complete-cost selection rule.

Until those are fixed and the eight-variable falsification test beats the
same-space controls, implementing a broad SDL syntax would mainly create a new
front end for established representations while leaving the decisive archive
cost and bounded-decoding questions unresolved.
