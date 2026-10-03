# Exhaustive tiny relational search v2

This is an isolated mathematical search, not a production compressor and not
a corpus benchmark. Source and harness were frozen before dispatch. The Rust
program considers all **56,616 distinct pairs of 337 generic predicates** on
all256 possible eight-bit objects. An independent Python oracle regenerates
the predicates using a different expression implementation and confirms every
aggregate cardinality/category result. Python is not a codec.

| Quantity | Exact result |
|---|---:|
| Predicate count |337|
| Distinct unordered pairs |56,616|
| Empty intersections |1,148|
| Redundant/nested intersections |34,298|
| Independent intersections, after excluding nested |6,051|
| Other nonempty overlaps |15,119|
| Positive volume interaction, across all nonempty pairs |7,810|
| Member rank/unrank checks |4,183,808|
| Joint descriptions smaller than raw logical code |0|
| Both singleton descriptions lose, joint description wins |0|

Categories in the first four pair rows are exclusive by priority; positive
interaction is a separately counted property. Independence is the exact
integer identity `NA*NB=256*NI`, avoiding floating-point threshold decisions.
All feasible ranks are checked for each intersection by selected-set index.
The independent oracle verifies sizes and total number of these checks, not
the individual Rust rank values. Rust checks use the same membership set in
rank/unrank; this is not implementation-independent exhaustive rank validation.

The strongest reported interaction is `bit7=1` AND `x<=128`:
NA128, NB129, NI1. Interaction is log2(64.5), approximately6.011bits.
But the paid joint logical code costs27bits versus16bits for the raw logical
code, so it **loses11bits**. The surviving object is128; nothing about it is
known to the decoder from a corpus or filename.

## Frozen prefix accounting

Length8 is paid by gamma(8), seven bits. Raw mode adds one mode bit and an
eight-bit value, total16bits. Constrained mode adds a mode bit, gamma(k) for
the predicate count, all predicate tokens/parameters, and ceil(log2 NI) rank
bits. NI is derived from the stored predicates. Predicate type tags cost
two bits; bit position/value add3+1; XOR positions/value add3+3+1; popcount
adds4; numeric upper bound adds8. Fields have deterministic arity.

The source enumerates bit conditions16, pair parity56, population counts9,
and all numeric upper thresholds256. It does **not** emit physical archives,
implement that grammar's decoder, pay an integrity/version/container header,
or benchmark an established compressor. Consequently no actual archive win
is claimed; adding framing to these nonwins cannot create one under common
framing. Byte padding could eliminate differences but does not establish a
win. Direct raw is retained; a comprehensive direct-model search is pending.

## Failure preserved and scope

V1 completed the Rust loops but printed a hardcoded incorrect pair total56496.
The independent oracle correctly rejected it: 337*336/2 is56616. No successful
v1 qualification is claimed. `failed-v1/` retains source, freeze, harness,
stdout and failure receipts. V2 replaces the printed constant with a loop
counter and completes the oracle check. This is correction and qualification,
not repeated timing for averages.

Actual v2 receipts: CPU8, quota100000/100000, memory268435456, swap0, active
temporary allowance67108864bytes. Build limit120s; run limit60s. Aggregate
search+oracle wall0.32s/user0.31s/system0.00s, peakRSS13056KiB, zero swaps.
This does not measure practical compressor throughput. Exact source/binary
and toolchain bindings accompany the receipt packet.

Reproduction is `python3 docs/research/2026-10-03-constraint-space/search-evidence/schedule.py`
under the existing global lease. Completed evidence need not be rerun. Higher
order intersections, actual bit-prefix round trips, independent rank-value
oracles and computationally growing compiled diagrams remain untested here.

The two singleton predicates `popcount=0` and `popcount=8` each cost15
logical bits including the common length/mode/count fields, one bit less than
the16-bit raw logical code. These atomic wins are implied by the declared
grammar but were not separately counted by the source. They are not physical
archive wins. The zero-win result is strictly about joint pairs.

Conclusion: strong set interaction is common in this finite declared family;
paid joint-pair compression benefit is absent. This does not disprove every useful
constraint family, but it refutes equating interaction with net archive gain.
