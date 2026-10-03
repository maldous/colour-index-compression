# Shared-description language: fixed-space bounds and controls

**Status:** theory/design note only. No SDL prototype, source change, run, or
novelty claim is made here. The proposal is a deliberately tiny, fixed-state-
space comparison intended to separate representation savings from modelling
claims.

## Prior art first

Shared directed acyclic representations, canonicalisation under an order, and
the trade-off between succinctness and tractable queries are established work.

| Relevant result | Primary source | Consequence for this design |
| --- | --- | --- |
| Ordered decision graphs represent Boolean functions as DAGs; worst-case size remains exponential, though sharing can make many instances smaller. | R. E. Bryant, [“Graph-Based Algorithms for Boolean Function Manipulation”](https://doi.org/10.1109/TC.1986.1676819), *IEEE Transactions on Computers* 35(8), 677–691 (1986). | A hash-consed reduced ordered BDD (ROBDD) is a required established control, not a new SDL idea. |
| Knowledge-compilation languages differ in succinctness and in which queries/transforms they support efficiently; the analysis includes nested DAG languages such as OBDDs. | A. Darwiche and P. Marquis, [“A Knowledge Compilation Map”](https://doi.org/10.1613/JAIR.989), *JAIR* 17, 229–264 (2002). | “Smaller description” cannot be discussed without declaring the representation language and supported operations. |
| Deterministic decomposable factorisations permit product/sum model counting and compact enumeration. | D. Olteanu, [“Factorized Databases: A Knowledge Compilation Perspective”](https://www.cs.ox.ac.uk/dan.olteanu/papers/o-beyondnp16.pdf), BeyondNP (2016). | Shared products/unions and count propagation are established; a byte archive still needs its own wire grammar and canonical member code. |
| Exact weighted model counting can be computed by dynamic programming over a project-join tree. | J. M. Dudek, V. H. N. Phan and M. Y. Vardi, [“DPMC: Weighted Model Counting by Dynamic Programming on Project-Join Trees”](https://arxiv.org/abs/2008.08748), CP 2020. | Exact completion counting on a restricted compilation is plausible, but general constraint counting is not thereby cheap. |
| Model counting has already been used to choose a constraint model from positive examples. | C. Coulombe and C.-G. Quimper, [“Constraint Acquisition Based on Solution Counting”](https://doi.org/10.4230/LIPIcs.CP.2022.15), CP 2022. | Choosing a restrictive/short model from examples is prior art and is not a compression result without a physical code. |

This document therefore treats SDL as a wire-format and control experiment,
not a claim of a new theory of constraints, sharing, or model counting.

## Fixed state space and oracle

Fix \(d\leq12\) Boolean variables and the universe
\(U=\{0,1\}^d\). A candidate description denotes a truth set \(S\subseteq
U\). An exhaustive oracle enumerates all \(2^d\) assignments, evaluates the
candidate's declared semantics, and emits a canonical truth-table bitset in
lexicographic variable order. Two descriptions are comparable only if their
oracle bitsets are byte-identical.

The oracle is a *qualification tool*, not a decoder shortcut. The archived
decoder receives the candidate's nodes, IDs, parameters, lengths, root, and
member information; it must reproduce the designated member without an oracle
or encoder-side search. The tiny \(d\leq12\) boundary makes exhaustive semantic
equivalence practical and deliberately says nothing about general #P-complete
counting.

For each truth set, select the smallest complete serialized candidate among a
declared finite set by actual bytes. Candidate construction may use canonical
hash-consing, but selection is by the final archive, including its container,
not an in-memory node count.

## Wire-level representations and mandatory fees

All alternatives use the same outer container:

```
magic | version | state-space-id | d | representation-id |
model-length | model-bytes | member-length | member-bytes |
checksum
```

All integer encodings, byte order, checksum, and `state-space-id` are fixed
before a screen. `state-space-id` identifies the ordered variable universe,
not a benchmark or filename. The following fees are non-optional.

| Representation | Model bytes that must be present | Member bytes / reconstruction rule |
| --- | --- | --- |
| Canonical flat conjunction | Clause count; per clause arity; every variable ID and polarity; any equality/count/offset/parity operator tag and all operands/parameters; explicit root/acceptance convention. | Canonical rank among satisfying assignments only if an exact completion-count method is also stored/defined; otherwise a direct \(d\)-bit assignment. |
| Direct truth bitset | Exact \(2^d\)-bit table in fixed assignment order. | The original assignment may be stored directly, or as an index among set bits with an exact fixed scan rule. |
| Direct combinadic member set | Set cardinality, canonical sorted member indices, and enough range/width information to distinguish a subset of \(U\). | A member rank/index uses the same fixed ordering; no uncharged set reconstruction. |
| ROBDD | Fixed variable order ID or an explicitly stored order; root ID; node count; terminal convention; for every node, variable ID and both child IDs. IDs must be topological and bounds-checked. | A fixed branch order plus exact per-child completion counts can encode a satisfying member; otherwise store the assignment directly. |
| Shared SDL DAG | Node count, root, node tag, child count/IDs, operator parameters, variable/offset/constant IDs, and explicit type/arity. Hash-consing does not waive any reference or node record. | Same rule as ROBDD; every choice is derived from stored nodes and a declared traversal order. |

Lengths are physical fields, not inferred process state. Root IDs, terminal
IDs, parameter widths, duplicate child IDs, and empty/one-node cases are
validated by the decoder. A shared DAG wins only after every node and edge
reference is charged; a flat conjunction wins only after each repeated literal
is charged.

### Representation effects to classify rather than combine

| Claimed effect | What the control must isolate |
| --- | --- |
| Ordinary metadata entropy | Compress the exact model byte string, with its length and codec ID, while retaining the same semantic representation. |
| Deduplication | Compare an ordered flat list with an explicitly referenced shared-node table. No change to operators or truth set. |
| Shared parameter | Compare repeated literal parameters against an explicit parameter table plus references. |
| Factoring | Compare a flat conjunction/disjunction against a DAG whose product/union structure is stored. The oracle must show equal truth sets. |
| Recursive graph | Compare only where a finite acyclic unfolding is stored or a cycle semantics and bounded evaluation rule are fully specified. A pointer cycle is not an uncharged recurrence. |

Metadata-compression controls use the same chosen metadata backend for every
representation in that row: raw, and separately a fixed-version/configuration
`zstd` and `bzip2` encoding. The codec name/version/configuration,
uncompressed length, compressed length, and failure fallback are stored. The
member payload is unchanged. This tests ordinary byte redundancy in metadata;
it must not be described as a constraint-model gain.

## Safe selection and pruning statements

Let \(B\) be the bytes already irrevocably committed by a partial candidate and
\(F_{min}\) a proved lower bound on every mandatory remaining field under the
wire grammar. Then \(B+F_{min}\geq I\), where \(I\) is the incumbent complete
archive size, safely prunes the candidate. The universally valid fallback is
usually weak: remaining semantic structure may require zero extra nodes only
when the partial object already denotes a valid truth set.

The following are **not** safe lower bounds without proof: current node count,
an estimated entropy, an MDL score with fractional logarithms, an approximate
model count, or a presumed amount of future DAG sharing. Candidate search can
still use them as labelled heuristics, but cannot claim exhaustive minimization.

For a fixed compiled object, a completion count can be exact only under a
declared restricted semantics. For example, an ROBDD with a fixed variable
order permits suffix completion counts by dynamic programming, accounting for
variables skipped between a parent and child. A bounded-width acyclic SDL with
width at most 12 can similarly evaluate every remaining assignment explicitly.
These are practical indexing methods for this screen; they are not a general
#P-closure result for arbitrary constraints, recursive graphs, or unbounded DAG
width.

## Unrelated structural families for the same oracle

Each family is instantiated only with \(d\leq12\), then all candidate
descriptions are oracle-checked against the same truth-table bitset. The
families exercise sharing for different reasons, avoiding a claim based only on
one equality-shaped input.

| Family | Two-way relation cases | Three-way relation cases | Required absent/negative control |
| --- | --- | --- | --- |
| Finite binary relations | Symmetry/anti-symmetry-style constraints on facts \(R(u,v)\), with a fixed finite domain and a flattened fact-variable order. | A transitivity-style implication over \(R(u,v),R(v,w),R(u,w)\), where the domain is chosen so total facts remain \(\leq12\). | A randomly selected truth set of the same \(d\) and cardinality, with no template dispatch. |
| Equality, count, and offset | Equality pairs and exact/interval Hamming-count conditions. | Three-variable parity or offset relations such as \(x_i\oplus x_{i+o}\oplus x_{i+2o}=b\), with all offsets and boundary policy stored. | Same histogram/cardinality but a shuffled truth table or a flat explicit member set. |
| Repeated parameter templates | Repeated two-argument predicates with an explicit parameter table. | Repeated ternary predicate templates with shared offsets/constants. | Unique parameters per predicate, so the shared-table form pays overhead without reuse. |

The random and unique-parameter controls must be generated from a frozen seed
and treated exactly like every other state space. There is no filename, corpus,
or semantic-class dispatch in the encoder policy.

## Exact index controls

For any candidate that claims an index shorter than the direct \(d\)-bit
assignment, it must provide one of the following, and the decoder must use the
same choice:

1. a direct bitset scan in the fixed lexicographic universe;
2. a combinadic rank over an explicitly stored sorted member set; or
3. a compiled-DAG prefix traversal with exact child completion counts.

The third control is only admitted when every node has finite acyclic semantics
and the stored model plus order determines the count. For width \(\leq12\),
the exhaustive oracle can independently check the count at every prefix. A
general constraint solver, an approximate count, or an encoder-only search is
not an index decoder.

## Falsifiable result categories

* **Metadata-only:** compressed flat metadata beats raw metadata while the
  semantic representation is unchanged.
* **Deduplication-only:** shared-node references beat repeated flat fragments,
  with identical operators and parameters.
* **Factoring:** a DAG beats both its flat expansion and metadata-compressed
  flat control while the oracle bitset is identical.
* **No opportunity:** direct bitset/combinadic set or canonical flat form is
  smaller after all fields. Retain this result; it falsifies the proposed
  representation advantage for that state space.

No category establishes a general compression improvement. It establishes only
a complete-byte result for a fixed finite state space, wire grammar, and
candidate set.
