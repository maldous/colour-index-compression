# N6 — universal integer substream closure

**Status:** prepared, not compiled, tested, or measured.  Root dispatches only
after a resource lease.  This is an isolated experiment; it changes neither
the native format nor the generic selector.

## Question and control

Can a bounded universal-integer description reduce the *complete* archive size
of a tagged structural integer sequence against the existing unsigned LEB128
description?

Each fixture is encoded once with these fixed coders:

| Control/candidate | Frozen configuration |
| --- | --- |
| Current control and exact fallback | unsigned LEB128 (`varint`) |
| Candidate | Elias gamma with a one-bit `u64::MAX` escape |
| Candidate | Elias delta with a one-bit `u64::MAX` escape |
| Candidates | Rice `k=0`, `2`, `4`, and `8`; paid raw-`u64` escape after the 65-bit regular-code boundary |

There are 21 planned rows: three fixtures times seven coders.  Each row is one
trial; no averages or pre-encode size pruning are permitted.  A successful
candidate must be smaller than its same-fixture varint control and satisfy the
fresh archive-only restoration receipt.  Results remain unqualified if the
resource, exact-restore, or input-hash receipts are missing.

## Input scope and source audit

The source audit found CIXG1 route-3 parsing in
[`fast_lz.rs`](../../../../../rust/cix-native/src/fast_lz.rs): it emits
tags, literals, lengths, and distances, with length/distance values already
serialized as LEB128.  That parser is a format-scoped native implementation;
there is no frozen public integer-sequence extraction interface that this
stand-alone experiment can reuse without changing production source or adding
a new adapter.

Therefore the three frozen `ISIN1` inputs are **synthetic structural controls,
not measurements of real LZ parses**.  They carry sequence tags cycling in
this order: length, distance, count, exception position.  Tags make the schema
and ordering explicit; their values deliberately include zero and `u64::MAX`
to exercise the decoder boundaries.

| Fixture | Sequence and tail | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| strong | 256 values; an eight-value palette (`0,1,4,16,64,255,MAX,8`) repeated 32 times; tail `tail` | 846 | `927cfb2e0f615934fc4493107bbc0368956be509b8675557a0028d3b3851626e` |
| weak | 256 values; six frequent small values with every ninth value from the deterministic xorshift stream; tail `t` | 590 | `8f9473fa95a7d43429675cc53378556000444028344438935114b1b7341fdcc3` |
| absent | 256 xorshift values masked to 16 bits; tail `t` | 972 | `b578babbd2cafee8655d68eca4076a7e67672fd9c8084437debc763829b4f8a8` |

The fixture generator is part of the harness and its source hash is frozen in
[`freeze.json`](freeze.json).  The hashes above were calculated directly from
that deterministic `ISIN1` generator specification; dispatch must rehash the
materialized files before encoding.

## Archive and exactness contract

`ISC1` archives contain every charged byte: magic/version, coder id, Rice
parameter, schema, sequence count, tag length, tail length, exact integer bit
length, integer-payload length, tags, integer payload, tail, and CRC-32 over
the complete instruction-and-payload region.  Padding is included in the
stored integer payload; the declared bit length rejects trailing significant
bits.  The original `ISIN1` source itself contains its schema, tagged sequence,
count, tail length, and tail bytes.

`encode` invokes a new process of the same harness with only archive and output
paths.  That decoder has no encoder input, model, search, or sidecar.  It must
rebuild bytes exactly and the parent compares them byte-for-byte with the
source.  The root receipt records archive SHA-256, restored SHA-256, source
SHA-256, byte equality, coder, fixture, and complete archive bytes.

The reader obtains inputs only after regular-file metadata and a `Read::take`
cap (`cap + 1`) agree; the second cap catches a file that grows after metadata.
Decoder rejection checks cover unknown coder/schema, invalid Rice `k`, host
width conversion, count/tail/archive/bit caps, checked length arithmetic, CRC,
unknown tags, noncanonical or overflowing LEB128, truncated gamma/delta/Rice
bits, excessive Rice unary quotient, invalid declared bit length, nonzero
bit-payload padding, and coder-specific unused payload.  Gamma and delta
reserve `0` as a `u64::MAX` escape; their regular branch stores `value + 1`,
so zero is represented without an ambiguous code.  For Rice parameter `k`,
the regular code costs `q + k + 2` bits: one regular flag, `q` unary zeroes,
one unary terminator, and `k` low bits.  The raw escape is `0` plus 64 bits,
or 65 bits.  The encoder uses raw only when `q > 63 - k`; the equal-cost case
stays regular.  The decoder rejects raw values at or below that threshold and
regular unary values above it, making this exact finite wire language
canonical.  Every `u64` therefore has a Rice representation of at most 65
bits, including `u64::MAX`.  LEB128 directly covers zero and `u64::MAX`.

## Bounded dispatch plan

Root schedules the 21 rows under the existing one-core bounded schedule: one
logical worker pinned to its assigned physical core, no swap, 256 MiB aggregate
RAM reservation, 2 MiB aggregate temporary reservation, and 30 seconds wall
per row.  The harness input, archive, restored output, stdout/stderr, and
receipt are placed in a distinct `fixture/coder` directory.  The row deadline
is enforced by the root runner, not claimed as an unimplemented harness limit.

Required row receipt:

1. freeze/source/fixture hashes and command line;
2. scheduler assignment, wall time, CPU time, peak RSS, and temp high-water;
3. input and full archive byte counts, plus archive SHA-256;
4. separate fresh-child exit status and source/restored SHA-256 equality; and
5. an explicit `complete`, `failed`, or `budget-limited` result.

No broad parameter search, external acquisition, full corpus run, build, test,
or benchmark is authorized by this plan.
