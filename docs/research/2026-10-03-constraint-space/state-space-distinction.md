# State-space surplus versus model-description advantage

**Status:** mathematical distinction and audit protocol only. It records
facts already present in the frozen ERC1/RDIC evidence and defines a bounded
normalization test. This mathematical note itself ran no jobs; the subsequent
[physical test](normalised-evidence/REPORT.md) has now completed. No novelty or
new compression principle is claimed.

## 1. Three different comparisons

Fix a record width \(b\), a binary record universe of size

\[
U=2^b,
\]

and \(r\) ordered records. Let equality model \(E\), count model \(C\), and
their intersection admit \(M_E,M_C,M_{EC}\) records respectively. Always

\[
M_{EC}\le\min(M_E,M_C).
\]

Three questions must remain separate.

### Marginal joint reduction

The ideal joint reduction over the better component is

\[
J=\min(\log_2M_E,\log_2M_C)-\log_2M_{EC}.
\]

It is nonnegative by set inclusion. A strict value says the intersection is
smaller than each component. This is useful, but it is close to a tautology:
it does not show that the shrinkage exceeds what ordinary overlap predicts.

### State-space surplus interaction

The model-cost-independent cardinality interaction relative to the uniform
universe is

\[
\sigma=
\log_2\frac{M_EM_C}{U M_{EC}}.
\]

It is positive exactly when

\[
M_{EC}<\frac{M_EM_C}{U},
\]

the intersection size expected if membership in the two sets were independent
under a uniform record. This is the nontrivial state-space surplus statistic.
For \(r\) product records its ideal total is \(r\sigma\) bits.

### Description advantage for the same joint space

A direct dictionary and a constraint expression can denote the identical
joint set \(S=E\cap C\). Their uniform sequence rank is then the same size.
Any complete-size difference is model description, framing or finite-coder
overhead. It is not an additional state-space reduction.

Positive \(J\), positive \(\sigma\), and a shorter structural description are
three independently reportable facts. None should be used as a synonym for
the others.

## 2. Exact dense-rank lengths

For a uniform vocabulary of \(M\) records, ERC1 stores one dense integer for
the ordered \(r\)-record sequence. Its byte payload is

\[
P(M,r)=
\left\lceil
\frac{\operatorname{bit\_length}(M^r-1)}8
\right\rceil.
\]

This includes the exact power-of-two boundary and gives zero bytes for the
single-state case. It is the byte-rounded form of
\(\lceil r\log_2M\rceil\) bits.

At one fixed width, the current ERC1 E, C and EC modes all have the same
physical 24-byte area:

```text
20-byte header + rank payload + 4-byte CRC-32
```

Every header slot is present in every mode. Therefore their actual complete
sizes are

\[
L_E=24+P(M_E,r),
\]

\[
L_C=24+P(M_C,r),
\]

\[
L_{EC}=24+P(M_{EC},r).
\]

Within this matched-width comparison, model cost is already normalized. EC
beats E exactly when

\[
P(M_E,r)>P(M_{EC},r),
\]

and similarly for C. It beats both exactly when both strict inequalities
hold. Rank-byte rounding can turn a real-valued marginal reduction into a
physical tie.

The ideal per-record margins are

\[
\log_2(M_E/M_{EC})
\quad\text{and}\quad
\log_2(M_C/M_{EC}).
\]

With the common 24-byte fee there is no metadata-amortization threshold. The
only exact repetition threshold is the first \(r\) at which the corresponding
payload-byte widths differ. It must be determined from the integer formula
above; a log estimate is insufficient at a byte boundary.

More generally, if route \(X\) and EC have complete model areas \(F_X\) and
\(F_{EC}\) bytes, EC beats \(X\) if and only if

\[
P(M_X,r)-P(M_{EC},r)>F_{EC}-F_X.
\]

Ignoring only rank and byte rounding, the corresponding repetition threshold
is

\[
r\log_2(M_X/M_{EC})
>8(F_{EC}-F_X).
\]

The exact byte inequality is the decision rule. The ideal expression only
shows how repeated records amortize an extra joint-model area.

If E, C and EC select different record widths from a portfolio, their archive
comparison remains a valid portfolio result, but it is not this fixed-model
state-space identity. Width, universe, record count and alphabet must match.

## 3. Physical surplus with a common model fee

Suppose a valid uniform-binary-record mode over all \(U\) states uses the same
model area \(F\). Define

\[
P_U=P(U,r),
\quad P_E=P(M_E,r),
\quad P_C=P(M_C,r),
\quad P_{EC}=P(M_{EC},r).
\]

The exact byte-rounded surplus is

\[
\Sigma_F=P_E+P_C-P_{EC}-P_U.
\]

Because all four complete archives cost \(F+P_X\), this is also

\[
(F+P_E)+(F+P_C)-(F+P_{EC})-(F+P_U).
\]

