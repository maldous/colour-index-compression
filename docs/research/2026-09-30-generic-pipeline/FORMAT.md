# CIXG1 generic pipeline format and implementation

The new runnable interface is `python -m cix.pipeline`. The existing CIX
research stream and all historical production/PAQ portfolios remain intact.

## Archive-only reconstruction

All integers in fixed descriptors are little-endian. Archive header `<5sII>`
contains magic `CIXG1`, maximum block size, and decoded-history capacity (0 or
65,536 bytes). Each block frame `<BII32s>` contains route ID, original length,
payload length, and SHA-256 of the original block. Route 255 terminates the
archive with zero lengths and SHA-256 of the complete original stream. Reject
trailing data, unknown identifiers, truncation, invalid lengths or checksums.
Decoding never calls the selector or reads the source input.

Normal blocks are at most 65,536 bytes. Forced experimental routes may expand
but are limited to `8 * original_length + 4096` payload bytes on decode. The
normal selector always retains raw and accepts only shorter physical payloads.
Its maximum expansion is therefore exactly bounded by

`13 + 41 * (1 + ceil(original_bytes / block_bytes))` bytes.

The empty stream occupies 54 bytes. Counts and original lengths cap decoded
output per block. Independent blocks reset all local models; optional retained
history is used only by LZ and is reconstructed from preceding decoded blocks.
Independent blocks allow external parallel scheduling; this first version's
CLI encodes one block at a time. It does not silently claim parallel speed.

## Routes

| ID | Representation and reconstruction information |
|---:|---|
| 0 | Raw bytes, exact original length |
| 1 | `(byte, positive varint count)` runs |
| 2 | Original bytes in local CIX composition/index tiles |
| 3 | LZ tag, literal, match-length-minus-four and distance substreams; bounded 65,536-byte window, chain eight |
| 4 | Causal XOR residuals from a reproducible three-expert predictor: previous byte, lag four, previous two-byte context's last successor |
| 5 | Four-byte BWT primary index; MTF tags, nonzero ranks and zero-run lengths |
| 6 | One-byte generic transform ID and shared byte-plane streams; six fixed byte/word delta/XOR probes choose one representation |
| 7 | At most 32 input-derived two-byte phrases, transmitted verbatim; tags, literals and dictionary indices |
| 8 | Existing generic PPM, pinned order three, escape-one, no secondary escape or update-exclusion search |
| 9 | Existing generic fixed-point mixer; its three learning-rate trials are included in the route's search budget |
| 10 | Original bytes to zlib raw DEFLATE with fixed level six |

The pair dictionary is intentionally a small phrase baseline, not a general
grammar compressor. LZ supplies the richer history-derived phrase references.
No semantic parser, executable/image/XML recognition, language dictionary,
filename, source hash or corpus selector is reachable from this pipeline.
All word widths/endian transforms apply to arbitrary bytes and preserve tails.

BWT uses a bounded prefix-doubling suffix sort rather than the legacy Python
fallback's quadratic suffix-string allocation. BWT alone preserves counts;
the tested route depends on MTF, zero-run separation and local stream coding.
No entropy-coded output is recursively compressed.

## Substreams and cost attribution

A stream group starts with its stream count (one byte), then each descriptor
`<BII>` specifies coder ID, decoded length and physical payload length. Group
counts are limited to eight; aggregate decoded stream bytes are limited by
the route's bounded representation. Coder IDs are raw (0), runs (1), local
CIX exact ranks (2), raw DEFLATE (3), order-zero adaptive range coding (4), or
identical-count range ordering (5).

CIX uses fixed tiles of at most 1,024 symbols. Each tile transmits its active
alphabet, composition, sequence mode, payload and boundary length. Exact rank
integers are bounded to 8,192 bits, not enlarged with file size. Giant
factorials are not built. The paid composition and rank routines are the
unchanged existing CIX implementation. `count-range` uses the same paid
alphabet/count information with arithmetic remaining-count ordering; its
experimental construction also computes the incumbent rank, so its encoding
time is **not** a fair range-code speed comparison.

The hybrid stream selector compares complete materialized raw, run, CIX and
DEFLATE payloads. A count-entropy gate avoids CIX trials unlikely to repay
their count tables. It cannot disable the input's LZ, BWT, predictor or stride
opportunities. Every discarded stream and route trial is included in encoder
time. Route receipts account separately for structure/dictionaries, stream
descriptors, paid count tables, coded payload and framing; their sum is
asserted against physical size. Counts are transmitted, never hidden state.

## Bounded production selector

| Effort | Block bytes | Profile sample cap | Route trials | Search seconds/block | Seconds/trial | Child address-space MiB |
|---|---:|---:|---:|---:|---:|---:|
| fast | 32,768 | 2,048 | 4 | 0.75 | 0.30 | 256 |
| balanced | 32,768 | 4,096 | 7 | 3.0 | 1.0 | 384 |
| maximum | 65,536 | 8,192 | 10 | 12.0 | 4.0 | 512 |

These first budgets follow the preserved level-one baseline's observed
0.29–1.19 seconds to encode 4 KiB calibration cases. They are numeric ceilings
for initial research, not throughput promises. Workers receive hard deadlines
and address-space limits, and are terminated and joined on timeout. Search
time includes profiling, discarded trials and worker launch. Process shutdown
and file I/O add time outside the search ceiling. Trials proceed one at a
time per encoder, never multiplying the table's memory by the candidate count.

Four spread probes count symbols, adjacent runs, repeated four-byte keys,
lag residual entropy, last-successor predictability and regional entropy
changes. Those generic features determine a fixed ordered shortlist. All
eligible candidates compete by complete payload size; no estimated size wins.
The selected route is paid once per fixed block, avoiding tiny region
switching. Receipt records retain at most 32 blocks in memory; complete
block-level traces stream to JSONL. Offline broad trials are a separately
declared diagnostic using the same ceilings, not an oracle hidden inside
production. The heuristic is frozen before holdouts; it has not been trained
on their results.

## Backend provenance and distribution limitations

CIX composition, LZ parsing, transforms, generic PPM and fixed-point mixture
reuse the repository's existing Python code. The standard-library DEFLATE
backend is the installed zlib, with its zlib licence; Python uses PSF licensing.
Reference gzip/bzip2/XZ use unchanged Python bindings to installed codecs;
Brotli uses the existing installed module. Exact runtime versions and commands
are recorded in the evidence. There is no external PAQ binary in the generic
pipeline: historical PAQ versions contain specialized models and are retained
as historical evidence rather than silently imported into the generic policy.

No new third-party codec was acquired during this phase. ANS/FSE and Huffman
are not implemented in this first candidate set. No top-level distribution
licence was found for the inherited research code; a release needs a separate
licence review. This implementation is private and is not a Hutter submission.

## Commands

```sh
python3 -m cix.pipeline encode input.bin output.cix --effort balanced --receipt encode.json
python3 -m cix.pipeline decode output.cix restored.bin --receipt decode.json
sha256sum input.bin restored.bin

# Isolated contribution experiments, not normal production settings:
python3 -m cix.pipeline encode input.bin lz.cix --effort maximum --force lz --backend cix
python3 -m cix.pipeline encode input.bin range.cix --effort maximum --force lz --backend count-range
python3 -m cix.pipeline encode input.bin deflate.cix --effort maximum --force lz --backend deflate
```
