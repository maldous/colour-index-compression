# URPILS reconstruction: an MDL score, not a physical codec

**Status:** primary-paper reconstruction only.  This document reads the full
15-page author-hosted PDF of Wiegand, Klakow, and Vreeken, [“What Are the
Rules? Discovering Constraints from Data”](https://vreeken.groups.cispa.de/pubs/2024/urpils-wiegand,klakow,vreeken.pdf), *Proceedings of the AAAI Conference on Artificial Intelligence* 38(8), 8182–8190 (2024),
[DOI 10.1609/aaai.v38i8.28658](https://doi.org/10.1609/aaai.v38i8.28658).
It makes no implementation, experiment, performance, or novelty claim.

## Source versions and reading boundary

I read the complete 15-page PDF supplied at the author-group URL above and
the alternate author URL
[`urpils-wiegandklakowvreeken.pdf`](https://boris-wiegand.info/wp-content/uploads/2024/01/urpils-wiegandklakowvreeken.pdf).
The downloaded files were byte-identical at review time:

```
SHA-256 28c882f12fa5d90fff8d46063c19436a52f91d0aad807c548c5e335771213650
```

They contain the nine proceedings pages (8182–8190) followed by the supplied
appendix.  Page references below give both the PDF page number and proceedings
page where applicable.  This is a source reconstruction, not an exhaustive
review of the paper's cited counting literature or supplementary source code.

The short conclusion is important: the paper defines and approximately
evaluates an **MDL score for selecting constraint models**.  It says explicitly
that it computes code lengths and is “not concerned with actual code words”
(“Minimum Description Length Principle,” PDF p. 2 / proceedings p. 8183).
It does **not** specify a physical archive, a bit-level model code, a canonical
rank/unrank of satisfying assignments, an error-code decoder, or a complete
encoder/decoder.  It is therefore a strong antecedent for constraint-model
selection and accounting ideas, but it is not a ready-made lossless byte codec.

## Problem and constraint language

The paper is about learning constraints from a data set of exemplary **Boolean
assignments**, not compressing an arbitrary byte stream.  With object sets
\(O_1,\ldots,O_k\), it defines \(X=\prod_i O_i\), an assignment
\(f_a:X\to\{0,1\}\), a model \(M=\{C_1,\ldots,C_m\}\), and the set
\(F_M\) of assignments satisfying every constraint ("Boolean Constraint
Programming," PDF p. 2 / proceedings p. 8183).

Its grammar is given in “Model Encoding” (PDF pp. 2–3 / proceedings pp.
8183–8184).  A constraint has three components
\(C=(C_V,C_F,C_T)\):

* **Variable part \(C_V\):** empty, or universal quantification over one or
  two tuples from \(X\).
* **Filter \(C_F\):** equality/inequality of tuple components, Boolean
  relation calls, numeric comparisons, negation, conjunction, and disjunction.
  Numeric expressions allow literals, numeric-relation calls, arithmetic
  operators, absolute value, floor, and ceiling.
* **Target \(C_T\):** Boolean formulas over assignment values, including a
  bounded count constraint \(\ell\leq\sum f_a(v)\leq u\).

This is a domain-specific grammar over externally supplied Boolean and numeric
relations.  It is not a grammar of byte transforms, dictionaries, residuals,
or substream layouts.  A CIX adaptation would need a separately specified
finite grammar and decoder semantics; URPILS does not supply one.

## The stated two-part score

The paper uses crude/two-part MDL (PDF p. 2 / proceedings p. 8183):

\[
\arg\min_M L(M)+L(D\mid M),\qquad
L(D\mid M)=\sum_{f_a\in D}L(f_a\mid M).
\]

For one Boolean assignment it defines the idealised data length (PDF p. 2 /
proceedings p. 8183)

\[
L(f_a\mid M)=\log |F_M|+L_N(1+e_M(f_a))+
\log { |X| \choose e_M(f_a) },
\]

where \(e_M(f_a)\) is the minimum Hamming distance from \(f_a\) to an
assignment in \(F_M\).  \(L_N\) is Rissanen's universal integer length: the
paper gives \(\log c_0+\log z+\log\log z+\cdots\), retaining positive terms,
with \(c_0=2.865064\).  The intended interpretation is: identify a valid
assignment, state the error count, then identify the erroneous Boolean values.
For a binary assignment, error locations plus the chosen valid assignment do
indeed determine the observed assignment in principle.

The model score is (same section)

\[
L(M)=L_N(|M|+1)+\sum_{C\in M}L(C).
\]

For grammar nonterminal \(A\), it recursively uses a uniform choice cost
\(\log |A|\) for a branch plus its child descriptions.  Numeric literals are
charged through \(L_R(z)=L_N(s)+L_N(\lceil z10^s\rceil)+1\), with a
user-specified precision and a smallest decimal shift \(s\) satisfying the
paper's stated threshold (PDF p. 3 / proceedings p. 8184).

### What is exact in that description, and what is only a score

The formula is a useful **description-length specification**, but not a
complete physical archive format:

* Its logarithms are real-valued ideal lengths.  The paper gives no prefix or
  arithmetic code, rounding rule, end marker, framing, model identifier, or
  bit ordering that turns every term into stored bytes.
* It does not define a canonical enumeration/rank and unrank procedure for
  \(F_M\).  Saying “an index” of a valid assignment is enough for an MDL
  objective, but insufficient for an independent decoder.
* It does not define how the nearest valid assignment achieving \(e_M\) is
  selected or reconstructed if there is a tie.
* Its later count and error quantities are often estimates.  Substituting them
  into \(\log|F_M|\) or the error code means the resulting number is not the
  actual length of any demonstrated code.

The paper calls this a lossless encoding at the level of the two-part
description.  That should not be read as evidence of a physical lossless
codec: the authors expressly distinguish their computation of lengths from
actual code words.

## Counting and error estimates

“Formal Problem Definition” states that exact \(|F_M|\) is solution counting
for a Boolean formula and hence #P-complete (PDF p. 3 / proceedings p. 8184).
The abstract says the relevant model counting is “#P-hard to approximate,” but
the body passage establishes the exact-counting statement and then motivates
approximations; this reconstruction does not elevate the abstract wording into
a general approximation-hardness theorem for every proposed constraint grammar.

The “Estimating the Number of Valid Assignments” subsection (PDF pp. 3–4 /
proceedings pp. 8184–8185) makes the following concrete choices:

1. Convert the model to CNF, with a Boolean variable per possible assignment
   parameter combination.  Split disconnected constraint-graph components and
   multiply their counts.
2. Enumerate exactly only when a component has fewer than five variables.
3. For clauses containing at most two variables, the paper *asserts* that the
   valid-assignment count corresponds to independent-set counting on its
   constraint graph, then uses the degree expression
   \(\prod_{v\in V}(\deg v+2)^{1/(\deg v+1)}\) as a lower bound.  That
   correspondence is not a general fact about arbitrary mixed-polarity 2-CNF:
   an implication or a negated literal needs an additional monotone/switchable
   sign reduction before an independent-set formulation is valid.  The paper
   does not state those restrictions in this passage.  This audit therefore
   records it as the paper's heuristic counting step, not as a general
   2-CNF-to-independent-set theorem.
4. For a *single* equality count \(\sum_{i=1}^n x_i=a\), use
   \({n\choose a}\); for an inequality range, sum the corresponding binomial
   coefficients.  For multiple count constraints, the paper says their
   intersection cannot be counted tractably here and uses the explicit
   heuristic \(\left\lceil\sum_{C\in M}|F_{\{C\}}|/|M|^2\right\rceil\).
   This is an assumption for candidate comparison, not an exact combinatorial
   identity or an archive bound.

For the error term (PDF p. 4 / proceedings p. 8185), the paper does not solve
the nearest-satisfying-assignment problem.  It counts unsatisfied CNF clauses
and estimates the number of variables to flip using a coupon-collector model,
\(\lceil |V|-|V|(1-1/|V|)^m\rceil\), where \(m\) is the number of unsatisfied
clauses.  This estimate is fast and bounded by \(|V|\), but it is not the
defined minimum Hamming error in general.

Consequently, the selection score may order candidates differently from a
complete exact codec.  It is not a valid prune bound on final serialized bytes.

## URPILS search algorithm

Algorithm 1, **URPILS**, is a staged greedy search (PDF p. 4 / proceedings p.
8185): start with \(M=\varnothing\); then call `FILTER` on simple candidates,
complex candidates, and count candidates in that order.  Count candidates are
delayed because their data score is harder to compute.

Algorithm 2, **FILTER** (same page), sorts candidates by their individual
score.  For a candidate it attempts to merge it with an existing constraint
having the same variable and target parts, by disjoining the filters; it accepts
the resulting model only if the approximate total score falls.

The supplementary algorithm detail in the supplied PDF is material to the
search claim:

* `SIMPLECANDS` creates pairwise assignment implications with restricted
  equality, Boolean-relation, and numeric-relation filters (PDF appendix,
  pp. 10–11 of the supplied file).
* `COMPLEXCANDS` enumerates basic filter expressions to a bounded grammar
  depth (three in the reported experiments), then selects a conjunction by a
  separate MDL classification score.  It excludes conjunction/disjunction
  while making the basic elements to limit expansion (PDF appendix, pp. 11–12).
* Count candidates use observed bounds and an empty or one-Boolean-relation
  filter (main text, PDF p. 5 / proceedings p. 8186).

The paper itself says the score is neither monotone nor submodular and supplies
counterexamples in its appendix (PDF appendix p. 10).  Therefore this greedy
procedure has no stated global-optimality guarantee.  It is a heuristic
constraint-discovery algorithm, not an exhaustive representation search.

## Relevance and non-transfer to a CIX archive

| Paper component | Legitimate transfer lesson | What does not transfer without new work |
| --- | --- | --- |
| Constraint model plus member/error description | Account for decoder instructions and residual/error information, then choose by the full description. | The paper's real-valued score is not a serialized CIX size. |
| \(|F_M|\) term | If a byte constraint has a known finite admissible set, \(\log_2|F_M|\) is an ideal index cost. | A rank/unrank, exact count, state/path constraints, and finite coder must be implemented and framed. |
| Grammar model cost | A finite, decoder-known grammar can make representation selection auditable. | The URPILS grammar depends on external relational domain objects and has no byte-transform semantics. |
| Noise correction | Exact residuals can make an approximate constraint reversible. | The paper's nearest-error value is estimated; an archive needs exact residual positions/values and tie-independent reconstruction. |
| Greedy search | Shallow staged search can be honestly labelled heuristic. | Estimated scores cannot prove a final-size lower bound or safely discard a candidate. |
| Component factorisation | Independent constraint components can make exact counting tractable. | Independence must be proved for the actual decoder state and physical representation. |

## Answer to the codec question

URPILS supplies **neither** a physical codec nor rank/unrank machinery.  It
supplies an MDL-motivated *objective and heuristic model-discovery procedure*.
For exact constraint-space compression, a future design would need to add and
measure all of the following before claiming a codec relationship:

1. a fixed decoder-complete constraint language and canonical parameter code;
2. exact admissible-set or path counts for each accepted constraint, including
   start/end state and all conditional dependencies;
3. a canonical rank/unrank or a precisely specified arithmetic distribution,
   integer precision, termination, and error/residual code;
4. complete archive framing, lengths, checksums, padding, and selection tags;
   and
5. archive-only independent reconstruction.

Those additions may be worthwhile research, but they are not demonstrated by
the cited paper.  The paper is prior art against presenting “MDL-guided
constraint discovery” or “model-count-based selection” as new; it does not
settle novelty, correctness, or compression performance of a byte-level CIX
implementation.