The fee cancels exactly. Before rank and byte rounding,

\[
8\Sigma_F\approx r\sigma.
\]

This is the physical counterpart of the uniform state-space statistic. It is
not merely \(P_{EC}<\min(P_E,P_C)\).

The present ERC1 Raw mode is not this \(U^r\) control: Raw stores the original
source bytes, whereas \(U=2^b\) assumes the two stored symbols and packs one
binary choice at each of the \(b\) record positions. The bounded native RNC
harness now has a uniform-record route for this purpose. Until its physical
archive is produced and independently verified, the value remains a derived
normalized statistic. Subtracting the Raw payload would compare different
source models.

## 4. Exact even-width family

Let \(b\ge4\) be even. Define a fixed model family on binary length-\(b\)
records:

* \(E\): the first two positions are equal; and
* \(C\): the record has exactly \(b/2\) one bits.

The uniform universe has

\[
U=2^b.
\]

Constraint E removes one independent binary choice, so

\[
M_E=2^{b-1}.
\]

The fixed histogram has

\[
M_C=\binom b{b/2}.
\]

For the intersection, the equal pair is either `00` or `11`. The first case
chooses all \(b/2\) ones from the remaining \(b-2\) positions; the second
chooses \(b/2-2\). Binomial symmetry makes the two counts equal:

\[
\begin{aligned}
M_{EC}
&=\binom{b-2}{b/2}+\binom{b-2}{b/2-2}\\
&=2\binom{b-2}{b/2}.
\end{aligned}
\]

Substitution gives the exact surplus

\[
\begin{aligned}
\frac{M_EM_C}{U M_{EC}}
&=\frac{2^{b-1}\binom b{b/2}}
        {2^b\,2\binom{b-2}{b/2}}\\
&=\frac{b-1}{b-2},
\end{aligned}
\]

and therefore

\[
\sigma_b=\log_2\frac{b-1}{b-2}>0.
\]

Equivalently, under a uniform record \(P(E)=1/2\), while sampling positions
without replacement under the half-one histogram gives

\[
P(E\mid C)=\frac{b-2}{2(b-1)}.
\]

The surplus is \(\log_2(P(E)/P(E\mid C))\). This is the standard
hypergeometric dependence created by a fixed histogram, not a new
combinatorial result.

For \(r\) independently ranked records, all four cardinalities are raised to
the \(r\)-th power, so the ideal surplus is exactly

\[
r\sigma_b=
r\log_2\frac{b-1}{b-2}.
\]

The corresponding byte-rounded physical statistic is

\[
\begin{aligned}
\Sigma_{b,r}={}&
P(2^{b-1},r)
+P\!\left(\binom b{b/2},r\right)\\
&-P\!\left(2\binom{b-2}{b/2},r\right)
-P(2^b,r).
\end{aligned}
\]

It must be evaluated with the exact integer ranks. A positive ideal
\(\sigma_b\) can round to a physical tie for small \(r\).

The family yields the frozen cardinalities directly:

| Width \(b\) | \(M_E\) | \(M_C\) | \(M_{EC}\) | \(\sigma_b\) |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 8 | 6 | 2 | \(\log_2(3/2)\) |
| 6 | 32 | 20 | 8 | \(\log_2(5/4)\) |
| 8 | 128 | 70 | 30 | \(\log_2(7/6)\) |
| 10 | 512 | 252 | 112 | \(\log_2(9/8)\) |

The width-four row is a fixed-mask theorem, not the actual Auto-E ablation in
the frozen experiment. Its two observed joint records imply an additional
adjacent-pair equality, which the automatic E discovery admits; the E
portfolio selects a stronger width-two equality description with local
cardinality two. Therefore the fixed \(M_E=8\) row must not be substituted for
that actual selected E archive. Width, mask and candidate family have to
remain fixed for this identity.

## 5. Six-position ERC example

The frozen six-position strong fixture has

\[
U=64,
\quad M_E=32,
\quad M_C=20,
\quad M_{EC}=8,
\quad r=12288/6=2048.
\]

Its surplus interaction is

\[
\sigma=
\log_2\frac{32\cdot20}{64\cdot8}
=\log_2(1.25)
\approx0.321928\text{ bits per record}.
\]

The existing physical ERC1 archives are:

| Mode | Complete bytes | Common area | Rank payload |
| --- | ---: | ---: | ---: |
| E | 1,304 | 24 | 1,280 |
| C | 1,131 | 24 | 1,107 |
| EC | 792 | 24 | 768 |

Thus the exact marginal joint gain is

\[
\min(1304,1131)-792=339\text{ bytes}.
\]

A matched uniform-record rank would have

\[
P_U=P(64,2048)=1536\text{ bytes}.
\]

The derived byte-rounded surplus is therefore

\[
1280+1107-768-1536=83\text{ bytes},
\]

