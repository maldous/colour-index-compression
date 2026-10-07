# Addendum: paid record escapes and usage-histogram bounds

**Status:** derivation and evidence interpretation only. No code, test, or new
result is introduced. The formulae below distinguish a complete archive from
its model description and from the cardinality of the state space it indexes.

## Definitions and a concrete escape wire grammar

Let a stream contain `r` fixed-size records, each of `β` raw bits. A stored
model admits exactly `M >= 1` record values. Let `e` records be escapes, and
let `s = r - e` be the records represented by the model. Define

\[
 w(N)=\lceil\log_2 N\rceil\quad(N\geq1),\qquad w(1)=0.
\]

A complete escape archive must contain, at minimum:

```
mode | record-bit-width β | record-count r | model-length | model bytes |
escape-count e | escape-subset-rank | in-model-sequence-rank |
escape-record bytes in increasing escape-position order | checksum
```

`mode`, all self-delimiting integer fields, model length, model bytes, and the
checksum are paid framing/model bytes; call their total `F + L_M` bytes. `F`
contains the outer framing and scalar fields, including `e`; `L_M` is the
model's exact serialized description. They cannot be inferred from the
encoder's search state.

The escape positions form a subset of size `e` in `r` positions, so their
canonical combinadic rank has width `w(C(r,e))`. The `s` in-model records have
one rank in `[0, M^s)`, hence width `w(M^s)`. Escaped records are raw and take
exactly `βe` bits. With these three fields concatenated into **one** bitstream
and padded only once at its end, the complete byte cost is

\[
 C_{esc}=F+L_M+
 \left\lceil\frac{w\!\left({r\choose e}\right)+w(M^{r-e})+\beta e}{8}\right\rceil.
\]

This is the requested paid independent-record escape bound. It is exact for
that grammar, fixed canonical subset order, fixed model-value order, and one
terminal bit padding rule. If the wire instead byte-aligns each field, its
exact cost is larger or equal:

\[
 F+L_M+
 \left\lceil\frac{w({r\choose e})}{8}\right\rceil+
 \left\lceil\frac{w(M^{r-e})}{8}\right\rceil+
 \left\lceil\frac{\beta e}{8}\right\rceil.
\]

Those are different archive formats and must not be interchanged in a reported
comparison.

### Boundary cases

| Case | Required widths and result |
| --- | --- |
| `r = 0` | Necessarily `e = 0`; both ranks and raw escapes have width zero. The archive is still `F + L_M` unless its separately declared empty mode omits the model. |
| `e = 0` | `w(C(r,0)) = 0` and raw width is zero. The escape wire becomes the uniform rank over `M^r`, plus its paid framing and model. |
| `e = r` | Both combinadic subset width and `w(M^0)` are zero. The archive still pays `F + L_M + ceil(βr/8)` in this grammar. A raw mode may omit `L_M`; it is a different, normally cheaper candidate. |
| `M = 1` | The in-model rank is zero bits, but the model and escape locations remain paid. |
| `M = 0` | Invalid when `s > 0`. Do not use an ambiguous `0^0` convention to make an all-escape model appear free. |

The decoder obtains the escape positions by combinadic unrank, fills all other
positions from the base-`M` rank in canonical record-value order, then copies
raw escape records in ascending escape position. No decoder search is needed.

## Break-even comparisons that preserve the state space

A raw original-record archive using the same outer framing has

\[
 C_{raw}=F_{raw}+\left\lceil\frac{\beta r}{8}\right\rceil.
\]

The escape method beats it only when `C_esc < C_raw`. This inequality includes
the model and position-set description; comparing only `w(M^{r-e}) + βe` to
`βr` is incomplete.

A uniform code for the **same no-escape model state space** has

\[
 C_{uniform(M)}=F_U+L_M+\left\lceil\frac{w(M^r)}8\right\rceil.
\]

It represents the input only when `e=0`. For `e>0`, comparing `C_esc` with
`C_uniform(M)` is not a valid break-even test because the latter excludes the
actual escaped records. A valid uniform comparison must use a stated superset
of size `K` that contains every record actually used:

\[
 C_{uniform(K)}=F_K+L_K+\left\lceil\frac{w(K^r)}8\right\rceil.
\]

The raw universe is the special case `K=2^β`; its ideal rank has `βr` bits.

A learned dictionary control with `K` entries must additionally pay the
canonical dictionary description. If it selects `K` values from a raw universe
of `U=2^β` values by a combinadic dictionary rank, a representative complete
cost is

