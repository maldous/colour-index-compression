# Equality graphs plus binary histograms: exact proofs and controls

**Status:** mathematical derivation and proposed finite qualification only.
No implementation, job, compression result, novelty or general compression
principle is claimed. The counting method is standard weighted subset-sum
dynamic programming used as an exact enumerative model.

## 1. Model and exact intersection size

Let the source universe be the \(n\)-bit strings,

\[
\Omega=\{0,1\}^n,\qquad |\Omega|=2^n.
\]

An equality graph on the bit positions partitions the vertices into connected
components. All positions in one component must have the same bit. Order the
components canonically by their smallest vertex and let their positive sizes
be

\[
w_0,w_1,\ldots,w_{c-1},
\qquad \sum_iw_i=n.
\]

An equality-satisfying object is determined by component bits
\(z_i\in\{0,1\}\), so the equality model alone has \(2^c\) members. Add the
binary histogram constraint that the original object has exactly \(k\) one
bits. The intersection is

\[
\mathcal S(w,k)=
\left\{z\in\{0,1\}^c:\sum_iw_iz_i=k\right\}.
\]

Its exact cardinality is the coefficient

\[
N(w,k)=
[x^k]\prod_{i=0}^{c-1}(1+x^{w_i}).
\]

The equality graph, not merely the multiset of weights, is needed to expand a
component assignment back to the original positions. Any archive must carry a
canonical partition or a fully specified cheaper graph family such as a run,
lane or periodic pattern.

## 2. Exact suffix DP

Define

\[
F(i,s)=
\#\left\{(z_i,\ldots,z_{c-1}):
\sum_{j=i}^{c-1}w_jz_j=s\right\}.
\]

The exact recurrence is

\[
F(c,0)=1,
\qquad F(c,s)=0\ (s\ne0),
\]

\[
F(i,s)=F(i+1,s)+F(i+1,s-w_i),
\]

where a negative or out-of-range second argument contributes zero. Then

\[
N(w,k)=F(0,k).
\]

No floating-point value or estimated coefficient is used. Every DP value is
an arbitrary-precision nonnegative integer. Since

\[
0\le F(i,s)\le2^{c-i},
\]

an entry needs at most \(c-i+1\) bits including zero. Fixed-width wraparound
would change the model and can create rank collisions.

The same table can use

\[
K=\min(k,n-k)
\]

columns. When \(k>n/2\), rank the complemented component bits
\(y_i=1-z_i\), whose weighted target is \(n-k\). The decoder makes the same
choice from \(n,k\), so no flag is needed.

With all suffix rows stored, construction uses \(O(cK)\) big-integer
additions. A conservative bit-operation bound for schoolbook addition is
\(O(Kc^2)\), and the table occupies at most

\[
(K+1)\sum_{j=1}^{c+1}j
=\frac{(K+1)(c+1)(c+2)}2
\]

bits before allocator and indexing overhead. A rolling two-row counter uses
\(O(Kc)\) bits but does not retain enough suffix counts for one-pass unranking.
Rows can instead be recomputed or checkpointed, trading bounded memory for
additional deterministic work. Parsing and expanding the partition costs at
least \(O(n)\) time and storage proportional to its chosen representation.

## 3. Exact rank and unrank

Use lexicographic order on the canonical component-bit vector, with zero
before one. Start with remaining weight \(s=K\) and rank \(r=0\). At component
\(i\), the number of valid objects in the zero branch is

\[
q_0=F(i+1,s).
\]

For ranking:

* if \(y_i=0\), leave \(r,s\) unchanged;
* if \(y_i=1\), set \(r\leftarrow r+q_0\) and
  \(s\leftarrow s-w_i\).

The final state must have \(s=0\), and the result satisfies
\(0\le r<N(w,k)\).

For unranking, first reject \(r\ge N(w,k)\). At component \(i\):

* if \(r<q_0\), choose \(y_i=0\);
* otherwise choose \(y_i=1\), set \(r\leftarrow r-q_0\), and subtract
  \(w_i\) from \(s\).

Reject a negative remaining weight or a nonzero final \(r,s\). Complement if
required and expand each component bit to all of its graph vertices. Once the
table exists, rank or unrank uses \(O(c)\) big-integer operations, at most
\(O(c^2)\) conservative bit operations, plus \(O(n)\) reconstruction.

