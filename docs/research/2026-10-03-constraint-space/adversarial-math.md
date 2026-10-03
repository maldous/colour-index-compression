# Constraint-space coding: adversarial mathematical audit

**Status:** mathematical audit and finite counterexample only. This note does
not claim novelty, an implemented production format, or a measured compression
gain. It uses the established antecedents in `prior-theory.md` and asks what a
complete lossless code would have to prove.

**Terminology:** this note's “set-volume synergy” is a legacy descriptive
label for a signed cardinality interaction. It is neither a proposed new name
nor a novelty claim. `synergy-search-theory.md` distinguishes it from mutual
information, PID and interaction information.

## 1. The object being coded must be fixed first

Let \(\Omega\) be a finite source universe and let \(|\Omega|=M\). For a byte
block this can be all length-\(n\) byte strings, in which case \(M=256^n\).
If length is not already known, its self-delimiting description is part of the
archive. There is no finite uniform universe of arbitrary-length strings
without such a length model.

The finite construction below writes the positive integer length first with
an Elias gamma code. A production archive would additionally need its format
version, integrity fields and container framing. Those are common constants in
the comparison below and are deliberately omitted. The example is therefore
a complete logical prefix code under a frozen grammar, not a physical CIX
archive.

A usable model description \(d\) must let the decoder reconstruct all of the
following without seeing the original object:

1. a decidable set \(S_d\subseteq\Omega\) containing the object;
2. its exact integer cardinality \(N_d=|S_d|\);
3. a deterministic total order on \(S_d\); and
4. exact, mutually inverse rank and unrank procedures in that order.

A predicate alone is therefore not a code. Nor is an estimated set size. The
description must include, or canonically identify, every constraint ID,
parameter, boundary, transform order, initial state, reset rule, table,
dictionary, arithmetic convention and format version needed for those four
operations.

For the simplest physical construction, make the model descriptions a
prefix-free language of lengths \(D_d\) and append a fixed-width rank

\[
r_d(x)=|\{y\in S_d:y\prec_d x\}|,
\qquad 0\le r_d(x)<N_d,
\]

using

\[
R(N_d)=\lceil\log_2 N_d\rceil
\]

bits, with \(R(1)=0\). The decoder rejects unused rank values. Ignoring no
fields, the candidate length is

\[
L_d(x)=D_d+R(N_d)+F_d,
\]

where \(F_d\) is all remaining framing, alignment, integrity and termination
cost. A real selector must compare final serialized bytes, so bit savings that
disappear under byte padding are not wins. The rest of this note folds \(F_d\)
into \(D_d\) for compactness.

A raw model \(d_0\), with \(S_{d_0}=\Omega\), must remain available. Its
complete cost is \(L_0=D_0+R(M)\), not merely \(\log_2 M\).

## 2. Gain and synergy relative to the same uniform universe

For a constraint set \(A\subseteq\Omega\), its ideal set-volume gain over the
uniform universe is

\[
g(A)=\log_2\frac{M}{|A|}.
\]

For two constraints with nonempty intersection, the interaction, or
set-volume synergy, is

\[
\begin{aligned}
\sigma(A,B)
  &=g(A\cap B)-g(A)-g(B)\\
  &=\log_2\frac{|A|\,|B|}{M\,|A\cap B|}.
\end{aligned}
\]

It is positive exactly when the intersection is smaller than the
independence-size reference \(|A||B|/M\). It is negative when the constraints
are redundant at that reference. This is a cardinality identity, not yet a
compression result.

For \(k\) constraint sets \(S_1,\ldots,S_k\), the corresponding total excess
over their individual gains is

\[
\sigma(S_1,\ldots,S_k)
=\log_2
  \frac{\prod_{i=1}^{k}|S_i|}
       {M^{k-1}|\bigcap_i S_i|}.
\]

Pairwise positive values do not guarantee that every larger intersection is
worth coding. For selection, conditional marginal gain is safer. If
\(S_J=\bigcap_{j\in J}S_j\), adding constraint \(i\) has ideal rank gain

\[
\Delta_i(J)=\log_2\frac{|S_J|}{|S_{J\cup\{i\}}|}.
\]

Let \(D_J\) be the complete model and framing description for the current
intersection. The exact fixed-rank improvement is

\[
I_i(J)=
R(|S_J|)-R(|S_{J\cup\{i\}}|)-(D_{J\cup\{i\}}-D_J).
\]

The constraint improves that candidate exactly when \(I_i(J)>0\). A tie is
not a size win and should retain a deterministic incumbent. The real-valued
approximation

\[
\widetilde I_i(J)=
\Delta_i(J)-(D_{J\cup\{i\}}-D_J)
\]

