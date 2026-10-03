# Repeated-record paid intersection theorem

**Status:** exact accounting theorem and finite cardinality example only. It
does not claim novelty, an implemented CIX route, or measured compression.
Ranks, intersections, two-part descriptions and dictionary enumerations are
established coding constructions.

## 1. Setup

Let one record take values in a finite universe \(\Omega\) of size \(U\). Let
two decoder-complete constraints admit sets \(E,C\subseteq\Omega\), with

\[
|E|=N_E,
\qquad |C|=N_C,
\qquad |E\cap C|=N_{EC}>0.
\]

Consider an ordered sequence of \(r\ge1\) records, all coded under one selected
model. Under the uniform product model, route \(X\) admits \(N_X^r\) record
sequences. Define the exact fixed-rank payload

\[
B_r(N)=\left\lceil\log_2N^r\right\rceil
=\left\lceil r\log_2N\right\rceil.
\]

Also write \(R(Q)=\lceil\log_2Q\rceil\), with \(R(1)=0\).

This is a joint rank of the ordered \(r\)-tuple. Coding each record in a
separate fixed-width frame instead costs
\(r\lceil\log_2N\rceil\), which can be larger. The chosen framing convention
must be part of the format and comparison.

At a fixed \(r\), let \(D_E,D_C,D_{EC}\) be each route's exact effective
overhead beyond that rank: model/route selection, parameters, lengths,
boundaries, resets, tables, framing, integrity fields, termination and byte
padding. Equivalently, \(D_X=L_X-B_r(N_X)\) after physical serialization. The
overhead can depend on \(r\); notation suppresses that dependence. When the
format stores metadata once and its framing stays fixed as \(r\) changes,
\(D_X\) is a constant one-time charge. Then

\[
L_E(r)=D_E+B_r(N_E),
\]

\[
L_C(r)=D_C+B_r(N_C),
\]

\[
L_{EC}(r)=D_{EC}+B_r(N_{EC}).
\]

All exact archive decisions below use these integer lengths. The ideal-log
forms expose thresholds but can be wrong by a bit near a boundary and can lose
another decision at byte padding.

## 2. Necessary and sufficient gain against each component

The exact paid gain of the intersection over \(E\), per record, is

\[
g_{EC\mid E}(r)=
\frac{L_E(r)-L_{EC}(r)}r
=\frac{D_E-D_{EC}+B_r(N_E)-B_r(N_{EC})}{r}.
\]

It is positive if and only if

\[
B_r(N_E)-B_r(N_{EC})>D_{EC}-D_E.
\]

Likewise,

\[
g_{EC\mid C}(r)=
\frac{D_C-D_{EC}+B_r(N_C)-B_r(N_{EC})}{r},
\]

and the intersection beats \(C\) if and only if

\[
B_r(N_C)-B_r(N_{EC})>D_{EC}-D_C.
\]

Consequently its exact gain over the better individual route is

\[
G_{\mathrm{best}}(r)=
\min(L_E(r),L_C(r))-L_{EC}(r)
\]

and is strictly positive exactly when both inequalities hold. A tie is not a
size win.

Ignoring only rank rounding, define the marginal ideal reductions

\[
a_E=\log_2\frac{N_E}{N_{EC}},
\qquad
a_C=\log_2\frac{N_C}{N_{EC}}.
\]

Then

\[
g_{EC\mid E}^{\mathrm{ideal}}(r)
=a_E-\frac{D_{EC}-D_E}{r},
\]

and analogously for \(C\). If \(a_X>0\) and those \(D\) values are constant
one-time charges, repeated records amortize an extra joint-model description
precisely when

\[
r a_X>D_{EC}-D_X.
\]

The corresponding ideal first profitable integer repetition count is

\[
r_{\min,X}^{\mathrm{ideal}}=
\max\left(1,
\left\lfloor\frac{D_{EC}-D_X}{a_X}\right\rfloor+1
\right).
\]

To beat both components, take the maximum of their two thresholds. A physical
format must instead find the first \(r\) satisfying the exact integer
inequalities, because rank ceilings and byte padding can shift it.

If \(N_X=N_{EC}\), repetition creates no payload advantage and the
intersection wins only when \(D_{EC}<D_X\). If model metadata is repeated for
every record rather than shared once, replace \(D_X\) by \(rD_X\); there is no
one-time-cost amortization.

## 3. Cardinality interaction and paid superadditivity

Relative to the same uniform universe, the per-record cardinality interaction
is

\[
\sigma=
\log_2\frac{N_EN_C}{U N_{EC}}.
\]

It is positive when the intersection is smaller than the uniform-independence
reference \(N_EN_C/U\). For \(r\) product records, the ideal set-volume term is
\(r\sigma\).

Let the uniform-universe route have complete length

\[
L_U(r)=D_U+B_r(U).
\]

The exact paid superadditivity diagnostic is

\[
I_{\mathrm{paid}}(r)
=L_E(r)+L_C(r)-L_{EC}(r)-L_U(r).
\]

In ideal logarithmic form,

\[
I_{\mathrm{paid}}^{\mathrm{ideal}}(r)
=D_E+D_C-D_{EC}-D_U+r\sigma.
\]

This diagnostic and \(G_{\mathrm{best}}\) answer different questions.
Positive \(I_{\mathrm{paid}}\) says the joint improvement exceeds the sum of
the two improvements relative to the uniform route. Positive
\(G_{\mathrm{best}}\) says the joint route actually beats both components.
Neither condition alone says it beats an established nonuniform reference or
a direct representation of the same set.

