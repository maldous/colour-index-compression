# LLT1 latent-layout prequalification proof review

Date: 2026-10-03. This is a read-only static review of the isolated bounded
experiment. It is not execution evidence, a compression result, a production
integration review, or a streaming claim.

## Reviewed identities and decision

| Artifact | SHA-256 | Static decision |
|---|---|---|
| `rust/cix-native/experiments/constraint-space/latent_layout.rs` | `8611d8ef10279025d4b878d0340358b6b4c50f7317a15e63a08d55ace19e52b8` | source is suitable for controlled local qualification |
| `segmentation/latent-evidence/FORMAT.md` | `8ad0888918f0d46d77146d0ff4d7b57106e4e7b9ad969267b4b7af8bc0cb6ca6` | wire contract agrees with the reviewed source |
| `segmentation/latent-evidence/run.py` | `db001be92ea7bba0f61452e227353be68b014f9540dfa2cc86d6df73977d3496` | suitable for the declared bounded local qualification |

No build, codec process, fixture generation, or benchmark was run for this
review. Static acceptance authorizes the already planned bounded qualification;
it does not establish that the program compiles or passes.

The first frozen build identity failed Rust ownership checking because the
global candidate constructor read vector lengths after moving both vectors into
the result. That identity produced no input or archive evidence. The reviewed
source computes the same complete byte count before those moves; this is an
ownership/lifetime build repair with no candidate-family or wire change. A
successful build and qualification still belong to the execution evidence.

The review found no remaining static inversion, complete-cost selection, wire
boundary, or decoder allocation blocker in the bound source. Earlier draft
defects in the geometry subtraction guard, tiny oracle family, uniform policy,
wire specification, and Zstd frame-window guard are resolved in these bound
identities. Runner defects which made Zstd malformed checks depend on a
selected archive kind and omitted an unknown-route case are also resolved.

## Exact wire accounting

The 18-byte LLT1 header is

`magic[4] | version:u8 | kind:u8 | source_len:u32le | crc32:u32le |
width:u8 | phase:u8 | count:u8 | prefix_len:u8`.

The next `phase` bytes are the raw prefix. The native-lane complete size is

`18 + phase + sum_j(1 op + 1 route + 4 decoded length + 4 payload length +
payload_j)`.

The global complete size is

`18 + phase + width operator bytes + 4 payload length + one Zstd frame`.

The encoder compares these complete byte counts, and `pack` rejects a mismatch
between the materialized archive and the recorded candidate cost. Kind IDs,
route IDs, little-endian integers, the reflected IEEE CRC-32 polynomial and
Zstd level are explicit in `FORMAT.md`. The decoder rejects unknown kinds,
routes and operators, noncanonical empty archives, count/geometry mismatch,
truncation and trailing bytes. The CRC covers reconstructed source bytes.

For every nonempty policy the candidate set contains an unsplit native raw
archive of exactly `source_len + 28` bytes. Empty input has one canonical
18-byte archive. Thus selection cannot be larger than this paid raw fallback
unless candidate generation or packing returns an error. This fallback is an
LLT1 archive, not a claim that the archive is smaller than the source.

## Geometry and inverse proof

Let a legal nonempty geometry have source length `n`, width `w`, phase `p`,
and suffix position

`i(p,r,j) = p + r*w + j`, with `0 <= j < w` and `i < n`.

Legality requires `1 <= w <= 8`, `p < w`, and `w <= n-p`. The explicit
`p <= n` guard precedes the subtraction in the Rust short-circuit expression,
so malformed input cannot underflow `n-p`. The last inequality also gives
every lane a first-row byte. Lane `j` has exactly

`ceil((n-(p+j))/w)` bytes,

and the sum of those lane lengths is `n-p`, including a partial final row.

Encoding leaves row zero literal. For later rows an operator is either
identity, wrapping difference or XOR against `x[i-w]`, or (for nonzero lanes)
wrapping difference or XOR against `x[i-1]`. Decoding visits rows first and
lanes second. By induction on this order, `i-w` was reconstructed in the prior
row and `i-1` was reconstructed in the current row. Addition inverts wrapping
subtraction and XOR is self-inverse. A partial row contains the contiguous
lanes from zero upward, so its horizontal predecessor also exists. The literal
prefix plus all reconstructed lanes therefore yields exactly the original
`n` bytes.

All predictors are computed from original source bytes during encoding and
already reconstructed original bytes during decoding. Candidate evaluation
order and output flushing do not define model state.

## What the oracle proves

For a fixed geometry the native cost has the form

`18 + p + sum_j(10 + payload_bytes(j, operator, route))`.

There is no state, dictionary, or payload shared between native lanes.
Consequently minimizing each lane independently over its legal operators and
five routes is the exact minimum of this defined native family. This is a
separability result, not a claim about all possible codecs.

Global Zstd is not separable because it sees the concatenation of transformed
lanes. For `n <= 12`, both `auto` and `oracle` use the same policy-admissible
geometries with width at most three. The exhaustive global family has three legal lane
zero choices `{0,1,4}` and five choices for every later lane, hence exactly
`3 * 5^(w-1)` vectors per geometry. `oracle` materializes each vector with the
same global framing and Zstd setting, retains its exact complete-byte winner,
and competes it against the exact native minimum and raw fallback. A separate
implementation can therefore check

