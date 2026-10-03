# Constraint intersections and paid search: theory boundary

**Status:** independent mathematical and search-objective audit. No new name,
novelty, implementation or compression result is claimed. Exact intersection
coding is established enumerative/two-part coding; the open CIX question is
whether a concrete, fully paid search finds useful descriptions under bounded
resources and survives direct-model controls.

This note uses **cardinality interaction** for the signed set identity. Older
notes use “set-volume synergy” descriptively. That wording is not a claim that
the identity, or intersection coding, is new.

## 1. Utility on a family of constraints

Let \(\Omega\) be a finite uniform universe with \(|\Omega|=M\). Let
\(C_i\subseteq\Omega\) be decoder-defined constraints indexed by a finite
ground set \(E\). For \(J\subseteq E\), define

\[
S_J=\bigcap_{i\in J}C_i,\qquad S_\varnothing=\Omega,
\]

and, for nonempty \(S_J\), the ideal cardinality utility

\[
g(J)=\log_2\frac{M}{|S_J|}.
\]

This is the ideal rank reduction after the model is known. It is monotone:
adding a constraint cannot increase \(|S_J|\). Empty intersections have no
codeword for an observed object and are excluded from exact-object selection;
treating their utility as infinity would obscure that eligibility condition.

The marginal utility of constraint \(i\notin J\) is

\[
\Delta_i(J)=g(J\cup\{i\})-g(J)
=\log_2\frac{|S_J|}{|S_{J\cup\{i\}}|}.
\]

The paid, fixed-rank utility is different. If \(D_J\) is the complete model,
selection and framing description and
\(R(N)=\lceil\log_2N\rceil\), then

\[
U(J)=
[D_\varnothing+R(M)]-[D_J+R(|S_J|)].
\]

Unlike \(g\), \(U\) need not be monotone: a real constraint can narrow the set
and still make the archive longer. Byte padding and other physical fields can
make the final archive utility differ from this bit-level expression too.

## 2. Additive, submodular, supermodular, or neither

The cardinality utility is **modular** when

\[
g(J)=\sum_{i\in J}w_i
\]

for fixed weights. This requires the retained fractions to multiply along
every relevant conditioning path. It is not true merely because predicates
look syntactically unrelated.

It is **submodular** when it has diminishing returns:

\[
A\subseteq B,\ i\notin B
\quad\Longrightarrow\quad
\Delta_i(A)\ge\Delta_i(B).
\]

It is **supermodular** when the inequality is reversed. Constraint
intersection supplies no general guarantee of either property.

### Modular example

Let \(\Omega=\{0,1\}^3\) and let \(C_i\) fix bit \(i\) to zero. Then

\[
|S_J|=8/2^{|J|},\qquad g(J)=|J|.
\]

Every new bit constraint saves exactly one ideal bit regardless of the
previous constraints.

### Strict increasing returns

Let \(\Omega=\{0,\ldots,7\}\),

\[
C_1=\{0,1,2,3\},\qquad C_2=\{0,4,5,6\}.
\]

Both singleton utilities are one bit, while the singleton intersection gives

\[
g(\{1,2\})=\log_2(8/1)=3.
\]

Thus \(\Delta_2(\varnothing)=1\) but
\(\Delta_2(\{1\})=2\). On this two-constraint ground set, \(g\) is strictly
supermodular and violates submodularity.

### Strict diminishing returns

On the same universe, use

\[
C_1=\{0,1,2,3\},\qquad C_3=\{0,1,2,4\}.
\]

Again each singleton utility is one bit, but

\[
g(\{1,3\})=\log_2(8/3)\approx1.415.
\]

The second constraint adds only \(\log_2(4/3)\approx0.415\) bits after the
first. On this two-constraint ground set, \(g\) is strictly submodular and
violates supermodularity.

### One family that is neither

Use all three sets above:

\[
C_1=\{0,1,2,3\},\quad
C_2=\{0,4,5,6\},\quad
C_3=\{0,1,2,4\}.
\]