The physical rank width is

\[
R(N)=\lceil\log_2N\rceil,
\qquad R(1)=0.
\]

Unused fixed-width ranks are invalid. The decoder derives \(N\) exactly, so a
separate rank-width field is unnecessary when the surrounding frame already
delimits the model and block.

## 4. Complete archive controls

Every comparison needs four complete archive costs, not payload-only
cardinalities:

\[
L_0=D_0+n
\]

for a strong raw control,

\[
L_E=D_E+c
\]

for equality only,

\[
L_C=D_C+R\!\left(\binom nk\right)
\]

for the histogram/count model only, and

\[
L_{EC}=D_{EC}+R(N(w,k))
\]

for the intersection. Each \(D\) is the route ID plus every applicable
length, partition/pattern, histogram, parameter, version, framing, padding,
integrity and termination field. Do not assume
\(D_{EC}=D_E+D_C\): a real format may share fields or require a distinct tag.

The joint advantage over the better component is

\[
G_{\mathrm{best}}=\min(L_E,L_C)-L_{EC}.
\]

The strong interesting case is

\[
L_E\ge L_0,
\qquad L_C\ge L_0,
\qquad L_{EC}<L_0.
\]

That establishes that neither component route suffices in the declared
format. It still does not defeat a cheaper direct model of the same set.

A separate paid superadditivity diagnostic is

\[
G_{\mathrm{sup}}=L_E+L_C-L_{EC}-L_0.
\]

It measures whether the joint improvement exceeds the sum of the two
individual improvements relative to raw. It is not interchangeable with
\(G_{\mathrm{best}}\).

Before integer widths and descriptions, the set-volume term in
\(G_{\mathrm{sup}}\) is

\[
\sigma(w,k)=
\log_2
\frac{2^c\binom nk}{2^nN(w,k)}.
\]

It is positive exactly when an exact histogram is less probable under uniform
component bits than under uniform original bits:

\[
\frac{N(w,k)}{2^c}<\frac{\binom nk}{2^n}.
\]

Complete paid interaction also contains
\(D_E+D_C-D_{EC}-D_0\), rank rounding and byte framing.

The final strong control is

\[
L_{EC}<L_D
\]

for every known direct run, period, composition or normalized predicate model
\(D\) that denotes the same set. Without it, a smaller intersection may only
have rediscovered an existing representation in a longer syntax.

### Partition-description bounds

An arbitrary equality closure is a set partition, not an arbitrary edge list.
There are \(B_n\) partitions of \(n\) labelled positions, where \(B_n\) is the
Bell number, so a uniform arbitrary-partition rank needs

\[
\left\lceil\log_2 B_n\right\rceil
\]

bits before route framing. A simpler explicit upper bound stores a validated
component label for each position using at most
\(n\lceil\log_2c\rceil\) bits, although a canonical restricted-growth string
avoids label-permutation duplicates. An edge list needs its edge count and
roughly \(2|E|\lceil\log_2n\rceil\) endpoint bits before integer framing, and
different redundant edge sets can describe the same closure. It is therefore
not a canonical cost unless normalized.

Restricted families can be much cheaper. A contiguous run partition with
\(c\) nonempty runs has \(\binom{n-1}{c-1}\) boundary patterns. A periodic or
lane partition can store a period, phase and tail convention. Whatever family
is used, \(D_E\) and \(D_{EC}\) include its actual route tag, parameters and
boundary cases. Transmitting only \((w_i)\) does not identify which source
positions belong to each component.

## 5. Uniform component weights

If every component has size \(s\), then \(n=cs\). The intersection is empty
unless \(s\) divides \(k\). For \(k=sr\),

\[
N(w,k)=\binom cr.
\]

Across feasible histograms, the minimum positive cardinality is one at
\(r=0\) or \(r=c\), and the maximum is

\[
\binom c{\lfloor c/2\rfloor}.
\]

This is not a new joint model. Once the equality/run/period mapping is known,
the original histogram says exactly that the \(c\) component bits have
\(r=k/s\) ones. Ranking the intersection is ordinary composition coding of
that component-bit string. A direct run or periodic representation followed
by a composition coder assigns the same uniform probability
\(1/\binom cr\) and has the same ideal rank cost.

Relative to storing the component bits literally, the maximum available rank
reduction is

