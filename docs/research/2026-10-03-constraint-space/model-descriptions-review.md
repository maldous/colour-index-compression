# Independent static review: MSL1 model descriptions

**Reviewed main source:** `rust/cix-native/experiments/constraint-space/model_descriptions.rs`  
**SHA-256:** `8258d42130bd37a062ae908e3e1de6328d08ed6042cf105786cc31e421d071cd`  
**Reviewed BDD helper:** `rust/cix-native/experiments/constraint-space/model_bdd.rs`  
**SHA-256:** `ba90d538f872e6899483d65f5dffc14ab1e1b9cd59c424e9861038dfaa35172a`  
**Review type:** source and arithmetic only; no compile, test or experiment run.

## Verdict

No remaining source-correctness blocker was found for the bounded prescribed-
model instrument or its separate bounded discovery command. A preflight parser
defect in the one-byte width-2 Bitset
form allowed nonzero unused high bits. The current main source rejects that
noncanonical padding; this review is bound to the corrected hash above.
The final hash also adds the explicit `(u16, u16)` RLE tuple type required by
the compiler; it does not change the RLE wire or run construction semantics.

MSL1 can validly compare seven stored descriptions of one exact local member
set: combinadic subset, truth bitset, run list, flat atoms, packed flat atoms,
shared-scope atoms and canonical ROBDD. Every structural route derives the
same ascending member order, so it also derives the same mixed-radix sequence
rank and payload. Complete wire differences are therefore model-description
differences.

The `encode ... auto` route is not model discovery: it receives the bit width
and atoms in a model file, checks that prescribed model, constructs its stored
representations, and selects the smallest complete archive. The separate
`discover INPUT ARCHIVE` route does derive a model from source bytes. Its
search is a finite, fixed primitive bank over aligned binary records. It is
valid evidence of bounded discovery in that declared grammar, but not of new
primitive synthesis, unrestricted CSP induction, or period/grammar discovery.

## Exact model semantics and common rank

The text model supplies `2 <= b <= 12` and at most 32 atoms. Atoms are sorted
and deduplicated syntactically. Their operations are:

* exact selected-bit count;
* upper-bounded selected-bit count;
* selected-bit parity; and
* equality/XOR of the lowest and highest bit selected by a scope mask.

Masks must be nonzero and contained in the `b`-bit universe. Count parameters
are bounded by `b`, parity parameters by one, and the endpoint operation needs
at least two selected positions. Exhaustive enumeration of at most `2^12`
values yields the authoritative ascending local member list. Empty exact sets
are rejected.

Each structural wire is serialized and immediately parsed back; the parsed
member list must equal that authoritative list before ranking begins. On
decode, each representation again reconstructs an ascending list. With local
cardinality `M` and `r=n/b` records, all routes therefore use

```text
COUNT = M^r
rank_bits = bit_length(COUNT - 1)
```

and the same base-`M` sequence order. `BigUint` preserves the full count and
rank. Rank integers use exact big-endian byte widths and reject nonzero high
padding and out-of-range values.

Flat and Shared normalization is canonical for the supplied atom list: sort,
deduplicate, validate, and reject noncanonical wire order. It is not a
semantic minimizer. It does not remove implied or tautological atoms or merge
different syntactic scopes that happen to define the same truth set. Claims
should call these prescribed-formula representations rather than the shortest
possible formula for the set. The truth-set representations and ROBDD do not
retain those syntactic redundancies.

## Wire accounting

The complete MSL1 layout is:

| Field | Bytes |
|---|---:|
| magic `MSL1` | 4 |
| version and representation kind | 2 |
| source length | 4 |
| record width | 1 |
| sorted two-byte alphabet | 2 |
| model length | 2 |
| model | representation dependent |
| sequence rank | `ceil(rank_bits/8)` |
| CRC-32 | 4 |

Thus every structural archive has exact size

```text
19 + model_bytes + ceil(rank_bits/8).
```

Raw has the same 19-byte header/CRC area plus `n` literal source bytes. The
JSON currently reports Raw with `rank_bytes=0`; its literal payload remains
physically included in `total_bytes`. Evidence should either add an explicit
literal/payload field or derive it as `total - 19 - model` rather than treating
Raw as having no body.

The model wire costs are physically complete:

* Subset: two-byte member count plus byte-rounded combinadic subset rank;
* Bitset: `ceil(2^b/8)` bytes, with unused high bits required to be zero;
* RLE: two-byte run count plus four bytes per canonical separated run;
* Flat: one-byte atom count plus four bytes per atom;
* Packed Flat: one-byte count plus three bytes per atom;
* Shared: mask-table count, sorted two-byte masks, atom count and two-byte
  `(operation, scope-id, parameter)` records;