The pair \((C_1,C_2)\) violates diminishing returns, while
\((C_1,C_3)\) violates increasing returns. Therefore the same set function is
neither submodular nor supermodular. A greedy approximation guarantee cannot
be imported from either theory without additional structural assumptions.

Adding a modular description charge preserves a proven submodular or
supermodular classification, but real model costs are often nonmodular because
parameters, dictionaries and framing can be shared. Rank-width rounding also
changes marginals. The paid utility \(U\) must be analyzed directly.

### A safe rejection theorem for affine constraints

There is a strong tractable special case. Let

\[
\Omega=\mathbb F_q^n
\]

and let every atomic constraint be one affine equation

\[
a_i x=b_i.
\]

For a consistent row set \(J\), let \(r(J)\) be the matrix rank of its
coefficient rows. Elementary linear algebra gives

\[
|S_J|=q^{n-r(J)},
\qquad
g(J)=r(J)\log_2q.
\]

The rank function has diminishing returns. If \(A\subseteq B\), the span of
the rows in \(A\) is contained in the span for \(B\), so a new row can raise
rank after \(B\) only if it also raises rank after \(A\). Equivalently,

\[
r(A)+r(B)\ge r(A\cup B)+r(A\cap B).
\]

Thus \(g\) is the standard representable-matroid rank function scaled by
\(\log_2q\), hence is submodular. For two disjoint row groups,

\[
r(A\cup B)\le r(A)+r(B),
\]

so their cardinality interaction is never positive. Independent equations are
exactly additive; dependent equations are redundant.

Suppose each row has an independent fixed description cost \(c_i\), and all
other framing is identical to raw and therefore cancels. Then

\[
U(J)=r(J)\log_2q-\sum_{i\in J}c_i
\]

is also submodular. Moreover,

\[
U(J)\le
\sum_{i\in J}\left[r(\{i\})\log_2q-c_i\right].
\]

If every singleton term on the right is nonpositive, no combination can win.
This is a sound family-wide pruning rule; exhaustive combination search is
unnecessary under exactly these conditions.

A constant field common to raw and every candidate cancels as stated. A
one-time header paid only by nonempty constrained candidates is different: it
can be amortized across rows, and “no singleton wins” no longer proves that no
combination wins. Shared parameter encodings, nonmodular metadata, non-power-
of-two quantization and byte padding can likewise break the paid-utility
property even though the ideal rank function remains submodular.

Equality graphs are the same theorem in familiar form. Constraints
\(x_u=x_v\) are incidence-matrix rows. For a graph on \(n\) variables with
\(\kappa(J)\) connected components,

\[
r(J)=n-\kappa(J),
\qquad |S_J|=q^{\kappa(J)}.
\]

This is the graphic-matroid rank function. Consistent offset equalities have
the same coefficient rank. An inconsistent affine system is empty and cannot
encode an observed object satisfying all selected constraints.

The full affine universe is essential. As a small nonlinear contrast, let

\[
\Omega=\{x\in\{0,1\}^4:\textstyle\sum_i x_i=2\},
\]

the six strings with binary histogram weight two. Let \(C_1\) fix the first
bit to one and \(C_2\) fix the second bit to one. Each set has three members,
while their intersection contains only `1100`. Their cardinality interaction
is

\[
\log_2\frac{3\cdot3}{6\cdot1}
=\log_2(3/2)\approx0.585\text{ bits}.
\]

The predicates are linear, but conditioning the universe on a fixed histogram
destroys the full affine-space counting law and permits positive interaction.
The affine rejection theorem must not be generalized to composition classes,
nonlinear predicates or mixtures without a new proof. The theorem itself is a
standard linear/graphic matroid consequence, not new CIX theory.

## 3. Relation to pointwise mutual information

Draw \(X\) uniformly from \(\Omega\), and define event
\(E_i=\{X\in C_i\}\). For two constraints, the earlier signed identity is

\[
\begin{aligned}
g(\{1,2\})-g(\{1\})-g(\{2\})
&=\log_2\frac{|C_1||C_2|}{M|C_1\cap C_2|}\\
&=-\log_2
  \frac{P(E_1\cap E_2)}{P(E_1)P(E_2)}.
\end{aligned}
\]

