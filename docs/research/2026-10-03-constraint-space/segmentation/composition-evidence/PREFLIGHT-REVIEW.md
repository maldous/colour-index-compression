# SMC1 composition preflight review

Date: 2026-10-03. This is a static, read-only review. No wrapper build,
transform, codec process, input extraction, archive, or benchmark was run.

## Reviewed identities and decision

| Artifact | SHA-256 | Decision |
|---|---|---|
| `rust/cix-native/experiments/constraint-space/representation_m6_wrapper.rs` | `2e785367f9dbea9fb94f6b6aeea4885da4cdac89f9008a222302cecd5aef72c0` | suitable for a bounded controlled build and qualification |
| `segmentation/composition-evidence/FORMAT.md` | `d7d2dfc4bf1f4368182d9dd90b4df5d7064f9dff7e54408dea0ee81202188fbf` | agrees with the reviewed source |
| frozen CIX d3a2 executable | `f9b8262086be9704d8d9425ccbf5cbf5274096ae88334ea1501aa4773034fac3` | required M6 child identity |
| frozen d3a2 `main.rs` | `b26c576008cd348358a0aa40e3360de2bd0992d1e8a042e1e71317861d3e4336` | reviewed M6 framing and decoder authority |
| frozen d3a2 `libcix_native.rlib` | `3db8b676ec03a2d0a5358f87d72af13ad6161a46b32467f4ea0dd34b8d5c475c` | required native proxy dependency |

No static correctness, complete-cost, inverse, or decoder allocation blocker
remains in the bound source. This is permission to perform the already planned
local build and finite qualification, not evidence that either passes. The
runner/freeze must enforce the child and library identities above; an absolute
path check inside the wrapper is not an executable identity check.

Earlier draft defects are resolved: the outer fixed cost is 25 bytes, CIXM6 is
fully preflighted before child execution, child output is capped before
retention, Zstd has an exact one-frame bounded decoder, backend bodies are bound
to the paid transform, and malformed varint high bits cannot be truncated into
a valid value.

## Wire and complete-cost proof

The fixed fields occupy 25 bytes, excluding the operator vector and payload:

`magic4 + version1 + backend1 + source_len4 + transformed_len4 + crc4 +
width1 + phase1 + operator_count1 + payload_len4 = 25`.

All multibyte fields are little endian. A complete SMC1 archive is therefore

`25 + width + complete_backend_body_bytes`.

`pack` calculates that value with checked additions, rejects values above
32,768, materializes every field, and requires the materialized length to equal
the calculated value. The raw prefix is already inside the transformed backend
body and is not charged twice. Backend IDs are 0 CIXM6, 1 one-frame Zstd and 2
the native per-lane proxy. The outer CRC is reflected IEEE CRC-32 of restored
source bytes.

For M6, the body cost includes `CIXM6`, history varint, every frame's mode and
length varints, complete selected payload, terminal mode, whole length and
transformed CRC. Zstd cost is the complete frame. Native cost includes the raw
prefix and every route, decoded length, payload length and payload.

## Transform inverse

For source position `i=p+r*w+j`, the transform copies `source[..p]` and then
concatenates lanes in increasing `j`. Each lane's first row is literal. Later
bytes are identity, wrapping difference or XOR against original `x[i-w]`; a
nonzero lane can also use original `x[i-1]`. SMC1 v1 deliberately requires
lane zero to use identity, a narrower grammar than LLT1.

The inverse consumes the prefix and lane streams in increasing lane order. A
vertical predecessor is in the previous row and a horizontal predecessor is
in an already reconstructed prior lane. Wrapping addition inverts subtraction
and XOR is self-inverse. `w<=n-p` gives every lane a first byte and makes each
lane count safe. The final cursor must consume exactly `n` transformed bytes,
including a partial last row. This establishes exact inversion for all admitted
nonempty geometries.

## CIXM6 preflight and child boundary

Before starting a child, `m6ok` requires:

1. exact `CIXM6` magic and a canonical history varint in `1..=1 MiB`;
2. canonical overflow-checked frame varints, including an explicit final-word
   high-bit bound on a 64-bit host;
3. a recognized data mode in `0..=20`;
4. nonzero frame source length, cumulative source no greater than `n`, and
   final cumulative source exactly `n`;
5. payload length within the body, no larger than 32,768, and no larger than
   `8*frame_source_len+4096`;
6. terminal mode 255, footer length equal to `n`, four footer CRC bytes, and
   immediate EOF, which excludes CIXF1 tails and concatenated streams.

At pack time the parsed footer CRC must equal the CRC of the paid transformed
source. This cheaply binds a generated M6 body to that transform. It does not
substitute for decoding the selected payload: qualification must still invoke a
fresh frozen child and compare the exact restored source hash.

