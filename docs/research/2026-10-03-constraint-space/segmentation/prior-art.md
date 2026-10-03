# Segmentation prior art and validity conditions

Status: literature and correctness review only. This document does not report a
CIX implementation, run, or compression result. It makes no novelty claim.

## Decision summary

There are three different problems which must not share an optimizer without a
proof that their costs have the required form:

1. **Independent-segment selection.** Every chosen segment starts from a fixed
   reset state and has a complete, path-independent cost. This is a shortest
   path problem and admits exact dynamic programming.
2. **Causal probability mixing.** A normalized sequential probability
   assignment weights many possible temporal partitions without selecting and
   transmitting one partition. Partition Tree Weighting (PTW) is in this class.
3. **Stateful framed compression.** A boundary can preserve dictionary,
   predictor, offset, or entropy-table state. The cost of the next region then
   depends on the path used to reach it. A position-only dynamic program is not
   an exact reference for this class.

The immediate blocker is therefore conceptual rather than computational: an
exact segmentation claim is invalid until every candidate boundary is labelled
as a reset or a state-preserving transition and the complete decoder-visible
state is represented in the reference.

## 1. Complete objective

Let the source be `x[0..n)` and let a path contain boundaries

```text
0 = t_0 < t_1 < ... < t_k = n.
```

For an independently decodable segment, define `b(i,j,a)` as the exact number
of bits added by applying action `a` to `x[i..j)`. It must include every cost
caused by that action: route and parameter identifiers, reset flags, lengths,
dictionaries, model descriptions, padding, checksums, termination, and the
segment's share of container framing. With an explicitly accounted global
header and footer, the additive objective is

```text
L(P,A) = L_global + sum_r b(t_r, t_{r+1}, a_r).
```

The exact recurrence is then

```text
D[0] = L_global_prefix
D[j] = min_{0 <= i < j, a in A(i,j)} D[i] + b(i,j,a)
```

with the footer added once at `j=n`. This is a shortest path in a directed
acyclic graph. A boundary count or prior can be included only when its code
length is additive per edge, or when sufficient extra state is added to the
recurrence. For example, a code for `k` followed by an enumerative code for the
`k-1` boundaries depends on `k`; a position-only recurrence must either carry
`k` or evaluate each `k` separately.

Summing complete one-segment archive sizes is usually wrong because it charges
global framing repeatedly. Summing internal payload sizes is also wrong because
it omits the framing that makes the partition decodable. The reference must
attribute the actual target wire format exactly, then materialize the winning
complete archive as a cross-check.

### Stateful form

Let `s` include all encoder and decoder state that can change later costs. A
stateful exact recurrence has the form

```text
D[j,s'] = min_{i,s,a : T(s,x[i..j),a)=s'}
              D[i,s] + b(i,j,a,s).
```

State can include retained source history, dictionary contents, predictor/model
counts, recent offsets, entropy tables, transform state, and any queued reset
decision. Two paths reaching the same byte position are interchangeable only
when their complete future-relevant states are identical. Comparing them by
position, history length, or a hash without collision resolution is insufficient.

In many practical compressors the state space makes this recurrence infeasible.
That changes the implementation strategy, not the definition of the exact
reference. A beam or learned boundary policy is an approximation and must be
measured against an exhaustive small reference.

## 2. Ferragina, Nitto, and Venturini