`oracle_bytes = min(raw/native exact minimum, exhaustive global minimum)`.

`auto` instead evaluates BSS, four legalized uniform vectors, the native
winner's vector under global Zstd, the exact native candidate and raw. The
difference `auto_bytes - oracle_bytes` on the tiny bank is shortlist regret
within this frozen family. It does not measure regret against unimplemented
widths, operators, segmentations, codecs or model grammars. Width one maps the
inapplicable horizontal uniform operators to literal lane zero; those are
intentional duplicate controls, not extra legal oracle states.

The separate `mask-control` enumerates each identity/previous-column-delta
mask for every policy-admissible geometry. Lane zero is identity, so it has
exactly `2^(w-1)` masks at width `w`; for widths one through eight and all
phases this is `sum(w*2^(w-1)) = 1,793` global materializations on an input
longer than twelve bytes. It also retains BSS, raw-whole and the whole native
literal control. This is an exact finite ordinary-preprocessing control, not
the auto selector and not a new wire representation.

## Decoder and resource boundary

The outer decoder reads at most 32,768 bytes and rejects a declared source
longer than 4,096 before reconstructing it. Width is at most eight. Native lane
decoded lengths must equal the geometry-derived counts. Raw payload length is
exact; Huffman's embedded output length must equal the bounded lane length;
adaptive and legacy LZ receive the bounded expected length; legacy LZ also
receives a 4,096-byte model limit.

The reviewed manual `FrameHeader` has the same field order, widths and C layout
as the host `/usr/include/zstd.h` `ZSTD_frameHeader`: two 64-bit fields followed
by seven 32-bit fields. Before one-shot Zstd decode, the code requires exactly
one frame, a complete parsed header, declared content size equal to the bounded
expected output, and window size no greater than 4,096. The linked symbol and
header/library identity still belong in build evidence; this manual binding is
host-specific experiment machinery, not a portable ABI claim.

The experiment buffers a whole input of at most 4,096 bytes and retains its
candidate payloads. It neither accepts a pipe nor emits incrementally. It is
therefore bounded offline computation and provides no evidence for the
production streaming interface.

## Runner controls reviewed

The runner takes Zstd corruptions from a known nonempty BSS/global archive,
rather than conditionally testing the selected auto kind. It adds an explicit
native route 255 archive and a noncanonical empty archive. The handcrafted
Zstd frame declares a one-byte result with a window larger than 4,096, and the
runner requires the specific `zstd frame bounds` diagnostic. Thus a generally
invalid frame cannot masquerade as evidence for the window guard. Truncation,
trailing input, header, geometry, count, prefix, operator, Huffman declared
length and CRC cases remain present.

This is static approval of those constructions. Their expected rejection and
fresh-output absence remain facts for the subsequent run to establish.

## Later hardening, not a source-correctness blocker

The trace now distinguishes retained complete candidates from the internal
oracle vector count, publishes operator and route vectors for retained
candidates, and explicitly reports `transform_cache: "none"`. It does not yet
count every route materialization.

Several candidates can encode identical transformed bytes: width-one
horizontal uniform aliases are literal, a native-selected vector can equal a
uniform or BSS vector, and data can make distinct reversible operators coincide.
This repeats deterministic backend work but does not change the candidate set
or selected complete bytes. Before throughput claims, add a bounded cache keyed
by exact transformed bytes plus backend and settings. A digest alone is not an
identity; confirm the bytes on a hash hit. Keep logical candidate counts,
unique materializations and cache hits separate, charge cache peak memory, and
preserve candidate-specific metadata costs.

The current implementation is deliberately serial. Parallel candidate
materialization is safe only with deterministic reduction by the existing
complete-cost tie key, a shared aggregate memory cap, and retained accounting
for all discovery work. These are performance follow-ons, not grounds to alter
the frozen qualification family.

## Required independent checks

The bounded qualification should retain all of the following:

1. Fresh archive-only decode and source hash equality for every produced cell.
2. An independently implemented raw-lane encoder over every legal small
   geometry and operator vector, including partial rows.
3. Independent enumeration of `3 * 5^(w-1)` global vectors and physical Zstd
   frame sizes, compared with the native oracle result.
4. Empty, the frozen small lengths, shifted phases and partial final rows. The
   current frozen tiny bank covers lengths one through eight; do not describe
   allowed oracle lengths nine through twelve as independently exercised.
5. Every malformed header/geometry/count/operator/route/length/truncation/
   trailing/CRC case, plus the separately proved Zstd window and one-frame
   guards.
6. Complete archive accounting from parsed fields, including raw prefix,
   operator/route metadata, substream frames and payloads.
7. External resource measurement and exact build, source, linked-library,
   input and command identities.

Passing these checks would qualify only the frozen small experimental family.
Real-input screening, general selection value and production integration remain
separate gates.