The preflight proves that a child can emit at most the outer `n<=4096` declared
bytes before footer validation. `cixdec` then reads no more than `n+1` bytes; an
overrun kills and waits for the child. Its input writer runs separately, so the
two pipes cannot form a write/write deadlock. A stdout read error kills, waits
and joins before returning. Child status and exact output length are mandatory.

The only allowed decoder child for evidence is the absolute frozen d3a2 CIX
path with SHA-256 above, invoked with exactly:

`-d --threads 1 --memory 1536MiB -c`.

The wrapper verifies that a supplied child path is absolute. The runner must
also require the exact path and rehash it immediately before each evidence
phase. The matching body encoder command is fixed as:

`--best --format cixm6 --threads 1 --memory 1536MiB -c -`.

The reviewed d3a2 M6 BEST encoder traverses its effort and memory-gated
candidate set deterministically; it has no M6 wall-clock search deadline. These
arguments constrain the container to CIXM6 and do not invoke automatic package
or external-codec selection.

## Zstd and native proxy boundaries

Zstd admission uses the host `ZSTD_frameHeader` ABI: two 64-bit fields followed
by seven 32-bit fields, matching the reviewed system header. It requires one
frame consuming the entire payload, a declared content size exactly `n`, and a
window no larger than 4,096 before allocating the `n`-byte output. Pack decodes
the frame and requires exact equality with the paid transformed bytes. Decode
repeats the checks before inversion.

The native proxy is a distinct control, not Zstd and not CIXM6. Each lane
materializes raw, canonical Huffman, adaptive order-0 and legacy LZ effort-1
payloads, and selects the smallest payload with route ID as the deterministic
tie break. Lane record overhead is constant, so the per-lane choice is
separable. Decode derives each expected lane length from outer geometry,
checks the stored length and route, validates Huffman's embedded output length,
and gives adaptive/LZ bounded expected output and model parameters. Native pack
decodes its body and requires exact equality with the original source before
writing the archive.

The manual Zstd ABI and native Rust library remain host/build-specific. Their
header, shared-library and rlib identities belong in the freeze and evidence.

## Frozen finite comparison

The original-input CIXM6 baseline is the bare complete CIXM6 body. It must not
be wrapped as SMC1 identity merely to impose a descriptor tax. This is a fair
asymmetry: the original needs no transform description, while every reversible
layout does. Report backend-body gain and net gain after `25+width` separately.
Apply the same rule to any original Zstd or native control.

The finite transform family is fixed before reading the new slice:

- the eight width-4, phase-0 vectors `[0,a,b,c]` with each of `a,b,c` in
  `{0,2}`;
- the old selected vector `E=[0,2,1,0]` at width 4, phase 0;
- neighbours `drop2=[0,0,1,0]`, `rowXOR4=[0,2,4,0]`, and
  `lastcol2=[0,2,1,2]` at width 4, phase 0;
- `E` at width 4, phase 1; and
- `[0,2,1]` at width 3, phase 0.

No width, phase, vector, backend setting or CIX effort may be added after the
qualification bytes are inspected. If two candidates produce identical
transformed bytes, reuse a backend body only after exact byte comparison and
include backend/settings in the key. Still materialize and charge each logical
candidate's descriptor. Record logical candidates, unique backend trials and
cache hits separately.

## Qualification obligations

The frozen runner must establish all of the following before a size claim:

1. build success against the frozen d3a2 native library, plus source, compiler,
   rlib, libzstd and executable identities;
2. independent transform/inverse checks for every vector, shifted phase and a
   partial final row;
3. fresh wrapper decode and exact original SHA-256 equality for every archive;
4. parsed complete-byte accounting for every outer field and complete backend
   body;
5. malformed magic/version/backend, zero/oversized/mismatched lengths,
   geometry/count/operator, payload truncation/trailing, outer CRC, canonical
   varint overflow, unknown M6 mode, cumulative/output/payload/footer bounds,
   child failure/overrun, and Zstd concatenation/content/window cases;
6. exact command, input range/hash, CPU, memory and temporary-space records;
7. bare original M6 and same-backend transformed controls on the identical
   frozen 4 KiB input; and
8. separate transformation, backend and paid-wrapper effects, with every loss
   retained.

The wrapper writes complete files only after constructing an in-memory archive,
but it does not use atomic replacement and is not a production CLI. It buffers
the entire bounded 4 KiB input and provides no streaming evidence.

The qualification slice may test the frozen hypothesis. Conditional replication
follows only its predeclared trigger. A win would demonstrate a paid transform
plus incumbent-backend gain on those slices. It would not establish a native
CIX model gain, production selection, bounded streaming, or general superiority.