[Ferragina, Nitto, and Venturini, *On optimally partitioning a text to improve
its compression*](https://arxiv.org/pdf/0906.4692) define the cost of a
partition as the sum of `|C(T_i)|` over independently compressed contiguous
parts. They assume `C(alpha)` is prefix-free so concatenated parts can be
decoded sequentially. Their exact recurrence is the position-only dynamic
program above; naively it evaluates quadratic many substrings and can take
cubic time when each compression is linear in substring length.

Their faster result is more specific than “segmentation has a near-linear
approximation”:

- Edge costs are independent substring costs.
- The pruning proof uses positive costs monotone under substring extension and
  containment. The paper calls this Fact 1 and retains cost-threshold edges.
- The retained graph has `O(n log_{1+epsilon} n)` edges and its shortest path is
  within a factor `1+epsilon` of the full graph's path.
- Efficient edge generation uses incrementally maintained entropy-based cost
  functions. The paper derives results for zero-order and fixed-order empirical
  entropy estimates, and a separate page-aligned BWT setting.
- Its paper-level complexities are `O(n log_{1+epsilon} n)` time and `O(n)`
  space for the stated entropy-cost cases, with a modified logarithmic factor
  when the base compressor has a maximum block size.

These assumptions do not automatically hold for complete CIX candidates.
Appending data can change a selected route, table representation, byte
rounding, or framing and can make the physical output smaller. Starting a
substring later can also change such choices. An entropy estimate can preserve
the paper's monotonicity while disagreeing with the complete archive ordering.
The paper itself distinguishes entropy estimates from a later restricted case
using real BWT-compressor sizes.

Consequently, its threshold pruning is valid for CIX only after all of the
following have been proved for the exact edge cost being pruned:

1. path independence;
2. positive, containment-monotone costs;
3. prefix-decodable concatenation or equivalent paid framing;
4. the same candidate set and wire costs in the reference and materialized
   archive.

Without those proofs, the paper remains useful as an additive baseline and as
an approximation design, but it is not a correctness certificate for a CIX
selector.

## 3. Partition Tree Weighting

[Veness, White, Bowling, and Gyorgy, *Partition Tree
Weighting*](https://arxiv.org/pdf/1211.0587) solve a different problem. Their
base `rho` is a probabilistic data-generating source: for every finite string it
defines compatible probability mass functions satisfying

```text
rho_n(x[1..n]) = sum_y rho_{n+1}(x[1..n] y).
```

This gives causal next-symbol probabilities and a chain rule. PTW weights a
restricted class `C_d` of binary temporal partitions:

```text
PTW_d(x[1..n]) =
    sum_{P in C_d} 2^(-Gamma_d(P)) product_{(a,b) in P} rho(x[a..b]).
```

`Gamma_d(P)` is the number of non-maximum-depth nodes in the partition tree.
The weights form a valid prior. Its recursive half “do not split” and half
“split” identity avoids enumerating the doubly exponential partition family.
For `d=ceil(log2 n)`, the paper's algorithm uses `O(n log n)` time and
`O(log n)` structural space, in addition to the active base-model instances and
their storage. It can be updated online in `O(log n)` time per symbol. The
unknown-length construction increases the tree depth at powers of two and adds
an `O(log n)` ideal-code penalty relative to the corresponding fixed depth.

For any one partition in `C_d`, Proposition 1 gives

```text
-log PTW_d(x) <= Gamma_d(P) + sum_{(a,b) in P} -log rho(x[a..b]).
```

Thus `Gamma_d(P)` is a real prior/model-selection charge in ideal bits. PTW is
a mixture code, not an algorithm that finds the minimum-size physical archive
and transmits its partition. Its redundancy theorem additionally assumes a
base-model redundancy bound that is nonnegative, nondecreasing, concave, and
zero at length zero. Those conditions are needed for that theorem, although the
mixture definition itself only requires a valid coding distribution.

### Compatibility rule for CIX experts

A CIX mechanism can participate directly in such a mixture only if it exposes
a normalized causal distribution over the **same next-symbol sample space**
for every history used by the mixture. The component distributions need not
have identical supports, but the resulting mixture must assign positive mass
to every source sequence the format accepts. A full-support component or a
common escape construction is a usual way to guarantee this. The
arithmetic/range decoder must reproduce the same finite-precision probability
updates.

The following are not interchangeable with PTW experts without another proof:

- final archive byte counts or selector scores;
- whole-block transforms that require future symbols before defining the next
  original-byte probability;
- routes whose coded alphabets or symbol orders differ;
- candidates whose segment decoder requires an untransmitted choice;
- estimators that do not sum to one.

A selector may compare the physical PTW archive with other physical route
archives. That outer comparison is ordinary model selection and must pay a
route identifier. It is not the same operation as inserting those archives into
the PTW probability sum.

Ideal `-log` results also do not by themselves establish a physical win. A CIX
experiment must count probability quantization, range-coder initialization and
termination, model identification, stream length, and container alignment.

## 4. RFC 8878 as a concrete state-dependence case

[RFC 8878](https://www.rfc-editor.org/rfc/rfc8878.html) makes the reset boundary
explicit. Multiple Zstandard frames can be concatenated, and each frame is
independent of other frames, given any dictionary that its header requires. A
standard frame pays a 4-byte magic number, a 2--14 byte frame header, one or
more data blocks, and an optional 4-byte content checksum.

Blocks inside a frame are deliberately different:

- each has a 3-byte block header;
- block content is bounded by the smaller of `Window_Size` and 128 KiB;
- a block can be decoded before its successor, which enables streaming;
- a compressed block may depend on prior decoded bytes up to `Window_Size`,
  recent offsets, a prior Huffman tree, and prior FSE tables;
- `Treeless_Literals_Block` and `Repeat_Mode` are corrupt when the required
  prior table is unavailable;
- the window descriptor communicates a decoder memory requirement, and a
  decoder may reject a frame beyond its authorized limit.

Therefore a Zstandard block boundary is not an independent edge. Moving one
boundary can change later matches, recent offsets, and reusable table costs.
Only a new frame, or a separately specified reset operation with equivalent
wire semantics, creates the fixed initial state required by the simple
additive recurrence. A required dictionary must be a fixed shared condition or
its bytes and identification must be charged. Scoring each block by compressing
it alone would discard the very cross-block savings of the stateful format;
scoring it as part of one chosen prefix would make the edge depend on the path.

The RFC specifies decoding semantics and framing, not an encoder's parsing or
boundary-search heuristic. It supports the state-dependence diagnosis but does
not establish an optimal Zstandard segmentation algorithm.

## 5. Valid exact reference and pruning rules

### Exact small reference

For a bounded source of `n` atomic units, the reference should enumerate all
`2^(n-1)` boundary subsets, all legal reset/preserve choices, and the permitted
route/parameter actions. For every path it should:

1. transition the exact decoder-visible state;
2. account for complete physical bits, including the common header/footer
   exactly once;
3. materialize the complete winning archive;
4. decode it in a fresh process and verify the exact source hash;
5. retain tied winners so deterministic tie-breaking can be checked separately.

If a reset-only subset is extracted, compare exhaustive enumeration with the
additive dynamic program. Equality is a qualification test for edge accounting,
not merely for payload estimates. Then compare any adaptive/approximate policy
with this oracle and classify losses as candidate-generation, cost-estimation,
pruning, state-merging, or tie-breaking errors.

### Safe pruning

The following criteria are valid when their premises are recorded:

- **Admissible lower bound:** prune a partial path only when
  `cost_so_far + proven_lower_bound >= incumbent`. Zero future payload plus
  unavoidable known framing is safe but weak. A sampled score or entropy
  estimate is not a lower bound unless proved for every legal remaining route.
- **State dominance:** at the same input position and the same complete
  future-relevant state, retain only the lowest-cost path. No dominance follows
  from position alone. Hashes can index state but require equality resolution.
- **Immutable emitted prefix:** physical bytes already emitted can be a lower
  bound only when no finalization can rewrite, remove, or amortize them and all
  remaining costs are nonnegative.
- **Restricted candidate proof:** min/max segment lengths, permitted boundary
  sites, or a route shortlist define a smaller oracle. Results must be labelled
  for that restricted space; they cannot certify the unrestricted optimum.
- **Ferragina threshold pruning:** use only after proving its additive,
  positive, monotone edge assumptions for the exact cost in question.

Unsafe pruning examples include “high entropy, so skip duplicate discovery,”
discarding a path with a more useful dictionary because its prefix is larger,
and treating an independently recompressed block size as the marginal cost of a
history-preserving block.

## 6. Required staged programme

| Stage | Work | Gate before advancing |
|---|---|---|
| 1. Audit | Inventory every boundary type and all state crossing it: history, model counts, tables, offsets, dictionaries, checksums, framing, buffering, and footer behavior. | Each current candidate is classified as reset/additive, stateful, or causal-distribution; unknowns remain blockers. |
| 2. Exact small reference | Exhaustively enumerate boundaries, actions, and states on deterministic tiny inputs; materialize complete archives and independently decode them. | Exhaustive and additive-DP answers agree on the proven reset-only subset; malformed and truncation behavior is explicit. |
| 3. Adaptive policy | Add a bounded causal boundary policy or shortlist and compare it with the small oracle. Charge analysis, decision signaling, and latency. | Misses are attributed to generation, scoring, pruning, or state merging; no held-out tuning. |
| 4. Sharing | Permit one explicitly represented history/table/dictionary sharing mechanism across boundaries. | State transition, memory bound, reset semantics, and decoder reproduction are exact; comparison includes the reset control. |
| 5. One extension | Select one additional segmentation mechanism from measured failures. | Predeclare hypothesis, control, resource bound, complete cost, and promotion criterion. |

This order prevents a fast heuristic from becoming the de facto reference and
prevents sharing gains from being misreported as boundary-placement gains.

## 7. Review blockers and later hardening

### Blockers

1. A position-only dynamic program cannot certify a stream that preserves
   history or model/table state across candidate boundaries.
2. A segment edge cost that omits or duplicates global framing cannot optimize
   complete archive size.
3. Ferragina-style edge pruning cannot be imported until exact CIX edge costs
   satisfy the required monotonicity and path-independence properties.
4. PTW cannot directly mix arbitrary CIX routes, transforms, or final byte
   counts; each participant must first be a compatible causal coding
   distribution over common symbols.

### Later hardening

- Define canonical state serialization for oracle diagnostics so equal-state
  dominance is reviewable.
- Record both ideal probability length and actual finite-precision archive size
  for any PTW prototype.
- Add overflow-checked accounting for bit and byte costs before scaling beyond
  the exact-small reference.
- Report oracle coverage explicitly when the atomic boundary grid, action set,
  or state space is restricted.

## Sources and reading scope

- Paolo Ferragina, Igor Nitto, and Rossano Venturini, 2009,
  [*On optimally partitioning a text to improve its
  compression*](https://arxiv.org/abs/0906.4692). Reviewed the formal cost and
  dynamic program, monotonicity and threshold-edge pruning proof, incremental
  entropy-cost machinery, stated complexity, and the restricted real-size BWT
  discussion.
- Joel Veness, Martha White, Michael Bowling, and Andras Gyorgy, 2012,
  [*Partition Tree Weighting*](https://arxiv.org/abs/1211.0587). Reviewed the
  coding-distribution compatibility definition, temporal partitions, PTW prior
  and recursion, online algorithm and resources, best-partition inequality,
  redundancy assumptions, and unknown-length construction.
- IETF, 2021, [RFC 8878, *Zstandard Compression and the `application/zstd`
  Media Type*](https://www.rfc-editor.org/rfc/rfc8878.html). Reviewed the frame
  and block definitions, frame/header/checksum structure, window descriptor,
  block limit, compressed-block prerequisites, treeless literals, sequence
  repeat mode, and streaming/bounded-storage statements.
