# Mixed-content audit — read-only

## Finding

Whole-file portfolio selection does **not** satisfy the required mixed-input
case. It selects one completed archive for an entire named input. The restored
native code does contain one reusable mixed-region mechanism: `CIXZ1` writes
successive fixed-size regions and competes raw, persistent-zstd and nested
complete CIXG1/CIXG2 for each region. It has a decoder, transition/reset
framing, a whole-stream SHA-256, and a test containing text–binary–text data.
It is currently an admitted non-seekable BEST path after a bounded probe, not
a general content-derived specialised-region system.

## Reusable functionality

| Mechanism | What it actually does | Reusable for mixed content? |
| --- | --- | --- |
| CIXG1/CIXG2 normal encoder | Fixed blocks up to 64 KiB; native route competition inside each block; selection feature extraction includes regional entropy | Partly. It can choose native generic routes per block but does not encode a specialised-model identity or content-derived boundary map. |
| CIXZ1 streaming backend | Fixed `block` regions; per-region raw/persistent-zstd/nested-CIXG competition; explicit zstd reset frames when changing representation | Yes as a container/region-frame precedent. Its candidate set is too narrow for specialised numerical/image/database models. |
| CIXM6 | Per-block internal candidate competition and persistent/history support | Partly. It has local mode frames, but no general region directory or specialised adapter contract. |
| Python generic pipeline | `encode_file` reads `block_bytes` chunks, selects a route per chunk and writes self-describing `FRAME` route IDs and hashes; `decode_file` replays those frames | Yes as a generic local block-framing precedent, like CIXG. Its current route catalog does not itself provide automatic specialised mixed-region admission. |
| Historical transforms | Numeric, molecular, record/periodic, lane and segmentation experiments | Reusable transform ideas only where decoder/metadata are complete. Most closed work is not an admitted automatic mixed-region runtime route. |
| Whole-file `portfolio_auto` | Complete CIXG2 and CIXB1 archive competition | No. It chooses one archive and cannot express text + numerical region + text. |

## Concrete gaps

1. No current automatic content-derived boundary finder is serialized in a
   production archive. CIXZ1 boundaries are fixed blocks, not a paid detected
   segmentation.
2. No native region-candidate interface admits specialised transforms with
   explicit encoder/decoder memory, time and metadata cost.
3. CIXZ1 cannot currently nest CIXB1 or a specialised complete archive; it
   accepts raw, zstd and CIXG1/CIXG2 nested frames. Allowing a new family
   requires exact nested decoder dispatch and resource accounting.
4. There is no complete-archive comparison between a mixed-region result and
   whole-file CIXG2/CIXB1 candidates under one effort budget.
5. Historical segmentation gains cannot be reused as a format decision: their
   model description, boundary bytes, transition resets and decoder path must
   all be paid and independently restored.

## Required design after approval

Use a self-delimiting region frame carrying: uncompressed length, candidate or
transform ID, paid parameter/boundary description length, payload length and
integrity material. Boundaries may inspect the supplied input during offline
compression, but must be input-derived rather than filename/corpus/hash based.
The decoder must replay the boundary rule from the decoded bytes or receive its
complete paid boundary map. At each
region, compete admitted generic and specialised candidates on complete region
frame cost, including reset/transition cost. Then compare the completed mixed
archive against every admitted whole-file candidate before selection.

The text–large-numeric–text qualification fixture must prove that generic and
specialised candidates are considered for each eligible region, selections and
their paid costs are recorded, and one complete mixed archive restores exactly.
It must not force a specialist win: a whole-file candidate may legitimately be
smaller after all framing and transition costs. It must not use a filename,
corpus identity, hash lookup or saved stream.

## Magic compatibility

There are two incompatible naming eras. Legacy Python/binary frames use byte
magics such as `CIXB\x1d` and `CIXG\x01`; restored native 0.1 uses ASCII
`CIXB1` and `CIXG1`/`CIXG2` (plus `CIXM6`, `CIXF1`, `CIXZ1`). They must never
be conflated by a prefix-only dispatcher. Preserving a complete direct legacy
frame may avoid a new envelope only if the native decoder gains an exact magic
branch, length/integrity validation, bounded resource admission and strict
trailing-byte rejection. Otherwise it needs a versioned native envelope with
the same properties; wrapping arbitrary legacy payload bytes is unsafe.

No code, test, encode or benchmark was performed by this audit.