## 4. Necessary and sufficient strong-reference window

Let an established reference have complete length

\[
L_0(r)=D_0+r h_0,
\]

where \(h_0\) is its established payload rate in bits per record and \(D_0\)
is its one-time complete framing/model cost. If the actual reference has a
nonlinear or measured integer length, substitute that exact \(L_0(r)\); the
three comparisons below remain the theorem.

Neither individual route is profitable while the joint route is profitable
if and only if

\[
L_E(r)\ge L_0(r),
\qquad
L_C(r)\ge L_0(r),
\qquad
L_{EC}(r)<L_0(r).
\]

Using ideal product rates, this is exactly the reference-rate window

\[
\log_2N_{EC}+\frac{D_{EC}-D_0}{r}
<h_0
\le
\min\left(
  \log_2N_E+\frac{D_E-D_0}{r},
  \log_2N_C+\frac{D_C-D_0}{r}
\right).
\]

The window is nonempty if and only if the paid joint rate is strictly below
both paid individual rates. An established \(h_0\) must actually fall inside
it; the reference rate cannot be chosen after observing the candidate.

This condition makes no assumption that \(h_0=\log_2U\). A strong existing
compressor can have a much lower measured/model rate. Comparing only with raw
would answer a weaker question.

## 5. Six-bit ERC cardinality example

Take the stated six-bit-record cardinalities

\[
U=64,
\qquad N_E=32,
\qquad N_C=20,
\qquad N_{EC}=8.
\]

The ideal rates are:

| Route | Members | Ideal bits/record | Exact product-rank bits |
| --- | ---: | ---: | ---: |
| uniform | 64 | 6 | \(6r\) |
| E | 32 | 5 | \(5r\) |
| C | 20 | \(\log_2 20\approx4.321928\) | \(\lceil r\log_2 20\rceil\) |
| EC | 8 | 3 | \(3r\) |

The positive cardinality interaction is

\[
\sigma=
\log_2\frac{32\cdot20}{64\cdot8}
=\log_2(1.25)
\approx0.321928\text{ bits per record}.
\]

The joint marginal reductions are two bits per record versus \(E\) and

\[
\log_2(20/8)=\log_2(2.5)\approx1.321928
\]

bits per record versus \(C\), the better ideal component. Thus the exact paid
conditions are

\[
2r>D_{EC}-D_E
\]

and

\[
\lceil r\log_2 20\rceil-3r>D_{EC}-D_C.
\]

The first is exact because both cardinalities are powers of two; the second
retains integer rank rounding.

If all one-time description differences cancel, an established reference
rate \(h_0=4\) is inside the ideal strong window:

\[
3<4\le\min(5,4.321928).
\]

Then neither individual ideal route beats the reference, while the
intersection does. This is a cardinality/accounting witness only. Actual
format fields, integer ranks, record statistics and the direct controls below
still decide a CIX result.

## 6. Direct dictionary control

An arbitrary subset of size \(N\) from a known \(U\)-symbol universe can be
described by its enumerative subset rank using

\[
R\!\left(\binom UN\right)
\]

bits. Give the chosen symbols canonical numeric order, then encode the
ordered record sequence with \(B_r(N)\) bits. Let \(D_D\) be the exact
effective route, count, framing and padding overhead beyond those two ranks.
The direct-dictionary control is

\[
L_D(r)=
D_D+R\!\left(\binom U{N_{EC}}\right)+B_r(N_{EC}).
\]

The constraint intersection and direct dictionary assign the same uniform
probability to the same set. Therefore the constraint representation beats
this control if and only if

\[
D_{EC}<D_D+R\!\left(\binom U{N_{EC}}\right),
\]

after both sides include their actual route/count/framing fields. Repetition
does not change this inequality because their record payloads are identical.

For the ERC cardinalities,

\[
\binom{64}{8}=4,426,165,368,
\]

so an arbitrary eight-symbol subset needs 33 fixed rank bits. The complete
direct control is

\[
L_D(r)=D_D+33+3r.
\]

A constraint model with less than the corresponding 33-bit subset
description can legitimately exploit structure in the set. One costing more
is dominated by the arbitrary dictionary before runtime is considered.

The stronger data-dependent control uses the actual \(d\) distinct symbols
observed in the \(r\) records:

\[
D_D+R\!\left(\binom Ud\right)+B_r(d),
\]

plus the exact count-selection fields. It can beat a dictionary for all
\(N_{EC}\) members when the sample uses only a smaller subset. It must be
included when the production selector already supports learned dictionaries;
otherwise the comparison grants the intersection route an artificial
competitor omission.

## 7. What a positive result would and would not show

For a fixed record model, a paid intersection win requires all of the
following strict comparisons at the same \(r\):

1. exact \(L_{EC}<L_E\);
2. exact \(L_{EC}<L_C\);
3. exact \(L_{EC}<L_0\) for the established reference;
4. exact \(L_{EC}<L_D\) for arbitrary and observed direct dictionaries; and
5. exact \(L_{EC}\) below every known direct representation of the same set.

Positive \(\sigma\) is neither necessary nor sufficient for those archive
comparisons. It is only the ideal interaction term under the uniform universe.
Metadata sharing can produce a paid win with nonpositive \(\sigma\), and
expensive descriptions can erase a positive one.

The theorem is an accounting and threshold result. It does not establish a
new coding principle, a generic source model, or novelty for any constraint
grammar. A CIX claim still requires a frozen generic wire description,
archive-only exact reconstruction, complete byte accounting, direct-model
controls and independent qualification.
