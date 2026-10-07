# Independent constraint-space review

**Review scope:** read-only mathematical, source, and retained-evidence review.
No production source, experiment source, benchmark, build, or corpus job was
changed or rerun. This review covers `REPORT.md`, `adversarial-math.md`,
`prior-theory.md`, `tractable-families.md`, the isolated `CSP1` prototype, and
the completed one-shot evidence under `evidence/`.

## Verdict

The central theory is correct under the assumptions it states. A paid finite-set
description followed by an exact rank is established enumerative/two-part
coding. The defined pairwise set-volume interaction is negative pointwise
mutual information under a uniform finite universe. Its expectation is
`-I` only when the two labels are fixed deterministic partitions of that
uniform universe. The Kraft, exact marginal, certified pruning, and exact
completion-count arithmetic identities are sound.

The tiny prototype is a correct bounded exhaustive implementation of its own
fixed grammar. The retained run verifies counting and exact restoration for 13
models, producing 25 physical archives because the contradictory model has no
rank archive. The result is useful negative accounting evidence: intersections
reduce rank widths, but byte padding and the fixed paid header erase the tested
interaction gains. Every complete archive is larger than the corresponding
two-byte or five-byte materialized object.

This work does not establish a new coding principle, a practical compressor,
a generic constraint-discovery algorithm, or superiority to an established
direct code. The source-fixed catalogue example in `adversarial-math.md` is a
logical existence proof for a prefix code. It is not input-derived evidence and
must not be included in practical or generic-compression claims.

## Mathematical findings

### Set-volume interaction and mutual information

For uniform `X` on a universe of size `M`, fixed events `A` and `B`, and
nonempty intersection `I`, the report defines

```text
s(A,B) = log2(|A||B| / (M|I|)).
```

Since `P(A)=|A|/M`, this is

```text
log2(P(A)P(B)/P(A,B)),
```

which is negative pointwise mutual information. If `F=f(X)` and `G=g(X)` are
fixed deterministic labels, averaging the corresponding fiber value over
`P(F,G)` gives `-I(F;G) <= 0`. This expectation statement does not apply to a
pair of predicates selected after seeing `X`, to a nonuniform source while
still using cardinality ratios, or to a selected subset of favorable labels.
Those cases require the selection/model description and the actual source
probabilities.

The reported `k`-set expression is the negative pointwise total-correlation
analogue. It aggregates lower-order interactions and is not an irreducible
`k`-way synergy measure. The report states this limitation correctly. Calling
the quantity *set-volume interaction* is less likely to be confused with a
standard Shannon synergy decomposition.

The paid-gain identity is also correct:

```text
G(A,B)-G(A)-G(B)
  = s(A,B) + ell(A) + ell(B) - ell(A,B).
```

It compares a declared joint description with the two declared individual
descriptions. It is not invariant to changing the model language, framing, or
shared metadata policy.

### Kraft and finite ranks

For prefix-free model descriptions of length `D_d` and `N_d` valid fixed-width
ranks of width `R_d=ceil(log2 N_d)`, the complete Kraft contribution is

```text
sum_d 2^-D_d N_d 2^-R_d <= sum_d 2^-D_d <= 1.
```

Rejecting the unused ranks when `N_d` is not a power of two is required, as the
documents say. Overlapping model sets and multiple codewords for one object do
not invalidate prefix decoding because the stored description identifies the
model. To reason about selected per-object lengths, the encoder must choose a
deterministic codeword; selecting one codeword per object from the complete
prefix family preserves Kraft.

The four-codeword catalogue example (`0`, `100`, `101`, `11001`) is
prefix-free and its stated description Kraft sum, full codebook Kraft mass,
and mean selected length are correct. Its two constraint definitions are fixed
decoder assets. If the ranges are learned or changed per input, their complete
description must be added.

### Safe pruning

For a current set of exact size `N`, descendant size `N'`, and incremental
description cost `c`, the exact fixed-rank change is

```text
I = ceil(log2 N) - ceil(log2 N') - c.
```

If a certified lower bound `L <= N'` holds for every candidate remaining in a
branch, then

```text
I <= ceil(log2 N) - ceil(log2 L) - c.
```

Pruning at a nonpositive upper bound is sound. Current cardinality is generally
an upper bound on future intersections, so it cannot substitute for `L`.
Likewise, a certified upper bound on `N'` can prove a rank-level win, but neither
bound replaces the final serialized comparison. Framing, alignment, side
streams, and any replaced description must be included in `c`. Empirical
ratios and individually unprofitable predicates are not safe branch-pruning
rules when later intersections can create synergy.