close to the ideal \(2048\log_2(1.25)/8\approx82.41\) bytes. The 339-byte
marginal gain and the 83-byte surplus answer different questions.

## 6. Same-space uniform-code limitation

**Proposition.** Let two archive routes describe the same decoder-known set
\(S\) of size \(M\), assign the uniform model to \(S^r\), and store a dense
fixed-width rank. If their complete model/framing areas are both \(F\), then
their complete lengths are equal:

\[
L_A=L_B=F+P(M,r).
\]

**Proof.** Both routes have exactly \(M^r\) possible ordered sequences. A
dense fixed-width rank for either requires the same
\(P(M,r)\) bytes. Adding the same complete model/framing area gives the stated
equality. Different deterministic orderings can change the rank value, but
not its fixed width. \(\square\)

Therefore no route can strictly beat a direct same-space uniform dense-rank
code when complete model cost and framing are equal. A strict result requires
at least one actual difference:

* a shorter complete model description;
* a smaller admitted source set;
* a nonuniform probability assignment suited to the sequence;
* different valid finite-coder termination or packing; or
* a different comparison scope.

The first item is a legitimate compression gain, but it is a representation
or metadata gain rather than a new rank or state-space gain.

## 7. ERC1 versus RDIC

For every frozen strong row, ERC1 EC and RDIC use the same ascending observed
vocabulary and the same base-\(M\) sequence rank. Let

\[
Q=
\left\lceil
\frac{\operatorname{bit\_length}(\binom UM-1)}8
\right\rceil
\]

be RDIC's separately byte-rounded dictionary rank. The actual formats give

\[
L_{EC}=24+P(M,r),
\]

\[
L_D=19+Q+P(M,r),
\]

so

\[
L_D-L_{EC}=Q-5.
\]

The rank payload cancels. The frozen rows already show the complete
metadata-only result:

| Width | Joint vocabulary | RDIC dictionary bytes \(Q\) | RDIC minus ERC EC |
| ---: | ---: | ---: | ---: |
| 4 | 2 | 1 | -4 bytes |
| 6 | 8 | 5 | 0 bytes |
| 8 | 30 | 17 | 12 bytes |
| 10 | 112 | 64 | 59 bytes |

At width six, RDIC's 19-byte base plus five dictionary bytes is already the
same 24-byte model area as ERC1. The actual archives tie at 792 bytes, exactly
as the proposition requires. At widths eight and ten, ERC1 wins because its
constraint parameters describe the same vocabulary more cheaply than a
generic subset rank. At width four, the generic subset description is four
bytes cheaper. None of those differences is a rank-payload advantage.

## 8. Actual-archive common-fee test

A bounded normalization test should preserve decodability rather than
subtracting hypothetical headers:

1. Fix one source, record width, alphabet, record count and exact joint
   vocabulary.
2. Materialize and fresh-decode E, C and EC in their existing 24-byte ERC1
   envelopes. Retain complete bytes and parsed rank widths.
3. Use the native RNC harness's uniform-\(U\) route to materialize a dense-rank
   control in the same integrity-checked model area before reporting physical
   \(\Sigma_F\). Until that archive is freshly decoded and verified, report
   \(\sigma\) as exact mathematics and \(\Sigma_F\) as derived.
4. Materialize RDIC for the identical joint vocabulary and verify that its
   sequence rank width and ordered vocabulary match EC.
5. For a same-space cost-normalized diagnostic, choose
   \(F^*=\max(24,19+Q)\), zero-pad the smaller model area inside a declared,
   validated frame, and fresh-decode both actual archives. Both must then cost
   \(F^*+P(M,r)\).
6. Report separately the unmodified production-format sizes, the common-fee
   normalized sizes, marginal joint gain, uniform surplus, and model
   description difference.

Padding to \(F^*\) is a diagnostic, not a new compression result. Its purpose
is to remove the known metadata difference while retaining every byte needed
for either decoder. If the normalized same-space archives do not tie, the
test has exposed unmatched framing, rank width, vocabulary order or another
uncontrolled dimension.

No repeated broad CIX benchmark is needed for this distinction. The test is a
bounded paired archive check around the already frozen record fixtures and
native decoders.

## 9. Claim boundary

The current evidence supports two narrow statements:

1. within ERC1's equal 24-byte model areas, EC has a smaller exact state space
   and rank payload than either E or C on the strong fixtures; and
2. against RDIC on the same joint set, every size difference is model
   description cost because the sequence rank is identical.

The positive \(\sigma\) values show surplus relative to a uniform
independence reference. They do not show a coder unavailable to arithmetic,
enumerative or dictionary methods. Dense ranking of a finite state space,
two-part model descriptions and direct dictionaries are established prior
art. Any future claim belongs to a concrete generic compact description,
bounded discovery method or measured systems tradeoff after matched controls;
it is not a new information-theoretic principle.
