# Exact intersection/rank boundary

## Established boundary

BDD and ZDD `Apply` compute Boolean operations when operands share a variable
order; output size can nevertheless be exponential. SDD Apply is polynomial
for a fixed vtree subject to the usual compression caveats; d-DNNF supports
linear weighted model counting when already compiled, but conjunction can
destroy decomposability and require recompilation. Thus intersection closure is
representation-relative, never a guarantee that arbitrary individually easy
constraints remain small together.

The elementary obstruction is enough: each CNF clause has trivial satisfying
count/rank structure, while their conjunction is general #SAT. A claimed
polynomial exact-intersection compiler for arbitrary tractable conjuncts would
therefore imply an implausible polynomial #SAT count algorithm. Even when the
result has a compact representation, compilation can take or produce
exponential size.

## Classification table

| Classification | Closest paper | Different / matters | Exact count, rank, unrank | Complexity | Archive cost / confidence |
| --- | --- | --- | --- | --- | --- |
| A — established: ordered Boolean intersection | Bryant ROBDD Apply | Identical only with one fixed variable order | ROBDD suffix count multiplies by `2^k` for skipped levels; lexicographic unrank uses conditioned completion counts | Apply `O(|A||B|)` worst case; result exponential | Decoder needs result plus order and semantics, not both operands and result. High. |
| A — established: sparse set-family intersection | Minato ZDD Apply | ZDD skipped variables mean forced zero, unlike ROBDD free skipped levels | Count/unrank follows ZDD set-family semantics, not ROBDD assignment paths | Apply output may still blow up | Store universe/order/result and zero-suppression semantics. High. |
| A — established: structured circuit conjunction | SDD / d-DNNF | Fixed vtree makes SDD Apply relevant; arbitrary d-DNNF conjunction may lose decomposability | Deterministic sums and decomposable products permit exact counts; circuit-natural rank differs from original lex rank | Counts linear once compiled; compilation/output exponential generally | Store vtree/circuit and rank convention. High. |
| A — established: exact enumerative code | Cover | Dense rank requires exact counts; upper bounds permit holes | Exact or certified conditioned bounds; unrank follows same branch convention | Big-integer DP cost is representation dependent | Store only decoder-needed count/circuit data. High. |
| A — established: acquired constraints | CABSC / constraint acquisition | Acquisition proposes constraints; it supplies no compact intersection/count guarantee | Requires separately compiled exact representation | Can be hard before compilation | Store learned constraints/version or compiled certificate and semantics. Medium. |
| A — established: approximate table code | Arithmetic coding | Unique decoding does not prove closeness to `log |S|` | Deterministic nonzero-support table ranks arithmetic intervals, not necessarily constraint-set ranks | Table evaluation cost | Store table/version if decoder needs it. High. |

All classifications above use the user's A–F scale; A means established,
not a row identifier. Confidence means confidence in the established overlap,
not confidence in novelty. No D/E/F classification is supported.

## Count/rank/unrank conditions

For a fixed ROBDD, count suffix paths by DP and multiply by powers of two for
skipped free variables. ZDD skipped variables are zero, so the analogous factor
is absent. Original lexicographic rank requires conditioned completion counts;
circuit-natural rank may be cheaper but is a different code. For SDD/d-DNNF, sums
must be deterministic/disjoint and products decomposable; annotate each node
with an exact big-integer count and make an ordered child choice. Missing
variables must be accounted for (or the circuit smoothed); disjointness and
decomposability alone do not justify ignoring free variable assignments. A common
variable order or vtree is decoder metadata, not an inference made after
receiving the rank.

## Primary sources

* Bryant, [Graph-Based Algorithms for Boolean Function Manipulation](https://doi.org/10.1109/TC.1986.1676819), ROBDD canonicality and Apply.
* Minato, [Zero-suppressed BDDs](https://doi.org/10.1145/185138.185147), ZDDs.
* Darwiche, [The Knowledge Compilation Map](https://doi.org/10.1613/jair.989), language closure and tractable queries.
* Darwiche, [SDD](https://doi.org/10.1609/aaai.v25i1.7977), vtrees and Apply.
* Cover, [Enumerative source encoding](https://isl.stanford.edu/~cover/papers/transIT/0073cove.pdf), exact ranks and upper-bound prefix intervals with holes.
* Bessière et al., [Constraint acquisition](https://doi.org/10.1016/j.artint.2015.08.001), acquisition rather than a counting/ranking guarantee.
* CABSC, [CP 2022](https://doi.org/10.4230/LIPIcs.CP.2022.15), is a modern primary acquisition reference.
* Van den Broeck and Darwiche, [On the role of canonicity in knowledge compilation](https://doi.org/10.1609/aaai.v29i1.9258), gives the compressed-SDD Apply caveat.

This is a targeted boundary note, not a systematic review. “Potential” CIX
uses require a frozen representation, common order/decomposition, complete
metadata, raw fallback, and a full byte comparison; none follows from the
existence of Apply or model counting alone.
