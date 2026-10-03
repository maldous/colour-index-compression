# Independent static review: RNC1 normalized frame

**Reviewed source:** `rust/cix-native/experiments/constraint-space/normalised_frame.rs`  
**SHA-256:** `a7d60f029853c19eceabd8f28627088f54cb2e22de3307d10d9f9eea34807fdf`  
**Review type:** source and arithmetic only; no compile, test or codec execution.

**Execution addendum:** the frozen runner
`0f9a3dea36dff91518bef95a5756803ee8d4c2273650cadd318cee22ac98f61b`
now satisfies the cross-width intersection requirement below. It enumerates
E and C in EC's common block, requires aligned divisibility, proves their
intersection equals EC's table, and checks the resulting whole-sequence
cardinality widths. The earlier preflight evidence gap is resolved.

## Verdict

No source blocker was found for the stated isolated diagnostic. RNC1 is a
bounded framing adapter around existing ERC1 and RDIC archives. It is not a
new coder and must not be reported as a compression improvement.

The reviewed revision also constructs a native two-symbol uniform control.
That route correctly replaces the unsuitable byte-literal Raw comparison with
an actual dense rank over all `2^n` binary-symbol strings. It is valid for the
declared nonempty, even-length, two-symbol inputs up to 16,384 bytes.

For a payload of `P` bytes, both routes have the normalized complete size

```text
10-byte outer header + 256-byte model area + P + 4-byte outer CRC
= 270 + P bytes.
```

Consequently, an ERC EC archive and an RDIC archive for the same ordered
vocabulary and sequence must tie after normalization when their sequence-rank
payloads have the same width. A difference would expose an unmatched payload,
space, ordering or framing assumption. It would not establish a new rank gain.

The wrapper preserves the already established distinction:

* ERC E, C and EC already pay equal 20-byte metadata plus 4-byte CRC areas, so
  their measured payload differences are genuine differences in admitted
  state-space rank width at a matched record width.
* ERC EC versus RDIC on the frozen strong rows has the same state space and
  sequence rank. Their original 0/12/59-byte ties or wins come from model
  description cost. Padding both model descriptions to the same 256-byte area
  removes precisely that difference and must produce a tie.
* The uniform route supplies the missing physical `U` term for the exact
  byte-rounded state-space surplus. It is distinct from ERC Raw, which stores
  each original byte literally and therefore has an eight-times-larger
  payload than the binary-symbol universe requires.

## Frame and inverse

The RNC1 layout is unambiguous:

| Offset | Length | Meaning |
|---:|---:|---|
| 0 | 4 | `RNC1` magic |
| 4 | 1 | version 1 |
| 5 | 1 | codec: 1 ERC1, 2 RDIC |
| 6 | 4 | payload length, little-endian |
| 10 | 256 | codec model followed by canonical zero padding |
| 266 | P | rank or literal payload |
| 266+P | 4 | CRC-32 over every preceding RNC1 byte |

Packing first verifies the complete inner CRC. ERC1 contributes its fixed
20-byte header to the model area. RDIC Raw contributes its 15-byte header;
RDIC dictionary mode contributes the header plus the byte-rounded combinadic
dictionary rank. The remaining inner bytes are the payload. The inner CRC is
replaced by the common outer CRC rather than counted twice.

Unpacking verifies the outer envelope, CRC and exact payload length, derives
the unique codec-specific model length, rejects every nonzero model-padding
byte, concatenates that model prefix with the payload, and recomputes the inner
CRC. For every valid packed archive the reconstructed bytes before the CRC are
the original `data[..end]`, so the deterministic recomputed CRC restores the
original archive byte-for-byte.

The model length is not inferred by trimming zeros. It is derived from the
codec header, so legitimate trailing zero bytes inside a model are preserved.
The zero-padding check gives one canonical RNC1 representation for a given
codec, model and payload.

## Uniform binary-universe route

The `uniform` command first requires exactly two observed byte values and
orders them numerically. It maps each source byte to one bit, folds those bits
into one big-endian `BigUint`, and stores the explicit bit width `n`, where
`n` is the number of source bytes. Leading zero source symbols remain
recoverable because width is stored independently from the integer value.

It emits a valid ERC1 header with mode E, record width 2, equality mask 0 and
count 0. Although the ordinary ERC candidate search does not select an empty
E mask, the native decoder accepts this representation: the empty mask admits
all four two-bit records. For even `n`, there are `n/2` records and

```text
COUNT = 4^(n/2) = 2^n,
rank width = bit_length(2^n - 1) = n bits.
```

The source rank is the same binary integer as the base-4 rank obtained by
grouping the bit string into consecutive pairs. The existing native ERC1
decoder therefore provides the inverse without a new decoder rule. The rank
is left-zero-padded to `ceil(n/8)` bytes, wrapped in the same 270-byte common
area, and protected in RNC1 by the outer CRC. Unpacking reconstructs the native
inner CRC for the downstream ERC1 decoder; it is not a second independent
integrity check on the stored RNC1 frame.