* BDD: four-byte count/root prefix plus five bytes per nonterminal node.

The representation kind in the common header is the route label; there is no
unpaid selector. Auto compares the final archive lengths and preserves the
declared candidate order on exact ties.

## Parser and corruption review

The envelope checks magic, version, representation kind, CRC, source/model
caps and the exact physical split between model and rank body. Raw requires
zero record width, alphabet and model length, and an exact `n`-byte body.
Structural modes require a nonempty aligned source, a sorted two-symbol
alphabet and a valid record width.

Representation parsers enforce:

* Subset count/rank bounds, exact rank length, high padding and canonical colex
  inverse;
* exact Bitset length and, after the preflight fix, zero unused high bits;
* positive, ordered, nonadjacent RLE runs with no overlap or universe overrun;
* exact Flat/Packed length, valid atoms, sorted order and no duplicates;
* sorted Shared masks, valid scope IDs, no unused stored scope, canonical atom
  order and the unique `[0,0]` empty-atom form; and
* the BDD invariants described below.

After model parsing, rank-body length, padding and range are derived from the
decoded exact member set. Output is allocated only after the source cap and
model have been checked. A failed command writes no new output, although a
caller should remove a pre-existing output path before negative tests to avoid
mistaking stale bytes for current output.

CRC-32 detects accidental corruption and is not an authenticity mechanism.
This isolated experiment does not claim hostile-input cryptographic security.

## ROBDD review

The helper uses a fixed MSB-to-LSB variable order. Construction recursively
builds low then high branches, eliminates equal branches, interns identical
`(variable, low, high)` triples and assigns deterministic postorder IDs.
Terminals are IDs zero and one. At `b <= 12`, the unreduced full binary tree
has at most 4,095 nonterminal nodes, exactly the declared cap.

The parser requires exact wire length, bounded IDs, children preceding their
parent, strictly increasing variable index along every edge, unequal low/high
children, unique triples and reachability of every stored node. It enumerates
all at most 4,096 assignments, then re-encodes the member list and requires
byte identity. That last check fixes the postorder ID allocation and rejects a
semantically equivalent noncanonical layout.

Skipped variables are handled correctly. Membership follows only variables
present on a path; omitted variables remain unconstrained during enumeration.
Terminal roots correctly encode the empty and full universes, although MSL1
rejects an empty structural member set at the enclosing format level. No
unsafe code or unbounded graph traversal is present.

## Allocation and computation bounds

All filesystem reads use `Read::take(cap+1)` and reject the extra byte. Source
length is at most 16,384 bytes, text model input at most 4,096 bytes, stored
model at most 21,000 bytes and archive at most 40,000 bytes. The authoritative
truth table contains at most 4,096 `u16` values.

Actual representation maxima fit those caps:

* Subset and Bitset are at most about 514 and 512 bytes respectively;
* canonical RLE is at most 8,194 bytes;
* Flat, Packed Flat and Shared are at most 129, 97 and 130 bytes;
* BDD is at most `4 + 5*4095 = 20,479` bytes.

Because `M <= 2^b`, the global rank width is at most `n` bits and its body at
most 2,048 bytes. Even the largest BDD archive is therefore at most 22,546
bytes, within the 40,000-byte archive cap. Exact local enumeration, BDD
construction/validation and `BigUint` work are all bounded by these limits.

## Auto behavior and errors

Raw accepts every bounded byte input. Structural eligibility requires exactly
two observed symbols, record alignment, a nonempty prescribed set and every
source record inside that set. Empty, mono-symbol, nonbinary, misaligned or
out-of-model inputs leave Auto as an explicit Raw-only choice with a diagnostic.
Forced structural requests propagate the same conditions as errors.

For eligible inputs, Auto evaluates Raw then every structural representation.
Only explicit size-bound failures may be logged and skipped. Other candidate
failures are reported and abort the encode, preventing silent omission of a
representation from the comparison. This is the correct fail-closed behavior
for a same-space experiment.

Auto's Shared candidate automatically interns repeated masks from the supplied
atom list. That is deterministic metadata deduplication. It is not evidence of
automatic relationship discovery from source bytes.

## Bounded native discovery

Discovery first requires exactly two observed byte symbols. It considers each
aligned width from 2 through 12 and converts every complete record to a binary
word using the stored sorted alphabet. Empty, mono-symbol and nonbinary inputs
take the complete Raw route. No filename, source identity, prescribed model or
external model asset enters this command.