### Exact rank and constrained arithmetic coding

Let `Z(u)` be the exact number of model completions after prefix `u`. The
conditional probabilities

```text
q(a|u) = Z(ua)/Z(u)
```

telescope to `1/|S|` for each complete member of a fixed finite set `S`.
Therefore lexicographic enumerative rank and an ideal uniform constrained
arithmetic model use the same admissible information and have ideal cost
`log2 |S|`. This is an ideal-probability equivalence, not a byte-for-byte
implementation equivalence. Rank rounding, finite integer intervals,
quantization, renormalization, termination, and container fields remain real
costs. An approximate normalized model can still be exactly decoded, but its
rate is `-log2 q(x)`, not the exact uniform-cardinality rate.

### Equality graph plus binary histogram

The new proposition in `REPORT.md` is correct and elementary. Equality
components of sizes `w_j` each choose one shared bit, so the number of
assignments with exactly `h` ones is

```text
[z^h] product_j (1 + z^w_j).
```

The suffix recurrence in the report exactly counts completions. Ordering
components by their first position preserves the original bit-string
lexicographic order, so the proposed branch-count rank and unrank are inverse.
With unary component weights summing to `n`, the `O(mh)` pseudo-polynomial DP
is valid; it does not solve binary-encoded general subset-sum counting. The
`n=4`, component weights `(2,1,1)` example has counts 8, 6, and 2, with
interaction `log2(1.5)`. Metadata can readily exceed that sub-bit ideal value.

This is a known coefficient-extraction/dynamic-programming consequence. The
report correctly avoids a novelty claim.

## Prototype source review

The isolated source hash is
`6aebc87fcb1048e16c01cbcd7340f3018205ce1bca2252c7ae8f45a8720b18e5`,
matching `evidence/freeze.json`. The runner and scheduler hashes also match
their freeze entries.

The implementation has the following verified properties:

* Byte universes are bounded to length two and nibble universes to length five,
  so exhaustive counts and rank scans stay below `2^20` objects.
* Membership, rank, and unrank use the same lexicographic integer order.
  The Python runner independently enumerates the predicate semantics and agrees
  with all 13 Rust counts. It is an independent counter, not an independent
  archive decoder.
* Byte prefixes contain 49 bits before the object/rank payload; nibble prefixes
  contain 42. All declared model fields are physically stored even when a mask
  makes some fields inactive. Raw and rank modes therefore pay the same model
  field layout.
* Payload width is recomputed from the decoded model. Unused ranks, wrong
  widths, nonzero padding, invalid model metadata, CRC mismatch, and trailing
  prefix bits are rejected. Reads use a regular-file check and `take(cap+1)`.
* Raw mode deliberately ignores membership and can carry an object alongside a
  contradictory model. Rank mode requires a nonempty model and membership.
* Nibble objects restore as exactly `n` physical bytes whose values are in
  `0..15`. The raw nibble payload is `4n` information bits, but the materialized
  source reported by the evidence is still `n` bytes. These are different
  accounting quantities and should remain distinguished.
* CRC covers the serialized prefix after the four-byte magic. The magic is
  validated separately and is not CRC-covered. This matches `PROTOTYPE.md`.
* `encode` starts a fresh process of the same executable with only archive and
  output paths, then byte-compares its output. This is process separation, not
  an independently implemented decoder.

Allowing nonzero inactive metadata creates multiple valid descriptions of the
same extensional model. That does not break decoding or Kraft accounting
because every field is stored, but a production grammar would normally require
canonical inactive fields or let the selector compare the extra descriptions.

## Evidence findings

I independently rehashed and parsed all 25 retained archives. Their sizes,
archive hashes, CRCs, and restored hashes match `evidence/results.json`.
Every successful raw and rank invocation records
`fresh_archive_only_decode:true` in its retained stdout. The physical outcomes
are:

| Case | Raw bytes | Rank bytes | Exact count | Finding |
|---|---:|---:|---:|---|
| byte none | 17 | 17 | 65,536 | no gain |
| byte A | 17 | 16 | 32,768 | one byte versus framed raw |
| byte B | 17 | 17 | 33,024 | no gain |
| byte intersection | 17 | 16 | 256 | ties byte A after padding |
| byte contradiction | 17 | no archive | 0 | raw only |
| byte expensive | 17 | 17 | 65,536 | paid redundant model does not win |
| nibble none | 16 | 16 | 1,048,576 | no gain |
| nibble equality | 16 | 14 | 16 | two bytes versus framed raw |
| nibble even | 16 | 16 | 524,288 | no gain |
| nibble intersection | 16 | 14 | 8 | ties equality after padding |
| nibble singleton | 16 | 14 | 1 | zero rank bits, header dominates |
| nibble redundant | 16 | 14 | 1 | ties singleton |
| nibble modulo-16 | 15 | 14 | 16 | one byte versus framed raw |

