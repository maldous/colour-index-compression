# Prior art and methodological boundary

**Scope.** This note bounds the complementary-predictive-information audit. It
is a literature and method note, not a claim that any CIX route currently
exposes a usable distribution, an implementation proposal, or an empirical
result. The code inventory and trace results determine which parts apply.

## Established work

Combining causal predictive distributions before entropy coding is established
source coding and online prediction. A finite Bayesian model mixture is:

```
P_t(x) = sum_i w_i,t P_i,t(x)
w_i,t+1 = w_i,t P_i,t(x_t) / P_t(x_t).
```

With a fixed prior, this is both a causal probability assignment and the
log-loss/Bayesian posterior update. If every `P_i,t` is a normalized
distribution available before `x_t`, the mixture is normalized and a decoder
which starts from the same prior and sees decoded history reproduces the
weights. Its cumulative ideal log loss is no worse than expert `i` plus
`-log2 w_i,1`; a uniform `K`-expert prior costs at most `log2 K` ideal
bits. This is an established coding interpretation of Bayesian mixtures; see
Hutter's [Bayesian sequence-prediction treatment](https://arxiv.org/abs/cs/0301014).

Multiplicative/exponential weighting is established online learning. Freund
and Schapire give the decision-theoretic multiplicative-weight framework and a
general-loss setting ([article](https://doi.org/10.1006/jcss.1997.1504),
[author-hosted PDF](https://www.face-rec.org/algorithms/Boosting-Ensemble/decision-theoretic_generalization.pdf)).
For log loss, the probability-mixture/posterior form above is the primary
baseline because it remains a proper distribution and has an exact code-length
meaning. A generic Hedge implementation needs a frozen learning rate, loss
range and any probability floor; otherwise its code probabilities and regret
claim are not determined.

Switching experts are also established. Fixed-share updates a distribution from
the observed loss then reserves mass for potential switches. It compares to
expert sequences while charging a prior/model cost for their identities and
transitions. Herbster and Warmuth introduced the tracking formulation and
fixed-share algorithm ([paper record](https://doi.org/10.1023/A:1007424614876),
[PDF mirror](https://citeseerx.ist.psu.edu/document?doi=a9c5a8d53909d896b042d14359419c0932be7f88&repid=rep1&type=pdf)).
A compression control must report predictive loss *and* transition prior (or
equivalent switching complexity); an after-the-fact piecewise winner without
that cost is only another oracle.

Context-tree weighting (CTW) is a relevant universal-code example. It
recursively mixes bounded-memory context-tree models and parameter
distributions causally (a "double mixture"). The original paper accounts for
coding, parameter and model redundancy and gives linear time/storage in source
length ([Willems, Shtarkov and Tjalkens, 1995](https://doi.org/10.1109/18.382012);
[open institutional record and manuscript](https://research.tue.nl/en/publications/the-context-tree-weighting-method-basic-properties/)).
Hierarchical causal mixtures and universal model averaging are therefore not
novel simply because their CIX experts differ.

PAQ-family context mixing is direct prior art for heterogeneous causal
predictors. Mahoney describes independent bit predictions, confidence/context
signals, online weight adjustment after arithmetic coding and weighted
combination in a lossless compressor
([technical report](https://repository.fit.edu/ces_faculty/166/)). The
author-maintained technical account documents PAQ's logistic-domain mixing,
context-selected online weights and fixed-point implementation
([Data Compression Explained, §4.3](https://mattmahoney.net/dc/dce.html#Section_43)).
Mattern studies linear and geometric compression mixtures, including a
non-binary generalisation and convex weight fitting
([DCC paper/preprint](https://arxiv.org/abs/1302.2839)).

## Probability and coding discipline

The audit's expert is a probability assignment, never merely a route,
transform, backend or entropy coder. At every traced position it must provide
a non-negative, normalized distribution over the same target alphabet before
that target is observed. `P_i,t(x_t)=0` gives infinite ideal log loss, so
smoothing and initial state must be explicit and decoder-identical.

For a byte expert derived from a bit predictor, use:

```
P_i,t(byte) = product_b P_i,t(bit_b | decoded prefix, earlier bits of byte).
```

Each factor may use only history and already-coded bits of that byte. This
eight-branch construction is normalized when the bit conditionals are
normalized. It is invalid to use a later target bit or to treat one binary
probability as a 256-way byte distribution.

The arithmetic static mixture `P_mix=sum_i w_i P_i` is normalized only if
experts are normalized on the same alphabet, `w_i >= 0`, and
`sum_i w_i=1`. A geometric/logit mixture is a different model and requires
an explicit multi-symbol normalizer. PAQ's binary
`squash(sum w_i stretch(p_i))` is normalized because the complement is
`1-p`; it does not by itself specify a normalized 256-way byte mixture.

Ideal `-log2 P` diagnostics are not archive sizes. Finite precision,
termination, model/update description, framing and emitted parameters remain
physical-code costs. No ideal-bit improvement is a complete-archive claim
until a deterministically decodable physical stream is measured.

## Oracle controls and causal qualification

The per-symbol minimum-loss oracle observes `x_t` before choosing its expert.
It measures disagreement plus selection advantage, not a decoder-reproducible
code. Label it **HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY** throughout.
Its gap may be large even when no causal gate can predict the winner.

Controls establish the selection-advantage floor:

* Exact duplicate traces must have zero oracle gap (within trace arithmetic).
  Any nonzero result is an alignment or accounting defect.
* Redundant or deliberately perturbed copies distinguish near-duplicate noise
  from independent information.
* Fixed weak forecasts quantify the effect of adding poor experts.
* Time-shifted/alignment-broken traces, used only as deliberately invalid
  diagnostics, test accidental target alignment and are never achievable
  experts.
* Simulated independent forecasts matched in marginal log loss/confidence
  measure hindsight selection bias. Freeze their seed, generator and use
  before the held-out run.

Average correlation is insufficient because log loss can concentrate in rare,
catastrophic errors. Conditional tails, uncertainty-conditioned loss and
realised-symbol disagreement are useful diagnostics but do not create a
causal selector.

Choose expert membership, static weights, smoothing, update rule, learning
rate, floors, and gate feature/bin definitions on a predeclared development
split; freeze them before held-out tracing. Equal-weight and best-single
baselines must accompany frozen optimized weights. Re-fitting a threshold,
bucket, feature, stopping rule, or weight on held-out outcomes makes that
result development evidence.

An online mixture assigns the probability before `x_t`, then updates using
`x_t`; the decoder replays the same initial weights and rule. Every gate
feature must be recoverable before the target: for example confidence, context
depth, already-available match state, past loss, run length or fixed position
modulo. Bound gate capacity and train only on development data. Retain it only
for held-out gain beyond frozen static mixing and the predeclared online
baseline, accounting for computation/state; otherwise close it.

## Narrow prospective contribution

"Mix compression experts" has no general novelty claim: Bayesian averaging,
expert advice, switching, CTW and PAQ/context mixing already cover it. An
oracle gap also does not establish usable predictive information.

A possible CIX-specific result would instead need evidence for something
concrete: a newly exposed causal native signal, compatible-distribution
extraction for heterogeneous models, an expert-pruning method with marginal
conditional value, or a bounded decoder-replayable gate with a held-out gain
beyond these controls. All are conditional on the code inventory, frozen
qualification, and physical-codec accounting.

## Source limitations

This review uses the cited original articles and author/institutional copies
where available. PAQ details come from Mahoney's report and explanatory
material, not a formal specification of current CIX or any PAQ derivative. It
is not a patent search, exhaustive literature review, source-code audit,
experiment, clearance opinion, or priority claim.
