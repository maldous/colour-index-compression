# Independent static review: RDIC direct record dictionary

**Scope:** read-only source and prepared-harness review. No build, test,
generator, codec or corpus job was launched by this reviewer. The approved
source is
`rust/cix-native/experiments/constraint-space/record_dictionary.rs` at
SHA-256
`cc1cf83a91ca0c9945281187be0136ca26d7c5e49237e29b5b8b8d7d1c07dbfb`.
The retained `record-evidence/executed-dictionary-source.rs` is byte-identical.

## Verdict

The current RDIC source is approved as a bounded direct learned-record control.
Its dictionary and sequence spaces are exactly counted, both ranks are
physically stored with canonical widths, the colex and mixed-radix inverses are
correct, and decoder-controlled allocations remain within small declared
bounds. It stores every input-dependent reconstruction field.

An earlier source version propagated the expected `dictionary > 256` candidate
rejection and thereby aborted the whole encode after Raw and earlier valid
candidates had been built. The approved source fixes that failure mode by
checking the observed dictionary size and continuing to the next width. Raw
fallback and prior candidates now survive the declared dictionary cap.
Unexpected construction failures still propagate.

## Dictionary subset rank

For record width `b`, the word universe is the integers
`0..2^b` in increasing numeric order. The observed dictionary is a sorted,
strictly increasing subset

```text
a_0 < a_1 < ... < a_(m-1).
```

RDIC uses the standard colex combinadic rank

```text
sum_i choose(a_i, i+1),
```

whose cardinality is `choose(2^b,m)`. `colex_unrank` processes indices from
`m` down to one, choosing the largest value below the previous upper bound
whose binomial term does not exceed the remaining rank. Subtracting that term
leaves the unique lower-index combinadic expansion. The final strict-order and
zero-remainder checks reject malformed decompositions. Initial upper bound
`2^b` keeps every value inside the universe.

The zero-rank boundary is handled correctly: at index `i`, the smallest legal
value is `i-1` and `choose(i-1,i)=0`. A full-universe dictionary also has
cardinality one and a zero-bit rank; descending unrank reconstructs every
universe value in order. The stored dictionary width is the bit length of
`choose(2^b,m)-1`, exactly `ceil(log2 cardinality)`, with zero bits for a
singleton dictionary space.

The prepared Python oracle independently rebuilds the sorted observed words
and computes the same binomial sum with `math.comb`. Comparing that integer to
the retained dictionary bytes is an independent rank check. Fresh Rust decode
checks the inverse implementation; Python is not a separate archive decoder.

## Sequence rank and inverse

Once the ordered dictionary is known, every source record maps to its binary
search index in `0..m`. For `r=n/b` records, the sequence space has exact
cardinality `m^r`. Encoding applies

```text
rank = (((digit_0 * m + digit_1) * m + digit_2) ...),
```

so the first source record is most significant. Decode takes remainders while
filling records from `r-1` down to zero, exactly reversing that order. Since
`m<=256`, each remainder fits the first `u32` limb returned by `BigUint`.
The initial range check and final zero-rank check close the inverse contract.

The Python harness independently maps every source word through the sorted
dictionary and recomputes the same positional integer. The sequence width is
the bit length of `m^r-1`. Dictionary and sequence ranks are serialized as two
separate big-endian integers, so their actual payload cost is

```text
ceil(dictionary_width/8) + ceil(sequence_width/8),
```

including separate byte padding. They must not be presented as one jointly
packed ideal bit count.

## Complete framing and model cost

The fixed header is 15 bytes:

```text
magic 4 + version 1 + mode 1 + source length 4
+ record width 1 + dictionary count 2 + symbols 2.
```

The CRC adds four bytes, giving a 19-byte fixed frame. A dictionary archive is
therefore:

```text
R_D = ceil(log2 choose(2^b,m))
R_S = ceil(log2(m^r))
bytes = 19 + ceil(R_D/8) + ceil(R_S/8)
```

with each cardinality-one rank width defined as zero. Raw is `19+n` bytes and
requires zero record width, dictionary count and symbols.

The dictionary subset rank is model data, not ordinary sequence payload. The
prepared result retains its bit width separately from the sequence width and
uses the complete archive byte length for selection. Final reporting should
keep the 19-byte frame, byte-padded dictionary rank and byte-padded sequence
rank distinct; `framing_and_model_header_bytes=19` describes only the fixed
header plus CRC, not the full learned model.

No source identity supplies a model. The two sorted byte symbols, record width,
dictionary cardinality and source length are stored. Dictionary contents are
reconstructed from their subset rank in the fixed binary-word universe.
Record count and both rank widths are derived exactly. Record alignment is the
fixed decoder convention starting at offset zero.

The encoder scans every dividing width from 2 through 12 and selects the
shortest complete archive against Raw, retaining the earlier candidate on a
tie. Dictionaries above 256 entries are declared inadmissible and skipped.
This is an exhaustive minimum over that explicit bounded shortlist, not over
arbitrary dictionary, grammar or phrase representations.

## Parser and resource bounds

Source input is bounded to 16,384 bytes. Archive reads are bounded to 20,000
bytes with a one-byte excess probe. Decode rejects short/oversized envelopes,
magic, CRC, version, unknown mode, oversized source length, invalid record
width or division, zero or over-cap dictionary count, a count larger than the
word universe, and unordered/equal alphabet symbols.

Both rank widths are derived before slicing. The decoder requires the body to
equal the sum of their separately padded byte lengths, rejecting trailing and
truncated ranks. `unpacked_integer` rejects nonzero high padding, and explicit
range checks reject unused fixed-width values. Raw requires exact body length
`n` and canonical zero metadata.

The largest word universe contains 4,096 values, while the stored dictionary
contains at most 256. Colex reconstruction allocates 256 machine integers and
performs bounded binary searches over the universe. The sequence rank has no
more than `n` information bits because `m<=2^b` and there are `n/b` records.
The dictionary rank is also bounded by the declared universe and count. Output
allocation is capped at 16,384 bytes, and dictionary digits index only a
validated `m`-element vector.

`MAX_ARCHIVE=20,000` exceeds every Raw archive under the source cap and the
bounded dictionary representation. It remains an explicit encoder and decoder
limit. CRC-32 detects accidental corruption; it is not authentication. A
bounded reader can still wait for an open pipe, so the outer wall limit remains
part of qualification.

## Control and evidence boundary

RDIC is the necessary direct explanation for the strong ERC1 fixtures: a small
record vocabulary can use the same per-record index width as an equality/count
intersection after paying its dictionary. Including the complete RDIC archive
in L0 prevents that ordinary learned-word explanation from being omitted.
It does not exhaust stronger dictionary, entropy-coded sequence, grammar or
same-information arithmetic controls.

The updated runner invokes RDIC for every fixture, fresh-decodes its archive,
checks exact source SHA-256 and CRC, and independently recomputes the dictionary
and sequence ranks. The aggregate phase now passes zero processed bytes to the
shared bounded runner, avoiding the earlier fabricated throughput receipt.
Source, retained source, runner, scheduler and dependency hashes are bound in
the updated freeze.

The runner records a single complete RDIC winner across widths. It does not
retain every losing RDIC candidate, and its timings include RDIC's internal
same-process round trip before the separately timed fresh decode. Size is the
primary matched fact; timing scope must remain explicit.

This approval covers an isolated direct control and its parser. It does not
qualify ERC1 results in advance, establish production readiness, or support a
novelty claim.