Thus the run validates the implementation and its accounting but does not show
paid intersection synergy in complete bytes. It also does not show compression
against a generic direct description: all complete archives exceed the two- or
five-byte materialized objects. The raw comparison is an internal `CSP1`
framed control with the same fixed metadata layout.

The build and control phases exited zero under CPU 8, `cpu.max=100000 100000`,
256 MiB memory, and zero swap. The sampled build high-water was below the
limit; the control phase retained its cgroup and affinity receipts. These are
qualification receipts for a tiny correctness run, not meaningful throughput
measurements.

The three malformed files all reject, but each retained stderr is `CRC`.
Consequently they demonstrate rejection of three physically corrupted inputs,
not three independently reached parser invariants. In particular, the appended
byte was not CRC-resealed and does not dynamically exercise the later
`trailing prefix` check. Source inspection supports that check; the current run
does not.

## Resolution of earlier evidence findings

The earlier packet findings are resolved within the following scope:

1. `evidence/binding.json` now records the source and binary hashes, compiler
   version and flags. `evidence/executed-source.rs` is byte-identical to the
   reviewed source and has the frozen source hash. The build and control raw
   receipts retain the actual commands, child exit status, affinity, cgroup
   limits and timing records.
2. Every successful row in `evidence/results.json` now records both
   `fresh_archive_only_decode:true` and
   `fresh_decoder_success_observed_by_encoder:true`. This establishes a fresh
   process of the same Rust implementation, not an independent decoder.
3. The evidence report now describes the result categories directly and the
   top-level README explains both verdict scales. The stale next-evidence text
   has been replaced by the actual completed qualification and remaining
   same-information/direct-model work.
4. The malformed scope is now accurate: all three retained corruptions fail
   CRC first, so later parser invariants remain source-inspected rather than
   dynamically reached.

A final manifest is still pending at review time. This is a packet-sealing
step only; no new codec run is needed.

## Claim boundary

The supportable conclusion is narrow:

* finite-set descriptions, exact counts, and ranks provide a sound language for
  reasoning about paid constraint models;
* intersections can have positive per-object set-volume interaction and can
  win in a deliberately frozen prefix catalogue;
* the tested `CSP1` intersections do not improve complete bytes over their best
  tested constituent rank archive after padding; and
* practical value now depends on a compact decoder-known or fully paid model
  language, tractable exact completion counts, a direct baseline, and evidence
  on predeclared non-toy inputs.

The primary antecedents support the report's conservative novelty boundary:
Cover's enumerative source coding already ranks members of constrained finite
sets; Kolmogorov structure functions already trade model complexity against
log set cardinality; deterministic decomposable knowledge representations
already support tractable model counting after compilation. The proposed CIX
architecture may still be a project-specific engineering direction, but the
current record does not establish a novel coding theorem or a novel general
constraint algebra.

## Latest objective and prior-art checkpoint

`RESEARCH-DIRECTION.md` now states the right governing objective: minimise a
decoder-complete serialized archive under declared encode, decode, memory,
temporary-storage and streaming budgets. Its listed fields form the necessary
accounting categories, and it explicitly requires a disjoint partition rather
than adding overlapping estimates. It also limits every comparison to a
declared feasible reference set. This prevents a sample result from being
reported as a universal or best-known compression result.

The URPILS reconstruction supports the revised direction. It distinguishes the
paper's MDL-motivated discovery score from a physical code, identifies its
approximate valid-assignment and error estimates, and does not promote those
estimates to exact prune bounds. It is evidence that automatic constraint
discovery plus admissible-space scoring is prior art. It is not evidence that
URPILS supplies an exact byte codec, rank/unrank, or compact intersection
compiler.

The exact-IR boundary is sound at its stated level. ROBDD/ZDD/SDD and
deterministic decomposable circuit rows are established representation-specific
counting and compilation techniques. The arbitrary-CNF closure argument is a
conditional complexity obstruction: a polynomial compiler and exact counter
for arbitrary conjunctions would place #SAT in polynomial time. It does not
assert an unconditional separation. The count-to-rank reduction correctly
requires exact counts after prefix conditioning; a single total model count is
insufficient. The current classification rows make no unsupported E/F novelty
claim.

