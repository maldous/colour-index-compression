# Constraint-space coding: prior-theory map

**Status:** literature and theory audit only.  No implementation, experiment,
performance claim, or novelty claim is made here.

**Scope.**  “Constraint-space compression” here means describing a byte string
by a reversible constraint or model plus an index/residual within the strings
admitted by that constraint.  The sources below are primary papers or the
publisher's record of a primary paper.  This is a deliberately small map of
well-established antecedents, not an exhaustive search and not a freedom-to-
operate or novelty opinion.

## Primary antecedents

| Area | Primary source | Precise relevant result | Coverage status and consequence for a CIX claim |
| --- | --- | --- | --- |
| Enumerative coding | T. Cover, [“Enumerative source encoding”](https://doi.org/10.1109/TIT.1973.1054929), *IEEE Transactions on Information Theory* 19(1), 73–77 (1973). | Gives a source-coding construction based on enumerating sequences in a constrained set. | **Known direct antecedent.** Ranking a fixed-composition byte sequence is established enumerative coding. |
| Types | I. Csiszár, [“The Method of Types”](https://doi.org/10.1109/18.720546), *IEEE Transactions on Information Theory* 44(6), 2505–2523 (1998). | Treats length-*n* sequences as classes by empirical distribution and develops the counting method and extensions with memory. | **Known direct antecedent for fixed partitions.** A histogram-defined sequence class is a type class.  A history-dependent partition needs a path-feasibility count, not independent lane multiplication. |
| Arithmetic coding | I. Rissanen and G. G. Langdon Jr., [“Arithmetic Coding”](https://doi.org/10.1147/rd.232.0149), *IBM Journal of Research and Development* 23(2), 149–162 (1979). | Describes arithmetic coding as a general variable-rate, noiseless coding mechanism with decodability analysis. | **Known direct antecedent.** A remaining-count range coder supplies a probability assignment to an established coder. |
| MDL | J. Rissanen, [“Modeling by shortest data description”](https://doi.org/10.1016/0005-1098(78)90005-5), *Automatica* 14(5), 465–471 (1978). | Formulates modeling through a shortest description containing model structure/parameters and data described by that model. | **Known direct antecedent.** Fully serialized finite-family selection is a two-part-description policy; selector, IDs, parameters, and fallback must be coded. |
| MML | C. S. Wallace and D. M. Boulton, [“An Information Measure for Classification”](https://doi.org/10.1093/comjnl/11.2.185), *The Computer Journal* 11(2), 185–194 (1968). | Derives an information-theoretic measure for classification by viewing it as economical statistical encoding. | **Known direct antecedent.** Charging model/configuration and data is MML-consistent accounting, not proof that a portfolio is MML-optimal. |
| Algorithmic statistics | N. Vereshchagin and P. Vitányi, [“Kolmogorov’s Structure Functions and Model Selection”](https://doi.org/10.1109/TIT.2004.838346), *IEEE Transactions on Information Theory* 50(12), 3265–3290 (2004); [author manuscript](https://homepages.cwi.nl/~paulv/papers/structure.pdf). | Defines the structure function \(h_x(\alpha)=\min_{S\ni x,\,K(S)\le\alpha}\log|S|\), explicitly separating a model set from an index in it. | **Known direct antecedent for the abstract model/index form.** It is not a computable recipe because \(K(S)\) is uncomputable and the model language changes constants. |
| Contemporary algorithmic-statistics survey | A. Semenov, A. Shen and N. Vereshchagin, [“Kolmogorov Last Discovery? (Kolmogorov and Algorithmic Statistics)”](https://arxiv.org/abs/2303.13185) (2023). | Surveys the historical development of resource-bounded complexity, structure functions, and stochastic objects. | **Known related literature; partial implementation relevance.** It reinforces that “algorithmic statistics” is a pre-existing field; it does not yield a finite CIX selector. |
| Universal sequential coding | Y. M. Shtarkov, [“Universal Sequential Coding of Single Messages”](https://www.mathnet.ru/eng/ppi811), *Problems of Information Transmission* 23(3), 175–186 (1987). | Establishes a uniform redundancy formulation and bounds for specified source families, including memoryless and Markov cases. | **Known direct antecedent.** “Universal” requires a defined probability/model family and regret criterion. |
| Finite-state limits | J. Ziv and A. Lempel, [“Compression of Individual Sequences via Variable-Rate Coding”](https://doi.org/10.1109/TIT.1978.1055934), *IEEE Transactions on Information Theory* 24(5), 530–536 (1978). | Studies finite-state information-lossless encoders and asymptotic limits for individual sequences. | **Known direct antecedent.** Bounded-history models belong in a finite-state setting; the result gives no finite-block guarantee for a particular archive format. |
| Adaptive context models | J. G. Cleary and I. H. Witten, [“Data Compression Using Adaptive Coding and Partial String Matching”](https://doi.org/10.1109/TCOM.1984.1096090), *IEEE Transactions on Communications* 32(4), 396–402 (1984). | Presents adaptive partial-string-matching (PPM) coding, with a model reconstructed dynamically at both sides. | **Known direct antecedent.** Causal context prediction and decoder-synchronised adaptive state are established. |
| Graph ensembles and MDL | L. Hébert-Dufresne *et al.*, [“Network compression with configuration models and the minimum description length”](https://arxiv.org/abs/2204.08444), *Physical Review E* 110, 034305 (2024). | Counts approximate constrained network ensembles and applies MDL to a nested configuration-model family. | **Partial analogue.** It is evidence that constrained-ensemble size plus model description is established in graphs, but it does not supply a byte-string causal-context coder. |
| Algebraic model counting | A. Kimmig, G. Van den Broeck and L. De Raedt, [“Algebraic Model Counting”](https://arxiv.org/abs/1211.4475) (2012). | Generalises weighted model counting over semirings and relates evaluation to compiled circuits. | **Partial analogue.** It concerns counting/inference for logical constraints, not a complete lossless archive construction. |
| Algebraic model-counting learning | J. Maene and L. De Raedt, [“The Gradient of Algebraic Model Counting”](https://arxiv.org/abs/2502.18406) (2025). | Extends the semiring perspective to gradient-based learning and discusses tractable circuits. | **Partial and non-coding.** It does not establish a coding gain or a decoder-complete constraint-space representation. |

### Novelty-map coverage boundary

| Proposed family | Status in this audit | What remains open here |
| --- | --- | --- |
| Fixed histogram/type-class rank and remaining-count coding | **Known.** | Finite archive overhead and implementation quality remain empirical questions. |
| Externally fixed substreams and hierarchical count factorisations | **Known.** | Whether a specific header/reuse format saves complete bytes needs a matched measurement. |
| MDL/MML finite model selection | **Known.** | A particular representation language is not shown to be optimal, universal, or novel. |
| Structure functions and algorithmic statistics | **Known theory; partial engineering relevance.** | A computable bounded grammar/search is not the Kolmogorov-complexity optimum. |
| Arithmetic/range coding and finite-state/context prediction | **Known.** | Quantisation, termination, resets, and finite-block performance need exact implementation evidence. |
| Causal-context type classes as independent product lanes | **Refuted as a general identity.** | Exact counting must include feasible state paths. |
| General exact enumeration of arbitrary adaptive causal constraints | **Literature pending in this limited audit.** | A targeted search and a formal state-machine definition are required before a novelty or completeness claim. |
| Graph constrained ensembles and algebraic model counting | **Partial analogue.** | The cited work does not provide a byte-stream archive with decoder-complete instructions. |
| Combined CIX constraint grammar, search, and archive framing | **Literature pending in this limited audit.** | Direct prior-art comparison is required; no exhaustive search or novelty conclusion has been made. |

## Exact coding identities

These identities hold before finite-precision, framing, or implementation
choices.  They delimit what can and cannot be attributed to a new constraint.

### Fixed composition: rank and remaining-count coding

For an alphabet with counts \(n_a\), total length \(N=\sum_a n_a\), and a
fixed canonical symbol order, the type class has

\[
M = \frac{N!}{\prod_a n_a!}
\]

members.  A uniform rank needs \(\log_2 M\) ideal bits for the sequence after
the counts are known.  A sequential coder which assigns the next symbol
probability \(n_a^{(t)}/(N-t)\), decrements the selected count, and uses the
same known counts gives every permitted string probability

\[
\prod_{t=0}^{N-1}\frac{n_{x_t}^{(t)}}{N-t}=\frac{1}{M}.
\]

Therefore its ideal negative log probability is also \(\log_2 M\).  This is
an exact equivalence of the *ideal sequence cost* under the same uniform type
class, not byte-for-byte equivalence of implementations.

Observed archive sizes may differ because of transmitted counts, length and
mode fields, rank-width rounding, bit padding, arithmetic initialization and
termination, quantised interval choices, block boundaries, checksums, and
container framing.  These are coding costs, not evidence that one of the two
encodes a different ideal fixed-composition relationship.

### Fixed position partition

Let an externally supplied, fixed partition assign every position to a lane
\(c\), with \(N_c\) positions and counts \(n_{c,a}\).  The partition must be
independent of the symbols being encoded (for example, fixed byte offsets or a
stored label sequence).  Given that partition and all lane counts, the
admissible sequence count is

\[
M_{\mathrm{ctx}} = \prod_c \frac{N_c!}{\prod_a n_{c,a}!}.
\]

This is the exact product-class identity.  If the partition label sequence is
not fixed by the format, its full recoverable description is additional
information.  The identity does not apply merely because both encoder and
decoder can eventually derive labels from a causal history.

### History-dependent contexts are path constraints

For a causal context, the lane occupied at time \(t\) depends on the already
decoded prefix.  Its per-context symbol counts constrain a state path; the
independent-lane product generally overcounts strings because it omits
reachability, state-flow, start-state, and end-state constraints.

A two-symbol counterexample makes the distinction concrete.  Use binary
symbols, length two, initial context \(0\), and let the next context equal the
previous decoded bit.  Consider the reported context counts \(n_{0,0}=1\),
\(n_{0,1}=1\), and no occurrences of context \(1\).  Treating lane 0 as an
independent fixed partition gives \(2!/(1!1!)=2\) orders: `01` and `10`.
Only `01` is feasible: after its initial `0` the second position remains in
context 0.  In `10`, the initial `1` moves the second position to context 1,
contradicting the claimed counts.  Thus the product is two while the feasible
path set has one string.

For an order-1 Markov context, transition counts form a directed multigraph;
valid strings are Euler-like trails subject to balance, connectivity, initial
state, and final state.  General adaptive contexts can impose still richer
state-path restrictions.  Exact enumeration therefore needs an explicit
automaton/path-counting construction or a sequential probability model that
assigns mass only to feasible transitions.  The narrow literature search in
this document has **literature pending** for a general, practical exact
enumerative coder for arbitrary CIX causal constraints; no novelty conclusion
follows from that gap.

Decoder reconstruction of causal state can avoid storing a position-label
stream, but it does not make the independent-lane formula valid.  Resets,
initial history, context parameters, lane/transition-count descriptions,
escape rules, precision, and arithmetic/rank termination still need their
actual stored cost.  A context can also be worse by destroying an ordering
relationship retained by a global class.

### Hierarchical count allocation

For a partition of symbols into groups \(G_j\), with
\(N_j=\sum_{a\in G_j}n_a\), the multinomial identity is

\[
\frac{N!}{\prod_a n_a!}
= \binom{N}{N_1,\ldots,N_g}
  \prod_j\frac{N_j!}{\prod_{a\in G_j}n_a!}.
\]

Thus a lossless re-factorisation of a fixed histogram does not reduce the
ideal information required for the same class.  It can still reduce complete
bytes through a cheaper finite representation, shared/reused count metadata,
or a genuinely narrower conditional model.  It can lose through group maps,
allocation headers, tags, boundaries, and termination.  Claims of a
“hierarchical histogram gain” must identify which of these changed.

### Reversible representation plus residual

For a reversible transform/model \(T,\theta\), an archive has the generic
two-part form

\[
L(T,\theta) + L(r\mid T,\theta),
\]

where the reconstruction instructions are part of \(T,\theta\).  This is an
MDL/MML-style accounting identity, not a proof of a particular optimality
property.  Intermediate expansion is compatible with it: only the final
complete archive decides the realised length.  A pruning decision is sound
only when it uses a proved lower bound that includes all mandatory remaining
instructions and framing; an estimate-based cutoff is heuristic.

## What the theory does **not** establish

1. **No novelty inference.**  Enumerative/type-class coding, arithmetic
   coding, two-part descriptions, context models, and finite-state coding all
   predate this work.  A particular integration might be an engineering
   contribution only after a direct artifact and literature comparison; this
   document supplies neither.
2. **No computable “best constraint” theorem.**  Structure functions use
   Kolmogorov complexity and an unrestricted set language.  A finite Rust
   representation grammar and a bounded search are useful engineering
   restrictions, not an implementation of that mathematical optimum.
3. **No free selection.**  Choosing the best of \(K\) finite candidates at the
   encoder requires a decodable choice code (often at least an identifier or
   a prefix code) plus every candidate's required parameters.  Comparing
   unframed payloads is insufficient.
4. **No free adaptive state.**  A decoder can reconstruct causal state without
   storing each state value, but it must know the model/update rule, initial
   state, resets, and the exact precision/termination rules.  Independent
   blocks change the available history and can change code length.
5. **No direct finite-size guarantee from asymptotics.**  Universal and
   finite-state results are conditional on their source/model classes and
   asymptotic regimes.  They do not prove a gain for arbitrary short blocks or
   a specific implementation.

## Evidence needed for a falsifiable implementation claim

Any future constraint-space experiment should predeclare a finite candidate
set and retain the physical archive.  For each candidate it needs, at minimum:

* the model/transform identifier, parameters, dictionary or external decoder
  asset, count/state descriptions, lengths, checksums, alignment, and
  termination bytes;
* ideal probability cost, quantised-CDF or integer-interval cost when that
  coder exposes it, and actual emitted bytes as separate quantities;
* an archive-only fresh-process exact reconstruction check; and
* a matched control that has the same counts, partitions, history policy,
  block boundaries, and metadata whenever an equivalence above is being
  tested.

The existing conditional-cost mechanism evidence is useful only as an
implementation-specific check of the first identity: its fixed-count rank and
remaining-count cases must be read with their complete archive fields and
finite termination differences, rather than interpreted as a new
type-class theorem.  It does not settle conditional contexts, hierarchical
allocation, or a general representation-language search.

## Research boundary

The working hypothesis “compact reversible descriptions can improve a complete
lossless archive” is falsifiable but is not novel on the strength of these
antecedents.  The informative question is narrower: for a fixed, declared,
decoder-complete language and generic encoder policy, does a proposed
constraint lower complete stored bytes on predeclared controls and held-out
inputs after all instruction and coder costs?  A negative result is evidence
against that concrete constraint and configuration, not against the general
literature.