can differ from the fixed-rank result by strictly less than one bit, before
padding and container effects. It cannot safely decide a close case.

The exact code-level interaction relative to the raw model is

\[
\Sigma_L=L_A+L_B-L_{A\cap B}-L_0.
\]

Positive \(\Sigma_L\) means that the joint candidate gains more than the sum
of the two separate candidates' gains. In ideal, unrounded form this is

\[
\sigma(A,B)
  +D_A+D_B-D_{A\cap B}-D_0.
\]

The second term prevents shared, duplicated or unusually expensive model
descriptions from being mistaken for set synergy.

## 3. Exact marginal bounds for sound pruning

Suppose the current set has exact size \(N\), the proposed intersection has
unknown exact size \(N'\), and its exact incremental description cost is
\(c=D'-D\). If a certified integer lower bound \(1\le L\le N'\) is available,
then

\[
I=R(N)-R(N')-c
 \le R(N)-R(L)-c.
\]

If the right-hand side is at most zero, the candidate can be pruned without
materializing it. The trivial \(L=1\) also shows that a description costing at
least \(R(N)\) additional bits can never win by rank reduction alone.

Equivalently,

\[
R(N)-R(N')\le
\left\lceil\log_2\frac{N}{N'}\right\rceil,
\]

so a certified ratio bound gives a slightly coarser pruning rule. A heuristic
or sampled ratio is not certified.

Conversely, if a certified integer upper bound \(N'\le U\) is available, then

\[
I\ge R(N)-R(U)-c.
\]

A strictly positive right-hand side proves a rank-level win. Neither result
replaces the final serialized-byte comparison. If adding the constraint also
changes side streams, coding precision or alignment, their proven bounds must
be included in \(c\); otherwise the pruning statement is about the wrong
candidate.

## 4. A complete finite example: each constraint loses, both win

This example is an existence proof for paid synergy. It uses a generic
self-delimiting expression grammar instead of giving the decoder a catalogue
entry for either set.

Let \(\Omega\) be the 64-bit strings, so \(M=2^{64}\). The leading Elias gamma
code for length 64 costs \(2\lfloor\log_2 64\rfloor+1=13\) bits. Number bit
positions from zero. Use these prefix expression tokens:

* `00 || position[6] || value[1]`: the selected bit equals `value`;
* `01`: every bit is zero;
* `10 || expression`: Boolean NOT; and
* `11 || expression || expression`: Boolean OR.

The arity of every token makes an expression self-delimiting. A model is `0`
for raw, or `1 || unary(k) || expression[0] ... expression[k-1]` for the
intersection of \(k\) expressions, where
`unary(k) = 1^(k-1) || 0`. Thus the model carries its mode, constraint count,
operators, bit position and bit value. Lexicographic order and the semantics
of the four generic operators are the only fixed decoder rules.

Define the fully serialized expressions

\[
A=(\text{bit }0=0)
\]

and

\[
B=\operatorname{OR}(\operatorname{NOT}(\text{bit }0=0),
                    \operatorname{ALL\_ZERO}).
\]

The expression for \(A\) costs \(2+6+1=9\) bits. The expression for \(B\)
costs \(2+(2+9)+2=15\) bits. Including mode and count, their one-constraint
model descriptions cost 11 and 17 bits. The two-constraint description costs
\(1+2+9+15=27\) bits.

The exact set sizes are

\[
|A|=2^{63},\qquad |B|=2^{63}+1,
\qquad |A\cap B|=1,
\]

because the only string with first bit zero that also satisfies \(B\) is the
all-zero string. For that string, the complete logical code accounting is:

| Candidate | Length bits | Model bits | Rank bits | Logical total bits |
| --- | ---: | ---: | ---: | ---: |
| raw | 13 | 1 | 64 | 78 |
| A | 13 | 11 | 63 | 87 |
| B | 13 | 17 | 64 | 94 |
| A and B | 13 | 27 | 0 | 40 |

Each single constraint is costly relative to raw. Their fully described
intersection saves 38 bits. No predicate ID, parameter, expression operator,
constraint count or model-selection tag is omitted. The ideal set synergy is

\[
\sigma(A,B)=
\log_2\frac{2^{63}(2^{63}+1)}{2^{64}}
=\log_2\frac{2^{63}+1}{2},
\]

slightly more than 62 bits. This is deliberately an extreme finite witness,
not evidence that such a relationship occurs often or can be discovered
cheaply.

It is also a mandatory representation-control failure. The same grammar can
describe the intersection directly as the single `ALL_ZERO` expression. That
model costs one mode bit, the one-bit unary count and the two-bit expression,
then no rank bits. Including the 13-bit length, its logical total is

\[
13+1+1+2=17\text{ bits},
\]

which is 23 bits smaller than the conjunction. The intersection demonstrates
set-volume synergy, but it does not demonstrate an algorithmic gain from
constraint intersection. Any evaluation must include direct or normalized
equivalent models or it will credit the search mechanism for a dominated
description.

Scale also reverses the paid result. For eight-bit strings, the gamma-coded
length costs seven bits and a bit position costs three bits. The identical
logical sets have \(|A|=128\), \(|B|=129\), and \(|A\cap B|=1\):

| Candidate | Length bits | Model bits | Rank bits | Logical total bits |
| --- | ---: | ---: | ---: | ---: |
| raw | 7 | 1 | 8 | 16 |
| A | 7 | 8 | 7 | 22 |
| B | 7 | 14 | 8 | 29 |
| A and B | 7 | 21 | 0 | 28 |
| direct `ALL_ZERO` | 7 | 4 | 0 | 11 |

At this scale the conjunction loses to raw by 12 bits despite the same
qualitative set interaction. Description cost and block scale decide the
actual code result.

It also respects no-free-lunch. The four displayed model descriptions are
prefix-free; adding the direct `ALL_ZERO` description preserves that property.
Their model-description Kraft sum is

\[
2^{-1}+2^{-11}+2^{-17}+2^{-27}+2^{-4}<1.
\]

Each appended rank subcode preserves that bound. The shortest listed code is
the four-bit direct model for the all-zero object and the 65-bit raw
model-plus-rank code for every other object. Including the common 13-bit
length prefix gives uniform mean length

\[
78-\frac{61}{2^{64}}>64.
\]

The generic expression parser is fixed decoder logic. If a scoring regime
charges the decoder or program, that implementation is charged there too.
The example proves logical possibility without establishing a generic CIX
opportunity.

## 5. Kraft inequality and the no-free-lunch boundary

Let the prefix-free model language satisfy

\[
\sum_d2^{-D_d}\le1.
\]

For each model, its fixed-width ranks contribute Kraft mass

\[
N_d2^{-R(N_d)}\le1.
\]

The entire two-part family therefore satisfies

\[
\sum_d2^{-D_d}N_d2^{-R(N_d)}
\le\sum_d2^{-D_d}\le1.
\]

Overlapping models and encoder-side shortest-choice selection do not break
decodability because the description identifies the chosen model. Omitting
that description does break the proof. A non-prefix container can be equally
valid, but its explicit length fields and delimiters replace, rather than
remove, this cost.

For any selected uniquely decodable code with lengths \(\ell(x)\) over the
uniform \(M\)-object universe, Kraft's inequality implies

\[
\frac1M\sum_{x\in\Omega}\ell(x)\ge\log_2M.
\]

One proof normalizes \(2^{-\ell(x)}\) to a distribution and applies
nonnegativity of relative entropy. Also, at most \(2^b\) objects can have
code length at most \(b\). Thus no lossless code shortens every uniformly
possible object. Constraint models can win for selected objects or a
nonuniform source distribution; their longer cases, unused prefix space and
model costs pay for those wins.

## 6. Exact rank coding and uniform constrained arithmetic coding

For a fixed model \(d\), uniform coding over \(S_d\) assigns

\[
p(x\mid d)=1/N_d.
\]

Its ideal information is \(\log_2N_d\), the same ideal information carried by
the rank. A rank code can be viewed as a single \(N_d\)-way uniform arithmetic
decision.

The sequential equivalence is also exact at the ideal-probability level. For
a decoded prefix \(u\), let \(n(u)\) be the exact number of valid completions
and let \(n(ua)\) be the count after candidate next symbol \(a\). Use

\[
p(a\mid u,d)=\frac{n(ua)}{n(u)}.
\]

For any valid complete object \(x=x_1\ldots x_n\), the product telescopes:

\[
\prod_{t=0}^{n-1}
\frac{n(x_1\ldots x_{t+1})}{n(x_1\ldots x_t)}
=\frac{1}{N_d}.
\]

Exact enumerative ranking and exact uniform constrained arithmetic coding
therefore describe the same ideal uniform model. They need not emit the same
bits or bytes: fixed-rank rounding, quantized intervals, initialization,
renormalization, termination and framing remain physical costs.

If an approximate shared probability model \(q\) is used instead, arithmetic
decoding can still be exactly lossless, but it is no longer the exact uniform
rank model. Its ideal per-object cost is \(-\log_2q(x)\). Under the uniform
distribution on \(S_d\), its excess expected ideal cost is

\[
D_{\mathrm{KL}}(U_{S_d}\Vert q)\ge0
\]

when \(q\) is a valid normalized distribution with positive probability on
the set. A per-object lucky result does not prove the claimed cardinality
code.

## 7. Quotients, fibers and reversible transforms

Let \(f:\Omega\to Q\) partition the universe into fibers
\(F_q=f^{-1}(q)\). Sending only \(q=f(x)\) chooses a quotient class; it does
not identify \(x\). Exact reconstruction also requires a rank within
\(F_q\).

Under the uniform universe, the induced quotient probability is

\[
p(q)=|F_q|/M.
\]

An ideal quotient code plus an ideal within-fiber rank costs

\[
-\log_2p(q)+\log_2|F_q|=\log_2M.
\]

So a smaller quotient is not itself a compression result. A saving arises
only from genuine side information, a nonuniform source model, or a cheaper
complete physical description, all charged consistently.

A vector of discovered predicates is such a map, and an intersection is one
of its fibers. Unless the predicate outcomes and definitions are already
decoder-known, their description is part of selecting that fiber. A bijective
reversible transform has singleton fibers and merely relabels all \(M\)
objects. It can help a downstream nonuniform or local model, but it cannot
reduce the possibility count of the same uniform universe by itself.

This is the main quotient-versus-fiber failure mode: counting quotient labels
and silently discarding the within-fiber rank proves a lossy code, not a new
lossless bound.

## 8. Approximate counting: safe and unsafe uses

An exact rank width and exact unranking partition require exact integers or a
different complete code. General intersections can make exact counting the
hard part.

Safe uses of approximate machinery include:

* shortlisting candidates before exact materialization;
* pruning from certified integer lower bounds as in section 3;
* proving a win from certified integer upper bounds;
* interval refinement until the branch is certified; and
* a separately framed literal/raw escape when certification exhausts its
  resource budget.

Unsafe uses include:

* rounding a Monte Carlo, neural, floating-point or belief-propagation
  estimate and using it as \(N_d\);
* allocating \(\lceil\log_2\widehat N\rceil\) bits when \(\widehat N\) can
  underestimate the true cardinality;
* letting encoder and decoder enumerate with different integer precision,
  iteration order or stopping rules; and
* claiming exact synergy from estimated intersection sizes whose error spans
  the model cost.

A certified upper allocation can be lossless only when the exact injective
rank/unrank mapping and the decoder's width are also defined; it merely spends
extra code space. Exact combinatorial counts and ranks require arbitrary-width
integers or proved bounded representations. Silent fixed-width wraparound is
a collision.

For unrestricted constraint languages, exact intersection counting can
subsume hard model-counting problems. Feasibility claims must therefore name
a tractable family and its bounded exact counter, such as a finite-state or
bounded-width dynamic program. Search heuristics do not turn an intractable
counter into a decoder contract.

## 9. Model selection and information leakage

Trying \(K\) candidates costs encoder time and memory. Rejected trials need
not be stored when the candidate language and decoder are fixed. The selected
model and all of its data-dependent parameters do need a decodable archive
description.

There are only three legitimate ways for a decoder to know the selection:

1. an explicit prefix/route/model description is stored;
2. the choice follows deterministically from already decoded public state; or
3. the union of candidate codebooks is itself uniquely decodable and its
   Kraft/framing cost is proved.

“The decoder can rerun the selector after recovering the block” is circular
when the selection is needed to recover that block. Trying all decoders and
accepting one checksum match also spends checksum/collision assurance and
needs an unambiguous failure rule; it is not a free selector bit.

There is a second, experimental leakage channel. Choosing the model grammar,
thresholds or pruning policy after observing held-out benchmark results puts
information into the fixed decoder/program rather than the particular
archive. It still invalidates a held-out generalization claim and, in regimes
that count the decompressor or model file, is a direct size cost. A generic CIX
claim therefore needs a frozen grammar and selection policy before held-out
replication.

## 10. Novelty and claim boundary

The following propositions are established consequences of enumerative
coding, constrained systems, arithmetic coding and two-part description
methods:

* a member of a finite set can be represented by a model plus its rank;
* intersecting constraints can yield a smaller set than either constraint;
* exact completion counts induce a uniform constrained arithmetic model; and
* model selection and model parameters have description cost.

Accordingly, “constraints intersect synergistically” or “encode the model and
rank” is not a defensible novelty claim on its own. A possible engineering
contribution would need to be narrower: a concrete generic constraint
language, a decoder-complete serialization, tractable exact counters and
unrankers, sound bounded pruning, and independently verified complete-archive
gains against matched existing methods.

The mathematical bottleneck is not noticing that an intersection is small.
It is describing that particular fiber cheaply, counting and ranking it
exactly within resource limits, and beating the complete alternatives without
selection leakage. Until those elements are implemented and measured, this is
a hypothesis and accounting framework rather than a CIX compression result.