For each eligible width the fixed bank derives:

* an exact full-word popcount when every observed count is equal, otherwise a
  full-word upper bound at the observed maximum when that maximum is not the
  tautological `b`;
* full-word parity only when popcount is not exact and parity is constant;
* a constant XOR relation between the first and last bit; and
* every constant XOR relation between adjacent bits.

Atoms are normalized, then removed in stable order only when exhaustive
enumeration proves that removing the atom leaves the complete local truth set
identical. This is semantic redundancy removal over at most 4,096 assignments,
not a heuristic equivalence claim. The maximum initial bank at one width is
bounded by the count/upper-bound atom, parity, the endpoint relation and
`b-1` adjacent relations. The width-2 duplicate endpoint relation is omitted.

Raw is considered first. For every eligible width, all seven structural routes
are materialized as complete MSL1 archives in this order: Subset, Bitset, RLE,
Flat, Packed Flat, Shared and BDD. Selection uses strict size improvement, so
ties retain Raw, then lower width, then the earlier representation. There is
no candidate skip path in discovery: any construction failure aborts instead
of silently narrowing the search. With at most eleven widths, candidate count
is bounded by `1 + 7*11 = 78`.

The archive contains the selected representation, width, alphabet, exact
model description or truth set, source length, rank and CRC. A fresh decoder
therefore needs neither the discovered atoms nor the original input. The JSON
`selectedatoms` field is diagnostic provenance for the selected truth set; it
is not an unpaid decode asset. When Raw wins, `selectedb` is zero and
`selectedatoms` is empty.

## Timing scope

The emitted timing labels require careful interpretation:

* `model_construct_ns` starts after reading the source and covers reading the
  model text, UTF-8/number parsing, validation, sorting and deduplication. It
  does not include construction of the binary model representation.
* `count_ns` is a separate probe containing one exhaustive local-table
  construction and one global `M^r` BigUint cardinality computation. The table
  and cardinality are intentionally recomputed later during encoding.
* `rank_ns` and `portfolioencode_ns` currently carry the same coarse interval.
  It covers structural eligibility and source scanning, every candidate's
  local enumeration/model/rank/archive construction and, for Auto, the full
  representation portfolio plus selection. It is not pure ranking time.
* `wire_construct_ns`, `model_compile_ns`, `cardinality_ns` and
  `symbol_rank_ns` describe only the ultimately selected candidate. For Auto,
  they are not sums over discarded candidates. Local member enumeration occurs
  before `wire_construct_ns`; rank packing, header and CRC construction occur
  after the reported selected kernels. All of that work remains included in
  the coarse portfolio interval.
* `internal_decode_ns` covers the full in-process semantic decode, including
  envelope/CRC/model/count/unrank work, but no output-file write.
* the separate decode command reports model compilation, cardinality and
  unranking kernels. Its overall `decode_ns` begins after archive-file reading
  and ends after output-file writing, so it includes envelope/CRC/rank parsing
  and output I/O as well.

For `discover`, `discovery_ns` covers alphabet inspection and derivation plus
semantic minimization of the candidate atom lists. `portfolioencode_ns` starts
after that and covers Raw plus every complete structural archive construction
and selection. `rank_ns` repeats that coarse portfolio interval. The four
kernel fields describe only the selected archive. These fields do not by
themselves expose per-width or discarded-candidate costs.

These are one-shot instrumentation fields with different scopes. They must not
be summed or compared as if each isolated one primitive, and they do not
support a speed ranking without an explicitly matched measurement design.

## Decoder and asset accounting

The corrected `sdl-experiment-design.md` uses the standard archive-comparison
convention: generic shared decoder software is excluded symmetrically from
every candidate and control, while its exact source/build identity is frozen
as provenance. The physical MSL1 wire accordingly stores no decoder binary.
This is coherent and does not leave a candidate-specific hidden asset.

Every input-specific requirement is present in the wire: representation kind,
record width and ordering convention, alphabet, exact model bytes, source
length, sequence rank or literal payload, and CRC. The current instrument uses
no source-specific pretrained dictionary or external model. Any future such
asset would have to be stored and charged.

Subject to the distinct prescribed-model and finite-discovery claim boundaries
and accurate timing labels, the two source files are statically approved for
frozen execution. The pre-execution harness independently checks the selected
archive's complete size/CRC, discovered truth set and rank, expected candidate
count, fresh restoration, clean fallback errors and the corrected Bitset
padding rejection. Those checks qualify the frozen cases; they do not expand
the primitive bank or establish general discovery beyond it.