\[
c-R\!\left(\binom cr\right),
\]

from which the count \(r\), route choice and all pattern metadata must be
subtracted. If the direct route already carries \(r\) or derives it from
\(k,s\), storing both is double charging in one candidate or hidden metadata
in the other. Physical coder differences can still affect bytes, time and
memory, but there is no additional probability-model surplus to attribute to
intersection search.

For arbitrary positive weights, subsets with the same weighted sum form an
antichain: a proper superset has strictly larger weight. Sperner's bound gives

\[
1\le N(w,k)\le\binom c{\lfloor c/2\rfloor}
\]

whenever the intersection is nonempty. Uniform weights at a central feasible
histogram attain the upper bound; a uniquely attainable sum attains the lower
bound.

## 6. Heterogeneous weights and a paid finite witness

Heterogeneous component sizes can create positive cardinality interaction.
For the weights

\[
(2,1,1),\qquad n=4,\quad c=3,\quad k=2,
\]

there are two valid component assignments: select the weight-two component,
or select both singleton components. Thus \(N=2\), and

\[
\sigma=
\log_2\frac{2^3\binom42}{2^4\cdot2}
=\log_2(3/2)\approx0.585\text{ bits}.
\]

This pattern has a generic periodic extension. In each four-position block,
equate one adjacent pair and leave the other two positions as singleton
components. With \(t\) blocks the weights are \((2,1,1)^t\),
\(n=4t\), \(c=3t\), and the central-histogram intersection has

\[
N_t=[x^{2t}](1+x^2)^t(1+x)^{2t}.
\]

The equality phase, block period and histogram deviation can all be generic
stored parameters. The coefficient must be evaluated exactly for every
claimed size; the positive \(t=1\) interaction does not by itself prove the
sign or paid benefit for every \(t\).

There is even a small fully paid byte-archive witness for the four route
controls. Use:

* a fixed five-bit magic/version prefix `10110`;
* an Elias-gamma length, costing five bits for \(n=4\);
* fixed three-bit route IDs `000` raw, `001` equality, `010` histogram,
  `011` intersection and `100` direct, with the remainder invalid;
* a one-bit equality phase, where zero equates the first adjacent pair and one
  the last adjacent pair in every four-bit block;
* a one-bit histogram deviation, where zero means \(k=n/2\) and one means
  \(k=n/2-1\) for the declared lengths; and
* validated zero padding to the next whole byte.

The constrained routes accept positive lengths divisible by four and reject
other lengths. Those fields define the entire frozen toy archive. It has no
checksum; a physical CIX archive would add and charge its integrity and other
framing fields. They are not silently assumed to be free in a production
comparison.

For phase zero and zero deviation, the complete physical lengths are:

| Candidate | Magic/version | Length | Route bits | Parameters | Rank | Zero pad | Complete bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| raw \(L_0\) | 5 | 5 | 3 | 0 | 4 | 7 | 3 |
| equality \(L_E\) | 5 | 5 | 3 | 1 | 3 | 7 | 3 |
| histogram \(L_C\) | 5 | 5 | 3 | 1 | 3 | 7 | 3 |
| intersection \(L_{EC}\) | 5 | 5 | 3 | 2 | 1 | 0 | 2 |

Thus both individual candidates tie raw at three bytes while the intersection
uses two bytes. This satisfies the strong four-cost condition after padding,
without an input name, hash or unstored parameter. The deliberately small
alignment illustrates why the complete archive, rather than the unpadded
payload, is the decision quantity; it is not evidence of a likely large-block
gain.

It is nevertheless a negative production control. The two intersection
members are `0011` and `1100`, which a generic direct representation describes
as two constant equal-length runs with opposite values. With the same length
and three-bit route fields, that direct route needs one orientation rank bit.
It totals 14 bits before padding and two bytes after padding, versus 16 bits
and two bytes for the intersection. The direct route ties the complete archive
size while having the shorter logical description. This demonstrates why
\(L_0,L_E,L_C,L_{EC}\) are necessary but insufficient; equivalent direct run
and periodic models remain mandatory.

For larger heterogeneous periodic patterns, a direct “weighted composition
of component bits” route is mathematically the same model as the equality plus
histogram intersection. Conditional histograms over component weights may be
useful engineering, but weighted subset-sum counting and enumerative coding
are established methods. No novelty claim is supportable without a separate
prior-art and artifact comparison.