Rejecting empty and odd-length sources is an explicit experimental scope
restriction. It does not affect the frozen strong rows. Any result must retain
that restriction rather than implying a general uniform route for arbitrary
input lengths or alphabets.

## RDIC model-budget proof

For RDIC dictionary mode, the model length is

```text
15 + ceil(bit_length(C(2^b,m) - 1) / 8)
```

with `2 <= b <= 12`, `1 <= m <= 256`, and `m <= 2^b`. Over this domain,
the largest combinadic dictionary occurs at `b=12`, `m=256`:

```text
bit_length(C(4096,256) - 1) = 1377 bits
dictionary bytes                    = 173
RDIC model bytes                 15 + 173 = 188
```

Thus every RDIC model accepted by its native format fits the 256-byte area,
with at least 68 padding bytes in the worst case. The implementation computes
the binomial coefficient exactly with `BigUint`; the loop is bounded by 256
iterations. The `length > MODEL` check remains a safe defensive invariant.

## Bounds and parser behavior

All input reads use `Read::take(cap+1)` and reject the extra byte. Inner input
is capped at 20,000 bytes. Outer input is capped at 20,270 bytes. The outer
payload is a `u32`, but packing can only create at most 20,000 inner bytes, so
the `usize` to `u32` conversion cannot truncate. Unpacking checks both the
declared payload against the physical frame length and the reconstructed inner
archive against the 20,000-byte cap.

All offsets are preceded by sufficient envelope-length checks. RDIC shift and
binomial parameters are validated before use. The largest allocation is
bounded by the declared archive caps, and the exact binomial work is bounded
by the fixed dictionary limit.

`metadata_len` intentionally validates only the fields needed to identify the
model/payload boundary. It does not reimplement all ERC1 or RDIC semantic
checks, such as alphabet order, source divisibility, canonical rank width and
rank range. Therefore successful RNC1 `unpack` is not by itself proof of a
valid inner archive. Qualification must perform the planned fresh native ERC1
or RDIC decode and exact source-hash check. Under that workflow this separation
is acceptable and avoids creating a second partial codec implementation.

The new uniform builder itself bounds the input before constructing the
`BigUint`. Its rank occupies at most 2,048 bytes at the 16,384-byte source cap,
well below the 20,000-byte inner cap and the outer-frame read bound.

## Required qualification assertions

The bounded harness should establish all of the following before drawing the
diagnostic conclusion:

1. Bind the RNC1 source, binary, frozen ERC1/RDIC binaries, source inputs and
   original inner archive hashes before the run.
2. For each packed archive, unpack in a fresh process and assert the recovered
   inner archive is byte-identical to the frozen original, including its
   recomputed inner CRC.
3. Decode that recovered inner archive with the corresponding fresh native
   decoder and compare the restored source SHA-256 with the frozen input.
4. For every claimed same-space pair, assert equal source length, record width,
   alphabet, vocabulary and sequence-rank bit width. RNC1 itself does not prove
   that two separately supplied archives describe the same set.
5. Before reporting a state-space surplus, assert that the selected EC set is
   exactly the intersection of the selected E and C sets. Equal selected width
   plus matching E mask/C count/EC fields proves this for four strong rows. The
   `dev-four` portfolio uses E width 2 and C/EC width 4; its relation is still
   exact because repeating the width-2 mask 1 over a width-4 record produces
   EC mask 5, but the harness must prove that expansion or omit the surplus for
   that row. Merely having all three archives is insufficient.
6. For each uniform frame, assert the stored alphabet equals the sorted source
   alphabet, the stored width is exactly `n`, the payload is
   `ceil(n/8)` bytes, an independent fold of the source bits equals the stored
   integer, and fresh native decode restores the frozen source hash.
7. Assert the RNC1 size equation `270 + payload_bytes` and equality of the two
   normalized sizes. Report original archive sizes separately.
8. Exercise outer truncation, CRC corruption, invalid codec/version, false
   payload length, nonzero model padding, oversized input and an invalid inner
   semantic field with a correctly resealed outer CRC. Remove any prior output
   before each negative case because a failed command does not delete an
   already existing output path.

## Claim boundary

The 256-byte reserve is an intentionally artificial common fee. It is useful
for controlling model cost and proving the same-space tie, but it is not an
optimal serialization and must not replace the original complete archive
sizes in a compression ranking. The normalized experiment can confirm that
ERC1's original advantage over RDIC is metadata-only. It cannot turn that
advantage into a state-space or rank-code claim.

The physical uniform frame makes the rounded surplus measurable as

```text
rank_bits(E) + rank_bits(C) - n - rank_bits(EC)
```

and, separately, with the byte-rounded payload lengths. This quantity is
meaningful only after proving that EC is the actual intersection of the
selected E and C models over the same length-`n` binary universe. The common
270-byte areas then cancel. It remains a state-space interaction statistic,
not a size win against the same-space RDIC control or a general compressor.

Subject to those harness assertions, the source is statically approved for the
bounded comparison.
