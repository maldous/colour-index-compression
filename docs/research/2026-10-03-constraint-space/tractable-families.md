# Exact coding of constrained spaces: tractable families

This note distinguishes a known exact ranking/counting result from a possible
compression use. A reversible code for a constraint set `S` needs the decoder
to reconstruct the same instance, compute `|S|`, and unrank an integer in
`[0,|S|)`. Approximate counts alone cannot safely delimit an exact code unless
they are converted into certified integer bounds and an explicit escape path.

## Families with usable exact structure

| Family | Established result | Exact-code implication | Potential CIX use |
| --- | --- | --- | --- |
| Product constraints / fixed compositions | Multinomial counts and lexicographic rank are polynomial-time big-integer arithmetic. | Counts plus rank give a complete enumerative code. | Existing composition/rank coding is this case. Joint blocks only help when the charged shared count description is smaller. |
| Finite-state constraints / symbolic dynamics | A regular constraint has an adjacency matrix; path counts are DP or matrix powers. Constrained-system coding is a standard application. | Store automaton/version, start/end state and length; rank transitions by suffix counts. | Bounded byte-state rules, run limits, periodic records. A learned automaton is not free decoder state. |
| Bounded-treewidth factor graphs | Variable elimination/junction-tree DP computes partition functions in time exponential in treewidth, polynomial in instance size. | With a fixed variable order and exact table counts, choose each value by conditional suffix count. | Explicit local byte constraints where primal/factor treewidth is bounded and the decomposition is stored or canonical. |
| Knowledge compilation (d-DNNF / SDD) | Deterministic decomposable circuits support linear-time weighted model counting after compilation. | Determinism supplies disjoint sums and decomposability supplies products, enabling rank/unrank with stored circuit. | Only where a compact circuit itself beats raw constraints; compilation cost and circuit bytes dominate otherwise. |
| Bounded-width posets | General linear-extension counting is #P-complete; restricted structural parameters admit DP. | Rank a linear extension through counts of feasible ideals only for a declared tractable class. | Ordering metadata or dependency schedules with small frontier width; arbitrary inferred posets are not tractable by default. |
| Permutations with simple restrictions | Factoradic ranks unrestricted permutations in linear/quasilinear arithmetic; some pattern classes have algebraic/DP enumeration. | Store the class and exact count recurrence, then rank. | Only if permutation structure is already transmitted or canonical; storing a general permutation costs about `log2 n!`. |
| Group actions / orbit codes | Orbit-stabilizer yields orbit sizes when group and stabilizer are computable; canonicalization can be hard. | Encode orbit representative plus group-coset rank, with a deterministic canonical representative. | Symmetric records/tables, only with an explicitly stored group action and canonicalization proof. |
| Succinct structures | Many tree, planar, and grammar classes have Catalan-like or grammar DP counts and rank/select encodings. | Code a canonical structural skeleton then literals. | Existing phrase/grammar work; payload and grammar dictionary must be charged. |

## Hardness boundaries

`#SAT` and general `#CSP` counting are #P-complete. General poset linear
extension counting remains #P-complete even under several restrictions. These
facts rule out treating arbitrary inferred constraints as a cheap exact coder.
Bounded treewidth, a fixed finite automaton, a decomposable deterministic
circuit, or a parameter with an explicit FPT bound must be part of the frozen
decoder contract.

## Exact counts are not required for every exact code

Approximate tables can define a uniquely decodable code when the decoder has the same deterministic nonzero-support table; their efficiency against true set cardinality is then unsupported. Cover allows integer upper prefix bounds, with holes, while preserving inversion. Safe designs are: exact
integer DP; interval arithmetic that refines until one branch is proved; or an
escape that stores literals when certification exceeds the budget. The search
model itself is encoder-only and must not be required for decode.

## Primary sources and contemporary entry points

* Brightwell and Winkler’s linear-extension hardness is summarized and extended
  by Dittmer and Pak, [Counting linear extensions of restricted posets](https://arxiv.org/abs/1802.06312).
* Bounded-treewidth #CSP algorithms are surveyed in Marx,
  [Tractable hypergraph properties for constraint satisfaction](https://arxiv.org/abs/0902.2129).
* Darwiche’s knowledge-compilation map, including decomposability and
  determinism, is [The knowledge compilation map](https://doi.org/10.1613/jair.989).
* The SDD formulation and tractable operations are Darwiche,
  [SDD](https://doi.org/10.1609/aaai.v25i1.7977).
* Exact exponential limits for two-dimensional posets are documented by Kozma,
  [Exact exponential algorithms for two poset problems](https://arxiv.org/abs/1912.13117).
* Permutation/poset pattern-counting tractability boundaries are Cooper and
  Kirkpatrick, [The complexity of counting poset and permutation patterns](https://arxiv.org/abs/1409.4368).
* Constrained coding using finite-state constrained systems is surveyed by
  Immink, [Codes for Mass Data Storage Systems](https://doi.org/10.1007/978-3-642-00258-4).

## Research consequence

Known: exact rank coding is practical for explicit finite-state, composition,
and bounded-width DP families. Potential: a CIX experiment could add a small,
versioned finite-state or bounded-frontier constraint language, complete
metadata and raw fallback. Newness is not established by this note. Any such
cell must compare complete bytes against identical native prediction and must
separately measure count-table memory, decomposition bytes, and rank cost.