## 7. Safe branch bounds

At suffix state \((i,s)\), let the remaining number of components be
\(m=c-i\), their total weight be \(W_i\), minimum weight \(a\), maximum weight
\(b\), and greatest common divisor \(g_i\). These are safe zero tests:

\[
s<0,
\quad s>W_i,
\quad\text{or}\quad g_i\nmid s
\quad\Longrightarrow\quad F(i,s)=0.
\]

The gcd condition is necessary, not sufficient. Exact rank and unrank still
use \(F\), never an estimate.

If a solution selecting \(t\) remaining components exists, then

\[
\left\lceil\frac{s}{b}\right\rceil
\le t\le
\min\left(m,\left\lfloor\frac{s}{a}\right\rfloor\right).
\]

Therefore a certified count upper bound is

\[
F(i,s)\le
\sum_t\binom mt
\]

over that integer interval, capped by \(2^m\). Positivity of the generating
polynomial also gives, for any positive rational \(\rho\),

\[
F(i,s)\le
\rho^{-s}\prod_{j=i}^{c-1}(1+\rho^{w_j}).
\]

It is safe only after outward rounding to a proved integer upper bound;
ordinary floating-point evaluation is a search estimate.

A certified lower bound comes from explicitly found, disjoint solutions. With
weight multiplicities \(m_a\), one feasible selection-count vector \(t_a\)
contributes

\[
\prod_a\binom{m_a}{t_a}
\]

distinct assignments. Sums over distinct feasible vectors remain lower
bounds. These integer lower and upper bounds can feed the exact pruning rules
in `adversarial-math.md`; they cannot replace the exact count in a materialized
rank code.

## 8. Repeated weights and the symmetry quotient

Group components by weight. If \(m_a\) components have weight \(a\), then

\[
N(w,k)=
\sum_{(t_a):\sum_at_aa=k}
\prod_a\binom{m_a}{t_a}.
\]

This can reduce counting work when few distinct weights occur. A grouped DP
transitions over \(t_a=0,\ldots,\min(m_a,\lfloor K/a\rfloor)\) with exact
binomial multipliers. Its operation count is bounded by the target width times
the sum of those per-group choice counts, with arbitrary-precision integer
cost still charged.

The vector \((t_a)\) is a quotient by permutations of equal-weight
components. It is not the whole source description. For one vector, the fiber
has

\[
A_t=\prod_a\binom{m_a}{t_a}
\]

position-distinct component assignments. If the quotient vector is coded with
its exact induced probability \(A_t/N\), then quotient cost plus within-fiber
rank is

\[
-\log_2(A_t/N)+\log_2A_t=\log_2N.
\]

Thus symmetry can accelerate counting and change physical metadata, but it
does not remove the need to identify which positional components are one.
Likewise, quotienting a graph by automorphisms requires an orbit index unless
the reconstructed output is itself invariant. Component labels can be made
canonical; they cannot be discarded.

## 9. Six gates before production consideration

1. **Generic grammar.** Freeze a decoder-complete partition/pattern and
   histogram grammar. Store every parameter; reject filename, hash, corpus and
   unstored source-specific dispatch.
2. **Exact semantics.** Use arbitrary-precision counts, exact rank/unrank,
   deterministic component order and exhaustive small-universe inversion.
   Reject invalid ranks, impossible histograms and malformed partitions.
3. **Complete accounting.** Materialize \(L_0,L_E,L_C,L_{EC}\), padding,
   framing and integrity fields. Also materialize every known equivalent
   direct run, periodic, composition and weighted-component model.
4. **Bounded resources.** Predeclare \(n,c,K\), DP memory, integer-operation,
   search and streaming limits. Use certified fallback rather than truncated
   integers or approximate decode intervals.
5. **Selector evidence.** On a finite oracle, compare the deterministic
   shortlist against exhaustive candidates and separate missed candidates,
   scoring errors and direct-model domination.
6. **Frozen qualification.** Freeze candidate settings before independent
   inputs, verify archive-only restoration, and report losses, time, memory
   and complete bytes. Perform a primary prior-art audit before any narrow
   implementation-novelty claim.

Passing these gates would qualify one bounded representation family for CIX
experimentation. It would not establish a universal intersection advantage or
a new information-theoretic compression principle.