It is therefore the negative pointwise mutual information of the particular
co-occurring outcomes \(E_1=true,E_2=true\). Positive cardinality interaction
means those outcomes are negatively associated: conditioning on one makes the
other rarer and its rank reduction larger.

This observation does **not** make the quantity mutual information. Mutual
information averages pointwise terms over every joint outcome and is
nonnegative. The all-true event term alone can have either sign.

It is also not partial information decomposition (PID). PID requires a target
variable, multiple predictors and a chosen redundancy functional in order to
separate unique, redundant and synergistic information. Bare constraint sets
provide no such target or decomposition.

For three or more events, the simple excess

\[
\log_2\frac{\prod_iP(E_i)}{P(\bigcap_iE_i)}
\]

uses only singleton probabilities and the all-true joint probability.
Interaction information/co-information uses an alternating combination of
joint entropies, or pointwise formulas containing lower-order joint terms;
sign conventions also differ. The simple excess is therefore not interaction
information except under additional special identities. Calling all of these
“synergy” without qualification conflates different objects.

## 4. Same probability model, same ideal coding cost

Let a complete decoder-known model assign distribution \(p\) to source
objects. Every ideal entropy coder using that same distribution assigns object
\(x\) information

\[
\ell_p(x)=-\log_2p(x).
\]

Consequently two coders inducing the same \(p(x)\) on original objects have
identical ideal per-object cost. Their physical outputs can differ through
integer probability quantization, rank-width rounding, table descriptions,
termination, padding and framing, and their time and memory can differ.

For a uniform constrained set \(S\) of size \(N\),

\[
p(x)=1/N\quad(x\in S).
\]

An exact rank and an exact arithmetic/range code using completion counts both
have ideal cost \(\log_2N\). If \(n(u)\) counts valid completions after prefix
\(u\), then the sequential probabilities telescope:

\[
\prod_t\frac{n(x_{1:t+1})}{n(x_{1:t})}=\frac1N.
\]

This proves equivalence of the ideal probability model, not byte identity.
Likewise, a bijective representation \(T\) followed by probability model
\(q\) induces \(p(x)=q(T(x))\). If a competing route induces that same \(p\),
the transform has not created an information gain; only its physical coding
or implementation tradeoff can differ.

Therefore a constraint-intersection experiment needs both controls:

1. the same exact set coded by each applicable backend; and
2. the cheapest direct or normalized model in the grammar that denotes the
   same set.

Without the second control, a verbose conjunction can be mistaken for a new
modeling gain even when a short atomic predicate describes the identical
fiber.

## 5. Exact-object optimization and collection acquisition are different

For one already-known object \(x\), exact-object compression solves

\[
L^*(x)=
\min_{m:x\in S_m}
\left[D(m)+L_m(x)\right].
\]

This is an individual two-part-code decision. If the stored archive is valid
and smaller, the size result is real even when the selected model is rare.
Encoder search time, peak memory and rejected trials remain separate measured
resources; the selected model and its parameters remain stored information.

Choosing which model machinery to acquire, implement or probe for a
collection is a different optimization. With a shared available library
\(A\), a representative objective is

\[
\min_A
\left[
H(A)+\sum_{x\in\mathcal X}
  \min_{m\in A:x\in S_m}(D(m\mid A)+L_m(x))
\right],
\]

where \(H(A)\) is any shared dictionary, model, program or acquisition cost
that the decoding setting requires. If archives are independently decodable,
no shared bytes may be amortized unless that shared artifact is fixed decoder
state or is supplied and charged for each archive. If it is a single
collection archive, a paid shared header can change the optimum.

Probe CPU and memory can instead be constrained as resource budgets rather
than added to byte length in incompatible units. FAST, DEFAULT and BEST are
then different feasible search sets or budgets over the same complete archive
objective.

The consequences are:

* the best model for one object need not be the best acquired library for a
  population;
* a shared model can lose on each small item separately yet win after its
  description is legitimately amortized;
* an exact-object win does not estimate expected gain on future inputs; and
* selecting a grammar or probe policy on the evaluation collection is
  training leakage, even though each produced archive remains decodable.