\[
 C_{dict}=F_D+L_D+
 \left\lceil\frac{w({U\choose K})+w(K^r)}8\right\rceil,
\]

when those two ranks share one padded bitstream. `L_D` includes the dictionary
mode and any non-combinadic parameters. A dictionary with a different
serialization needs its own exact expression. The only meaningful statement is
then `C_esc < C_dict` for the same source records and complete containers; it
is not a theorem about an uncharged model.

## Paid usage histograms

For the `s` in-model record positions, let usage counts be
\(h_1,\ldots,h_M\), with \(\sum_i h_i=s\). Conditional on this histogram,
the exact number of orderings is

\[
 T(h)=\frac{s!}{\prod_{i=1}^{M}h_i!}.
\]

A histogram-conditioned escape archive has, at minimum,

\[
 C_{hist}=F+L_M+H(h)+
 \left\lceil\frac{w({r\choose e})+w(T(h))+\beta e}{8}\right\rceil,
\]

where `H(h)` is the physically encoded histogram length, including any active
alphabet, order, and zero-count convention. This must be compared with the
uniform escape body `w(M^s)`, not with an unframed probability estimate.

If every nonnegative `M`-vector summing to `s` is allowed and the histogram is
sent in a fixed model order, there are

\[
 {s+M-1\choose M-1}
\]

possible histograms. A fixed-width canonical histogram selector therefore costs
at least `w(C(s+M-1,M-1))` bits before its conditional rank, unless a different
prefix code is fully specified. The multinomial identity gives

\[
 \sum_{h_1+\cdots+h_M=s}\frac{s!}{\prod_i h_i!}=M^s.
\]

Thus a model which permits every histogram but does **not** transmit/select one
has the full uniform state space `M^s`; it cannot lawfully use only
`w(T(h_observed))` bits. A correctly indexable superset costs the rank width of
its full cardinality. Transmitting a histogram selector plus its conditional
rank can be a valid two-part code, but its complete bytes decide whether it
beats uniform coding.

For an allowed subset `H_allowed` of histograms, the indexable state-space size
is

\[
 |S|=\sum_{h\in H_{allowed}}T(h).
\]

One rank over that superset takes `w(|S|)` bits. Alternatively, a paid selector
for `h` plus a rank in `[0,T(h))` is valid only if the selector code is
prefix-free/self-delimiting and the decoder can reproduce the same `H_allowed`
and ordering. Taking the best observed histogram without storing that choice is
encoder-side selection, not a decodable code.

## Retained weak-six evidence: what it does and does not show

The existing record-evidence fixture is not an escape experiment and must not
be retroactively described as one. Its frozen source
[`fixtures.py`](../record-evidence/fixtures.py) declares `weak-six` with:

* record width `b = 6` original bytes (`48` original bits), but the paid
  two-byte source alphabet maps these reversibly to `6` binary bits per
  exceptional record in REX1; `β=48` applies only to an untransformed raw record,
* `r = 2048` records (`12,288` input bytes),
* weak mutation of the first byte at every seventeenth record, and
* the two-byte source alphabet `{0, 255}`.

The retained encoder receipts report `record_dictionary` with `dictionary=144`
at its selected width12 (not the generator width6) and `bytes=1049`, while the restricted equality/count Auto route emits Raw at
`bytes=12312`; see
[`weak-six-rdic-encode.stdout`](../record-evidence/raw/weak-six-rdic-encode.stdout)
and
[`weak-six-auto-encode.stdout`](../record-evidence/raw/weak-six-auto-encode.stdout).
The report records the same complete archive sizes and explains that the global
rule is unavailable for the weak mutations
([`REPORT.md`](../record-evidence/REPORT.md)).

These numbers establish a retained **whole-archive** comparison for that
fixture and its declared codecs. They do not expose `e`, an escape-set rank,
or a paid partial-model wire format, so they cannot validate the formulae in
this addendum. In particular, `1049` is a dictionary whole archive with its
own dictionary/model description, while `12312` is the raw fallback container;
their difference is not an isolated model cost, state-space cardinality, or
escape bound.

## Control requirements

A future bounded screen of this design must retain separately:

1. whole archive bytes, split into framing, model, escape selector, normal-rank,
   raw escapes, padding, and checksum;
2. the exact `M`, `r`, `e`, `β`, model-value order, and all histogram counts;
3. raw, same-state-space uniform/superset, and paid dictionary controls; and
4. a fresh decoder check that reconstructs all records from stored fields.

A lower model description cost, a smaller conditional multinomial rank, and a
smaller complete archive are distinct observations. None is automatically
additive to another.