The cardinality-interaction note is mathematically consistent with the main
report. Positive interaction is negative pointwise mutual information for the
observed event labels, while its distributional expectation is `-I` only for
fixed deterministic labels under the uniform universe. The affine rejection
rule follows from submodularity of matrix rank under the stated additive-cost
and common-framing assumptions. The equality-graph and fixed-histogram
coefficient DP is a valid nonlinear restricted example, not a new theorem.

## Exhaustive pair search v2

The v2 Rust source is bound consistently:

* `rust/cix-native/experiments/constraint-space/search.rs` and retained
  `search-evidence/executed-source.rs` are byte-identical with SHA-256
  `ea8db8b2c525ef3eb3a2cbf408f03d9c27c6b9054e3c67fc167ccc860631cc9c`;
* the runner and scheduler hashes match the pre-execution freeze; and
* the binding records the compiled binary hash, compiler version and flags.

The enumerated family and aggregate arithmetic are correct. Sixteen bit tests,
56 pair-parity tests, nine population-count tests and 256 thresholds total 337
predicates. The nested `i<j` loop therefore visits exactly
`337*336/2 = 56,616` unordered distinct pairs. The exclusive categories sum to
that total: 1,148 contradictions, 34,298 redundant/nested pairs, 6,051 exact
independence cases and 15,119 other nonempty overlaps. Positive interaction is
a separate property and occurs for 7,810 pairs.

For every member of every nonempty Rust intersection, `rank` counts smaller
members and `unrank` scans the same bit set to the selected index. The Rust
assertion therefore establishes 4,183,808 same-implementation inverse checks.
The Python oracle independently reconstructs the predicate truth tables and
agrees on every aggregate count and cost decision. Its
`rank_unrank_checks` value is the sum of intersection cardinalities; it does
not independently compute the individual ranks. The search report states this
limitation accurately.

The frozen logical accounting is internally decodable: gamma-coded source
length, a raw/constrained mode bit, gamma-coded predicate count, fixed-arity
tagged predicate tokens and a rank width derived from the stored predicates.
It charges 16 bits for raw and all predicate parameters for a pair. It emits no
archive, CRC, versioned container or physical decoder, so it supports an exact
logical-prefix result only. The documented lack of physical archives and the
pending direct-model search are material limits, not evidence failures.

The v2 resource receipts agree with the freeze: CPU 8, one-core quota,
268,435,456-byte memory limit, zero swap and a 67,108,864-byte temporary
allowance. Build and search children exited zero. These receipts qualify the
bounded one-shot search; the subsecond observation is not codec throughput.

The failed v1 packet is preserved correctly. Its executed source differs from
v2 only by replacing the hardcoded printed pair count `56,496` with the
dynamically incremented count. The loops ran, but the independent Python
oracle observed the true `56,616` and caused the run to exit one. V1 supplies
no qualified result.

The qualified negative is **zero two-predicate joint descriptions smaller than
the 16-bit raw logical route**. It is not zero paid wins over the complete
raw/single/pair grammar. The source calculates singleton costs but never counts
or selects singleton wins. In particular, `popcount=0` and `popcount=8` each
describe a singleton and cost

```text
7 common + 1 mode + 1 gamma(1) + 6 predicate + 0 rank = 15 bits,
```

one bit less than raw. The README and search report now state this scope and do
not turn these logical atomic wins into physical archive claims. This
correction needs no rerun and does not weaken the conjunction result.

The stronger selector contract in `synergy-search-theory.md` remains future
work: v2 does not deduplicate extensionally equal models, compare every pair
with its shortest equivalent direct model, or prove that an implemented
selector equals the exhaustive argmin. Since every pair already loses to raw,
those missing controls cannot create a winning pair here. They do prevent this
run from qualifying the proposed general selector. Higher-order intersections,
independent rank-value verification and physical prefix round trips also remain
untested.

## Current approval boundary

The CSP1 prototype source and completed tiny physical qualification are
approved within their documented scope. Their earlier binding, fresh-child,
label, stale-text and malformed-path findings are resolved as recorded above.
The exhaustive v2 source and its 56,616-pair result are approved as an exact
finite logical search. Packet sealing still requires the planned final hash
manifest.

The combined checkpoint supports continuing the restricted computational
question and abandoning a new-general-principle claim. It does not support
production integration, a complete practical selector, an established
compressor win, or a full-paper novelty/exhaustivity claim.
