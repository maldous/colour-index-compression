# Constraint-space finite prototype

**Status:** prepared only. The isolated source is
`rust/cix-native/experiments/constraint-space/main.rs`. No build, run, or
measurement is authorized outside a root lease. This does not change a native
format or selector and makes no novelty claim.

## Premise

Intersecting two broad descriptions can beat storing two independently coded
sets. A single enumerative or arithmetic constrained model can encode the same
intersection, so the intersection itself establishes no new coding method.
This prototype charges the model prefix and compares its complete bytes with a
raw fallback. A direct constant or run description can beat the constrained
rank result; that outcome is an explicit negative result, not an exception.

## Exact byte toy

The two-byte universe has 65,536 objects. With `x0` the first byte:

| Predicate | Count |
| --- | ---: |
| none | 65,536 |
| A: `x0 < 128` | 32,768 |
| B: `x0 >= 127` | 33,024 |
| A and B: `x0 = 127` | 256 |
| redundant: `x0 < 128` plus `x0 < 200` | 32,768 |
| contradictory: `x0 < 127` plus `x0 >= 127` | 0 |
| expensive: `x0 >= 0` | 65,536 |

The prototype enumerates lexicographically, ranks only members, and un-ranks
from archive bytes alone. A contradiction has no rank archive and must use raw
mode. Redundant and expensive constraints retain their full prefix cost.

## Nibble controls and paid synergy

Nibbles have length 1–5 and at most `16^5 = 1,048,576` objects. The model can
apply an equality-chain mask, one position modular condition, and an exact
histogram count. Example exact counts for length five are: equality chain
`x0=x1=x2=x3=x4`, 16; position-0 modulo-2 residue-0, 524,288; histogram
`count(value=0)=5`, 1; equality chain plus even first nibble, 8.

The paid-synergy screen currently uses the implemented byte predicates, not a
claimed nibble all-symbol threshold mode: `x0 < 128` and `x0 >= 127` reduce
the two-byte 16-bit rank to the 8-bit intersection rank. Their two stored
8-bit thresholds and shared prefix can outweigh this reduction. Full prefix
bytes decide the result. The nibble harness implements equality chains,
position-modular conditions, and histogram counts only; it does not claim an
all-symbol threshold experiment.

## Archive

`CSP1` has a bit prefix containing version, domain tag, raw/rank mode, length,
constraint mask, equality mask, modular position, histogram value/count,
payload width, and declared zero padding. Byte mode stores upper and lower
thresholds as two 8-bit fields. Nibble mode stores modular modulus in five
bits and residue in four bits. The prefix carries either raw object bits or the
enumerative rank, then zero alignment padding and a CRC-32 over the full prefix
bytes. All fields are charged. Decoder checks version, model masks, metadata
ranges, exact payload width, rank range, CRC, zero padding, and no trailing
prefix bits. Raw mode is an explicit caller choice and works for a
contradictory model; it is not selected automatically. It has no input object,
dictionary, search, or encoder state. Restored byte objects are exactly `n`
bytes; nibble objects are exactly `n` bytes, each in `0..15`, while their raw
coding baseline remains `4*n` bits.

The harness command plans are `count`, `encode`, and `decode`; `encode` starts
a fresh `decode` process and compares the restored object bytes. Results must
retain complete archive bytes, raw bytes, prefix field values, exact count,
fresh-child status, and source/restored hashes.

## Scope

This is a tiny exhaustive model for theory and accounting. It does not imply
that constraints should be detected from input in a generic policy, nor that a
constraint intersection is better than an equivalent single enumerative model.
