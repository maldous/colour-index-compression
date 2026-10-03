# Addendum prior art: weighted models, shifted reuse, learned abstractions and noise

**Status:** literature and claim-scope audit only. This addendum preserves the
earlier evidence and does not implement syntax, run a codec, change production
code, or make a novelty or legal conclusion.

**Scope:** this review addresses the surviving proposals in
[ADDENDUM-DELTA.md](ADDENDUM-DELTA.md): paid exceptions, paid nonuniform
record-use models, restricted shift-aware sharing, and an exactly indexable
superset. It supplements rather than replaces [sdl-prior-art.md](sdl-prior-art.md).

## Findings before another representation is implemented

1. **Uniform constrained rank is established.** Cover gives lexicographic
   rank/unrank for a finite subset using exact prefix-completion counts,
   including fixed-weight and empirical Markov examples
   ([Cover 1973](https://isl.stanford.edu/~cover/papers/transIT/0073cove.pdf)).
2. **Hard logical support plus nonuniform probabilities is established.**
   A PSDD parameterizes an SDD so that positive probability is assigned exactly
   to the models of its logical base; its decision parameters are contextual
   probabilities and evidence probabilities are evaluated in time linear in
   the PSDD size
   ([Kisa et al. 2014](https://web.cs.ucla.edu/~guyvdb/papers/KisaKR14.pdf)).
3. **Using tractable probabilistic circuits for an actual lossless bitstream is
   established.** Liu, Mandt and Van den Broeck derive sequential conditionals
   from marginals and feed them to a streaming entropy code. Their accelerated
   algorithm has the stated $O(\log D\,|p|)$ bound only for smooth,
   structured-decomposable, balanced PCs under a constructed variable order
   ([Liu et al. 2022](https://arxiv.org/pdf/2111.11632)).
4. **Sharing a template across shifted variable sets is established.**
   VS-SDD stores a DAG node with an offset and shares functions equivalent under
   the paper's restricted vtree-preserving variable shifts
   ([Nakamura, Denzumi and Nishino 2020](https://drops.dagstuhl.de/storage/00lipics/lipics-vol160-sea2020/LIPIcs.SEA.2020.22/LIPIcs.SEA.2020.22.pdf)).
5. **Corpus-derived exact reusable abstractions and paid definitions are
   established.** Stitch searches a DSL top down for parameterized syntax
   abstractions, includes abstraction cost in its objective, rewrites exact
   matches, and uses sound branch-and-bound pruning
   ([Bowers et al. 2023](https://mlb2251.github.io/stitch.pdf)).
6. **Learning parameterized constraint templates in the presence of noisy
   training constraints is established as an approximate acquisition task.**
   GenCon classifies candidate constraints, extracts positive decision rules
   when possible, or generates and tests the entire candidate bias
   ([Tsouros et al. 2024](https://arxiv.org/html/2412.14950v1)).
   Its precision/recall objective is not an exact lossless code.
7. **Structured sparse PC inference is established as a model-efficiency
   technique.** Monarch PCs replace dense sum-block matrices with structured
   sparse maps. This reduces a two-layer hidden-size-$h$ block from
   $O(h^2)$ to $O(h^{3/2})$ parameters/FLOPs and generalizes to
   $O(dh^{1+1/d})$
   ([Zhang et al. 2025](https://arxiv.org/pdf/2506.12383)).
   The paper reports density estimates and generation/inference costs, not a
   complete CIX-style archive with transmitted model bytes.

The surviving CIX work is therefore an engineering question: can a small,
input-derived, decoder-complete model and its exact corrections beat the
strongest direct representation after model, parameter, rank, exception,
framing, construction, and decoder costs are charged?

## Exact overlap of the surviving proposals

| Surviving proposal | Closest established mechanism | Overlap level | CIX question which remains |
| --- | --- | --- | --- |
| Hard model plus paid exceptions | Two-part model/data descriptions; Cover ranking for the exception-position subset; ordinary residual/escape coding | The principle and position enumeration are established. GenCon is only a comparator for noisy model discovery. | Which bounded exception representation produces the smallest complete archive against dictionary/residual and raw controls? |
| Paid record-use histogram | Cover/type-class enumeration; decrementing remaining-count arithmetic | Exact same model at the ideal payload level. | Finite count-table, selector, rounding and framing quality in the current CIX wire. |
| Context-conditioned nonuniform use | PSDDs and probabilistic circuits followed by arithmetic/rANS coding | Direct antecedent, including logical support, contextual weights and sequential conditionals. | Whether a small input-derived model still wins after structure and quantized weights are transmitted. |
| Shift-aware template sharing | VS-SDD offsets; grammar/library abstractions; ordinary parameterized templates | Direct antecedent for restricted variable shifts and exact reusable syntax. | Whether a deliberately smaller CIX wire beats direct template+offset, packed atoms and compiled-diagram controls. |
| Automatic reusable-component discovery | Stitch corpus-guided top-down synthesis with a paid abstraction and arguments | Direct algorithmic analogue; applying actual byte cost is an engineering adaptation. | Whether bounded source-byte discovery finds wins on frozen held-out inputs without hidden semantic features. |
| Exactly indexable relaxed superset | Cover finite-set rank plus the standard two-part model tradeoff; knowledge compilation for exact count | Established construction. | Whether the saved model bytes exceed the larger exact rank and compiled-decoder cost. |
| Sparse large probabilistic model | Monarch-parameterized PCs | Direct throughput/memory antecedent for PC sum blocks, not for compressed representations. | Only relevant after profiling shows that a production-sized PC is both affordable and smaller after complete model accounting. |

## Method-level comparison

| Source | Representation and method | Relevant complexity or qualification | Exact overlap with the CIX addendum | What it does not supply |
| --- | --- | --- | --- | --- |
| Cover 1973 | An ordered finite set $S$; rank is accumulated from exact counts of completions under lexicographically earlier prefix choices. The inverse selects each next symbol from the same counts. | Efficiency depends on obtaining exact prefix-completion counts. The paper explicitly notes that loose upper bounds can retain invertibility while losing compression. It encodes empirical Markov statistics before the within-class rank when they are not known. | Exact set plus rank; exact histogram/type rank; exactly countable superset. | A cheap language for discovering or describing arbitrary $S$, model selection, archive framing, or noise handling. |
| Knowledge-compilation map | NNF target languages restricted by decomposability, determinism, decision structure, smoothness, and ordering. | Determinism plus decomposability enables polynomial model count; stronger restrictions reduce succinctness. Conditioning and Boolean Apply support vary by language ([Darwiche and Marquis 2002](https://arxiv.org/pdf/1106.1819)). | Required control for compiling a predicate grammar into something countable and conditionable. | A guarantee that an arbitrary compact source formula compiles compactly; a compressor wire format. |
| PSDD | A normalized SDD base fixes logical support. Local normalized weights parameterize decisions and terminal variables. A model has positive probability iff it satisfies the base. | Evidence and all literal marginals are computed in linear passes over the PSDD. Given a fixed structure and complete data, maximum-likelihood parameters are closed-form contextual counts; structure learning is separate and harder. | Hard constraints plus context-conditioned nonuniform weights; a faithful control for “conditional histograms on a shared constraint DAG.” | Per-archive model serialization, quantized coding probabilities, exception coding for objects outside the base, or input-only structure-search cost. |
| Lossless PC compression | Arithmetic/rANS-style sequential coding uses cumulative conditionals obtained as quotients of PC marginals. Cached/top-down values avoid reevaluating the full PC for each variable. | Naive marginal evaluation is $O(D|p|)$. The $O(\log D\,|p|)$ result assumes a smooth, structured-decomposable, balanced PC and a particular variable order. Reported model parameter counts range into millions and are separate from codeword bitrate. | Direct antecedent for a nonuniform probabilistic-circuit payload route and incremental conditional evaluation. | Evidence that a learned PC is worth transmitting inside one generic archive. The experiments train models over datasets; no complete model-plus-codeword archive cost is reported. |
| VS-SDD | An SDD-like DAG node is paired with an integer offset. Vtree nodes have preorder IDs, and edges store ID differences so a subfunction can be reused at isomorphic vtree locations. | Normalized/trimmed compressed forms have canonicity results; Apply is $O(|\alpha||\beta|)$. The paper proves exponential separation for a constructed family. Unweighted model counting stays polynomial; arbitrary weighted counting may require counters corresponding to expanded SDD nodes. | Direct antecedent for repeated record/lane templates which are identical under a permitted shift. | General affine renaming, arbitrary parameter substitution, near matches, or free wire savings. Offsets, vtree, nodes and references remain physical data. |
| Stitch | Corpus-guided top-down synthesis searches parameterized DSL abstractions. Partial-pattern matches overapproximate descendants' matches, enabling branch-and-bound. Exact rewriting uses arguments for varying subtrees. | Utility is $-cost(A)+cost(P)-cost(rewrite(P,A))$. The definition cost is charged. Overlapping rewrites are resolved by a linear-time dynamic program for this symbolic objective. The search is anytime; repeated library growth learns one abstraction then rewrites before the next iteration. | Automatic exact reusable-template discovery, arguments as exact residuals, paid abstraction definitions, and bounded/anytime search. | A physical prefix code or byte archive. Its configured symbol-cost function is not automatically complete wire length, and greedy repeated library growth is not a proof of a globally smallest library. |
| GenCon | Candidate constraints become labeled feature vectors. A classifier predicts membership; decision rules can be converted to relation/partition/sequence specifications, otherwise every generated candidate is tested. | The candidate bias applies detected relations to all scopes. Robustness is evaluated by precision/recall under randomly injected 5–20% false-positive or false-negative training constraints. It assumes a supplied parameterized vocabulary and feature design. | A comparator for inferring repeated parameterized constraint templates and for measuring discovery under noisy observations. | Exact support, exact count/rank, lossless correction, paid model bytes, or a generic byte-stream policy. A classifier error cannot be ignored by a decoder. |
| Monarch PCs | Sum blocks use interleaved structured sparse tensor contractions derived from circuit multiplication rather than dense matrices. | Dense blocks cost $O(h^2)$. Two-layer Monarch costs $O(h^{3/2})$; $d$ layers cost $O(dh^{1+1/d})$. Training memory also contains $O(dnhB)$ hidden-state caches, which can dominate. | A future throughput/memory control if a measured CIX hotspot is a sufficiently large PC sum block. | A new logical model, exact finite-set description, archive representation, or measured lossless compressor. Its Text8 and image results are likelihood/BPC/BPD, and the learned parameters are not charged as per-file archive bytes. |

## Uniform support, histograms, and probabilistic weights

These three payload models must be kept separate.

Let $M$ dictionary/model values be used in $s$ record positions with exact
usage counts $h_1,\ldots,h_M$.

### Uniform record use

If every ordered length-$s$ sequence over the $M$ values is permitted, the
ideal payload is

    log2(M^s) = s log2 M.

### Exact histogram-conditioned rank

If the histogram is transmitted or otherwise fixed, the type class has

    s! / product_i h_i!

members. Its uniform ideal payload is the logarithm of that quantity. This is
Cover-style enumerative coding. The histogram selector, each count, its order,
rounding, and framing are additional costs.

A remaining-count arithmetic coder which decrements $h_i$ after each symbol
assigns every member of this same type class equal probability. Its ideal
payload is the same as the exact rank. It is a coder implementation control,
not a second modeling gain.

The same uniform-support control can be expressed on an SDD/PSDD. For a
decision node with disjoint exhaustive elements $(p_i,s_i)$, let
$m_i=MC(p_i)MC(s_i)$ and set its branch probability to
$m_i/\sum_j m_j$; use probability $1/2$ at an unconstrained Boolean terminal.
Induction over the decomposable decision structure makes every model of the
base equiprobable. These weights need not be transmitted if the decoder
normatively recomputes exact model counts from the paid certificate. Learned
or quantized nonuniform weights are a different model and must be paid.

### Fixed nonuniform probabilities

A fixed probability vector $q$ assigns a particular sequence ideal length

    -sum_i h_i log2 q_i.

The maximum-likelihood choice $q_i=h_i/s$ gives $sH(h/s)$, which is not the
same finite code as selecting an exact histogram and then ranking within its
type class. A complete comparison must charge the probability precision or
count parameters and use the same entropy-coder termination. A PSDD or general
PC can further condition $q$ on circuit context; that is a nonuniform model
gain and must not be attributed to logical intersection or SDL syntax.

### Required four-way control

For the same dictionary, same sequence, and same framing, materialize:

1. uniform use over $M^s$;
2. exact paid histogram plus uniform multinomial rank;
3. the same decrementing probabilities through the production range coder;
4. a fixed or context-conditioned probabilistic model with all weights,
   quantization and model structure paid.

The first isolates dictionary structure, the second count information, the
third finite coder effects, and the fourth genuine nonuniform prediction.

## Noise and exceptions must be exact data

Suppose a hard model admits record set $S$ but an input contains exceptions at
positions $E$. At minimum an exact archive must determine:

* the model and its parameters;
* record count $r$ and exception count $e$;
* the exception-position subset, costing an ideal
  $\log_2 {r\choose e}$ before rounding unless a different paid position model
  is used;
* every exception value or exact residual under a declared universe;
* ranks or codes for the nonexception records;
* ordering, framing, padding, integrity, and termination.

False positives and false negatives have different effects:

* **Extra admitted values** enlarge a hard uniform state space or consume
  probability mass in a soft model.
* **Rejected observed values** make a hard model unable to encode the input
  and therefore require an escape or a relaxed exact superset.

GenCon's noise experiments show that a classifier can recover useful templates
despite noisy constraint labels, but precision and recall below 100% are
acceptable for its acquisition objective. They are not acceptable archive
semantics. If such a learner proposes a CIX model, the encoder must turn it
into an exact deterministic model and serialize every correction. Encoder and
decoder must not independently rerun a nondeterministic learner.

A PSDD assigns zero probability outside its SDD base. Smoothing its branch
weights does not admit a logically excluded object. CIX therefore needs one of:

1. an explicit escape mixture with positive probability for the residual
   universe;
2. a paid exception mask/list plus raw or modeled exception values; or
3. an exactly countable relaxed superset.

The direct controls are raw, an explicit dictionary plus residuals, the
existing RDIC/exact-only candidates, and the strongest full-support
probability model available under the same resource cap.

## Faithful restricted controls for the surviving proposals

### Shift-aware shared models

Do not implement all VS-SDD machinery first. Freeze a restricted comparator
which represents one exact predicate template plus permitted record/lane
offsets. Compare, on identical truth sets and orders:

* fully repeated packed predicates;
* ordinary hash-consed DAG/SDD nodes;
* direct template plus offset table;
* VS-SDD-style base node plus vtree-relative shifts;
* an explicit member set/dictionary;
* canonical ROBDD or SDD certificate where bounded.

Use four cases: no reuse, exact same-variable reuse, exact shifted reuse, and
near shifted reuse with paid exceptions. Store every template parameter,
offset, boundary rule, vtree/order choice, reference, and exception. VS-SDD's
result applies only to its defined substitution equivalence over isomorphic
vtree structures; it must not be cited for arbitrary affine or semantic
equivalence.

### Automatically discovered reusable abstractions

A faithful Stitch control uses a tiny frozen predicate DSL and searches
parameterized exact abstractions over the model descriptions. It must:

* charge the abstraction body, formal parameters, definition identifier,
  application identifiers, arguments, and unmatched literals;
* use the actual archive code length as utility rather than Stitch's
  experimental symbolic weights;
* report the finite grammar, node/depth/search budget, rejected candidates and
  early-stop condition;
* compare one-step selection with the final iterated library;
* retain packed-flat, shared-table, direct dictionary, ROBDD/SDD, and raw
  controls.

This would be an adaptation of established library learning. A useful result
could still be CIX engineering evidence; it would not establish a new
abstraction-learning principle.

### Learned noisy constraint templates

A faithful GenCon-inspired control may rank candidate templates or propose
partition/sequence rules, but its output is only a proposal. The physical
candidate must be reconstructed as a deterministic exact model, its entire
rule set paid, and every discrepancy from the observed records encoded. Report
discovery precision/recall separately from archive bytes. The smallest bounded
version uses the already frozen grammar and synthetic clean/single/sparse/
absent exception grid; no domain attributes, filename, corpus identity, or
hidden training model may enter the policy.

### Probabilistic-circuit payload

Before any general PC implementation, use one bounded structure shared by all
controls:

1. uniform probabilities over the exact SDD support;
2. PSDD branch probabilities derived from paid record/context counts;
3. a direct context histogram with the same information;
4. uniform exact rank through the same support;
5. escape/full-support variants for exceptions.

Use fixed-point integer cumulative frequencies and serialize their precision
and normalization. Floating training probabilities are not a decoder contract.
The model must fit the existing memory cap and its structure/weights must be in
the archive unless they are fixed generic decoder code. Liu's million-parameter
dataset-trained models and Monarch's very large hidden states are inappropriate
per-file controls unless their full model cost is paid or a separately
authorized shared-model setting is declared.

### Exactly indexable superset

For a proposed superset $T\supseteq S$:

* prove and independently recompute $|T|$ exactly;
* rank/unrank under one canonical order using arbitrary-precision integers;
* pay the full description of $T$ and any compiled certificate;
* compare $L(T)+\lceil\log_2|T|\rceil$ with the exact model, raw, direct
  dictionary/residual, and full-support probability controls;
* reject an estimator or approximate model counter as an index source.

The superset is useful only if its cheaper model description exceeds the extra
rank cost. This is a conventional model-cost versus data-cost tradeoff.

## Smallest bounded addendum test

The smallest useful extension of the existing eight-variable/256-object oracle
needs no corpus run:

1. Freeze the current atom grammar and add only a record-index shift operator
   whose valid offsets and boundary behavior are explicit.
2. Generate clean, one-exception, sparse-exception, and absent-opportunity
   record sequences from predeclared seeds.
3. Exhaustively enumerate each hard support and hash it; use this as the
   independent semantic oracle.
4. Materialize packed-flat, direct template+offset, VS-SDD-style shift, ROBDD,
   explicit set, raw, dictionary/residual, and exact exception forms.
5. For each exact support, encode uniform rank, paid histogram rank,
   decrementing-count range coding, and a bounded paid PSDD/context model.
6. Decode in a fresh process and test malformed node references, cycles,
   offsets, counts, probability totals, exception ranks, residual lengths,
   truncation and trailing bytes.
7. Record complete bytes by model/certificate/weights/exceptions/payload/frame,
   plus discovery, compile, count, rank, encode and decode resources.

Promotion requires a complete archive win against the shortest exact
same-information control. A likelihood, symbolic compressivity score, node
count, or uncharged pretrained-model bitrate is not promotion evidence.

## Separate patent claim review: US 12,456,231 B2

This section records the text observed in the published patent only. It is not
a validity, infringement, freedom-to-operate, ownership, jurisdictional, or
legal-status opinion.

The Google Patents record for
[US 12,456,231 B2](https://patents.google.com/patent/US12456231B2/en) lists a
29 April 2022 priority date, a 28 October 2025 grant/publication, and an active
status. Google expressly warns that its legal status is an assumption; current
status and the complete file history require official USPTO review.

There are two independent claims:

* **Claim 1**, a method receiving image data whose pixels are variables,
  sequentially compressing variables with conditionals computed through at
  least one marginal, initializing every PC unit probability to one, defining
  per-iteration evaluation sets, evaluating them bottom up to a target
  probability, and generating a bitstream with a streaming code.
* **Claim 11**, a non-transitory storage medium whose instructions perform
  substantially the same steps.

Claims 2–10 and 12–20 add cumulative left/right probabilities, marginal
quotients, one-by-one prefix marginals, average partial reevaluation,
feedforward evaluation, minimum/correct evaluation sets, elimination of units,
and weighted reconstruction of the root probability.

The following technical distinctions are relevant to counsel, but they are not
legal conclusions:

| CIX concept | Relation to the claim text |
| --- | --- |
| Uniform finite-set rank/unrank from exact combinatorial counts | Does not inherently require a probabilistic circuit, PC marginals, per-step evaluation sets, or a streaming probability code. |
| PSDD/PC used only as an encoder-side candidate scorer | Does not by itself describe generation of the claimed compressed bitstream, but actual use must be reviewed as a whole. |
| Generic byte PC route using sequential conditional marginals and partial PC reevaluation | Technically close to the method described by claims 1–10. The independent claim expressly recites image pixels, but claim construction, application to image inputs, and equivalents require patent counsel. |
| Reimplementation of the Liu 2022 accelerated PC compressor | Tracks the patent's evaluation-set and marginal-conditioning language closely; this observation is not a legal conclusion. |
| Monarch matrices inside a PC | Changes parameterization and inference cost; it does not by itself remove the sequential-PC-compression elements if those are otherwise used. |

The Liu arXiv paper was publicly submitted in November 2021, before the listed
patent priority date, and the patent itself cites that work. No inference about
validity follows: inventor disclosures, grace periods, prosecution, claim
construction, ownership, and jurisdiction require specialist review. The current user directive already keeps all experiments isolated and
prohibits production integration. This claim-text review adds no clearance,
infringement conclusion or new production approval requirement.

## Reading coverage and limits

The instruction was to read relevant methods and complexities beyond abstracts.
The following sections were reviewed:

* **Kisa et al. 2014:** PSDD syntax/distribution, base and parameter semantics,
  context-specific independence, evidence/marginal algorithms, complete-data
  parameter learning, and stated structure-learning boundary.
* **Liu et al. 2022:** probability-circuit definitions, sequential coding
  reduction, partial evaluation algorithm, formal balance/structure
  assumptions, complexity proof outline, HCLT construction, and experiment
  setup/model sizes.
* **Nakamura et al. 2020:** VS-SDD definition, offsets and identical-vtree
  rule, canonicity, size result, Apply complexity, supported queries, weighted
  counting caveat, implementation, and experiment discussion.
* **Bowers et al. 2023:** CTS match semantics, branch-and-bound/pruning,
  rewriting and overlap handling, exact symbolic utility, anytime behavior,
  iterative library construction, and evaluation cost settings.
* **Tsouros et al. 2024:** constraint-specification formalism, feature
  parameterization, rule extraction, generate-and-test, candidate-bias
  generation, false-positive/negative noise injection, metrics, and appendix
  feature/tuning details.
* **Zhang et al. 2025:** PC definitions, circuit multiplication, two- and
  multi-layer Monarch construction, FLOP/parameter and training-memory
  complexities, Text8/LM1B/image methodology, and reported metrics.
* **Cover 1973:** the full short paper, including general rank/inverse,
  fixed-weight, and empirical Markov cases.
* **Darwiche and Marquis 2002:** language definitions, succinctness map,
  supported query/transform tables, model-counting conditions, and
  conditioning discussion.
* **US 12,456,231 B2:** claims 1–20 and the description sections corresponding
  to probabilistic-circuit structure, sequential compression, partial
  marginal evaluation, variable ordering, and decoding.

This was not a reproduction study. Code artifacts, complete proof appendices
where a paper delegates them elsewhere, all empirical plots, patent prosecution
history, foreign family members, continuations, assignments, claim
construction, and litigation were not reviewed. The literature search is
targeted, not exhaustive, and cannot support a broad novelty or
freedom-to-operate claim.