A generic claim therefore freezes the grammar and search policy before
held-out replication and reports both per-object complete archives and any
collection-level shared costs.

## 6. Novelty audit A–F

These six layers keep possible implementation contributions separate from old
mathematics. None is established as novel by this note.

**A. Cardinality identity.** Intersections, ranks, negative event PMI and
model-plus-index descriptions are established mathematics. They are controls,
not novelty.

**B. Decoder-complete predicate grammar.** Boolean, finite-state and other
constraint languages are established. A particularly compact generic wire
grammar may be a useful engineering artifact, but needs direct prior-art and
artifact comparison.

**C. Exact bounded counters and unrankers.** General model counting is hard;
a concrete tractable compositional subset with proved bounds can be a real
implementation contribution. It is not implied by the intersection identity.

**D. Paid deterministic search.** A selector that deduplicates equivalent
sets, includes direct-model controls, charges every selected description and
finds the exact bounded-grammar argmin is testable. Any claim belongs to the
specific search and cost construction, not to “synergy.”

**E. Certified pruning and resource policy.** Safe cardinality bounds,
deterministic ties, bounded memory and measured shortlist misses against a
small exhaustive oracle can be an algorithmic or systems contribution after
comparison. Heuristic estimates alone do not establish it.

**F. Generic integration and evidence.** A versioned streaming format,
archive-only decode, raw fallback and predeclared transfer gains can establish
practical value. They are empirical and engineering evidence, not proof of a
new information-theoretic principle.

## 7. Proposed finite exhaustive screen

A useful first artifact is deliberately too small to support a compression
claim. Use the universe of all 256 eight-bit strings and a frozen generic
Boolean predicate grammar. It can reuse the self-delimiting tokens from
`adversarial-math.md`:

* bit equality with a three-bit position and one-bit value;
* `ALL_ZERO` and any other declared generic atomic controls;
* NOT and binary OR, plus an explicit AND or the outer intersection list; and
* a raw route, unary constraint count, gamma-coded source length and exact
  lexicographic rank.

Predeclare maximum expression depth and description bits. Enumerate all valid
expressions in serialized bit order. Evaluate each expression on all 256
objects into a 256-bit truth table, retain the shortest serialization for each
distinct truth table, and break equal-length ties lexicographically. This
truth-table canonicalization supplies the mandatory direct-model control.

Then enumerate every canonical single model and every canonical unordered
pair intersection. For each target byte:

1. reject sets not containing the target;
2. popcount the exact truth table;
3. compute and independently invert its lexicographic rank;
4. charge gamma length, model prefix, parameters, rank width and padding;
5. compare the pair with raw, its components, and the shortest direct model
   having the identical truth table; and
6. select minimum complete logical length with a fixed lexical tie rule.

The exhaustive screen should assert these oracle properties:

* every accepted rank round-trips for every member of every candidate set;
* no selected conjunction is longer than a known equivalent direct model;
* the selector equals exhaustive minimum cost, including its prefix; and
* raw wins whenever no candidate is strictly smaller.

The eight-bit worked case in `adversarial-math.md` already predicts a useful
negative control: its two individually broad constraints have a singleton
intersection, yet the paid conjunction is 28 bits, raw is 16 bits, and direct
`ALL_ZERO` is 11 bits under that logical grammar. The set interaction is large
while the conjunction is decisively dominated.

This finite oracle can later measure shortlist misses for a larger bounded
selector. It cannot establish novelty, corpus gain or production feasibility;
it establishes only semantic correctness, complete local accounting and the
cost of the search space declared in advance.

## 8. Decision boundary

The identity “a conjunction can describe a smaller fiber than either
predicate” is settled and insufficient. The falsifiable research question is:

> Within a fixed generic decoder-complete grammar and declared resource
> budget, does paid deterministic search find a representation that beats raw,
> every component, every equivalent direct model and matched probability
> coders on independently verified inputs?

Only that narrower result can support a CIX implementation claim. A positive
answer would belong to the concrete grammar, counter, search and integration;
a negative answer remains useful evidence about description cost and search
coverage.
