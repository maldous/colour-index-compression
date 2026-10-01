# CIX/Rust codec-principle coverage matrix

Scope: source and selector audit for the CIXG1 encoder under `rust/cix-native/`, with CIXM6 research modules called out separately. This is implementation coverage, not a claim of equivalent compression performance. All local size comparisons in this programme use the already verified Silesia Dickens member only. The upstream Squash import is an inventory/provenance source; its published sizes and CPU times are not ranked against local measurements.

## Status key

- **Implemented** — a Rust route or coder exists in the working stream encoder and its output is decodable.
- **Partial** — a related principle exists, but the reviewed codec's parsing, model, transform, framing, or selector breadth is missing.
- **Backend-only** — available as a separately framed CIXB1 complete-payload codec; the CIXG1 native route selector does not combine its internals with CIX representations.
- **Untested / absent** — no corresponding Rust implementation or verified path was found.
- **Rejected with evidence** — an explicit frozen trial was run and the hypothesis was falsified for the measured input/configuration.

## Squash codecs

The levels below are those present in the pinned Squash CSV import. `default` means the CSV level column is empty; it does not reconstruct any unrecorded build option. The per-machine imported table and its limitations are in [squash-settings-inventory.json](squash-settings-inventory.json). Plugin interface docs inspected from Squash v0.7.0 are not asserted to be the exact historical benchmark binary build.

| Squash plugin / codec and recorded level settings | Distinct method or core principle | Rust CIX coverage | Remaining gap / evidence |
|---|---|---|---|
| brieflz / brieflz (default) | Greedy LZ77-style matches and literals | **Partial** — CIXG1 LZ route | CIX uses a bounded hash-chain parser and generic substream coders, not BriefLZ parse/token choices or framing; `main.rs::lz_encode`. |
| brotli / brotli (1–11) | LZ77, static dictionary, context-dependent literals, Huffman coding | **Backend-only** — Brotli CIXB1 direct payload | Not a CIXG1 candidate inside per-block route/backend selection; CIXB1 eligibility is profile-gated (`external.rs::eligible`). No Brotli dictionary/context model in native routes. |
| bsc / bsc (default) | Large-block BWT family, MTF/run preprocessing, entropy coding and parallel block work | **Partial** — BWT + MTF + zero-run streams | CIX has a suffix-sort BWT and MTF zero-run route (`main.rs::bwt_transform`, `bwt_encode`), but no libbsc block parser, entropy stack, or tuned parallel block format. |
| bzip2 / bzip2 (1–9) | BWT, MTF, run-length coding and canonical Huffman | **Partial** — BWT/MTF and separate bzip2 CIXB1 backend | The direct bzip2 payload does not establish that the CIX BWT route has bzip2's RLE/Huffman decisions. It is not an inner CIXG1 coder. |
| copy / copy (default) | Store source bytes verbatim | **Implemented** — raw route and raw fallback | Complete raw route is always retained; route ID 0 and stream raw coder. |
| crush / crush (0–2) | CRUSH's own LZ/match and entropy decisions | **Untested / absent** | Squash interface and level range are recorded; no native CRUSH parser/coder or CIXB1 backend exists. |
| csc / csc (1–5) | CSC codec-specific parsing and entropy coding | **Untested / absent** | Plugin name resolves to the CSC library, but the CIX tree has no CSC implementation/backend. Its options are not inferred from CIX routes. |
| density / density (1, 7, 9) | Chameleon dictionary matching; Cheetah double-dictionary lookup/prediction; Lion adds multiple predictions and symbol/form-rank entropy coding | **Partial** — LZ, predictor, and composition building blocks | No swapped double-dictionary predictor, Density format, or joint symbol/form rank model. This is a high-value measured follow-up. |
| fari / fari (default) | Arithmetic coding | **Partial** — adaptive range and count/rank coders | Arithmetic/range coding is present, but no FARI implementation, probability update, bitstream or speed result. |
| fastlz / fastlz (1–2) | Low-cost LZ77 match parsing | **Partial** — CIXG1 LZ route | Different match finder, token costs, and framing; no FastLZ parity fixture. |
| gipfeli / gipfeli (default) | Snappy-family LZ parsing with optimized fast paths | **Partial** — LZ token/match concept | No Gipfeli parser, vectorized implementation, or framing. |
| lz4 / lz4 (1–14), lz4f / lz4f (0–16) | Fast LZ matching, literal/match tokens; optional LZ4 frame format | **Partial** — LZ route; separate XZ/LZ4 is not implemented | No LZ4 parser or LZ4F frame support. CIXG1 frames are CIX frames. |
| lzf / lzf (default) | Small-window LZ match/literal coding | **Partial** — LZ route | No LZF match finder or raw-LZF format. |
| lzg / lzg (1–9) | LZ parsing with codec-specific fast/ratio settings | **Partial** — LZ route | No LZG token costs, settings, or decoder. |
| lzham / lzham (0–4) | LZ parsing with adaptive binary arithmetic/context coding | **Partial** — LZ matches plus independent adaptive/range coder | No integrated LZHAM contexts, match/literal probability model, or exact LZHAM wire format. |
| lzjb / lzjb (default) | Simple fixed-window LZ matching and compact tags | **Partial** — LZ route | No LZJB parser/token format. |
| lzma / lzma, lzma1, lzma2, xz (1–9 each) | LZ77 with range coding, large dictionaries, configurable literal/context models and optional filters | **Backend-only** — liblzma XZ payload in CIXB1 | CIXB1 wraps XZ only; no native LZMA1/2 routes, filter search, LZMA dictionary parameter search, or XZ framing as CIXG1 substreams. |
| lzo / lzo1b, 1c, 1f, 1x, 1y, 1z (recorded variant levels) | Several low-latency LZ parsers and token formats | **Partial** — LZ route | No variant-specific parse/token implementation; recorded levels are in the settings JSON. |
| ms-compress / lznt1, xpress, xpress-huffman (default) | LZNT1 and XPRESS match parsing; XPRESS-Huffman literal/match coding | **Partial** — LZ plus Huffman/DEFLATE building blocks | No Microsoft-format parser, code tables, or decoder. |
| ncompress / compress (default) | Adaptive-width LZW dictionary coding | **Untested / absent** | No LZW encoder/decoder or `.Z` framing. |
| pithy / pithy (0–9) | Snappy-derived parsing with Pithy-specific match finder and token decisions | **Partial** — LZ route | No Pithy parser or byte-compatible stream. |
| quicklz / quicklz (default) | High-speed LZ77 parsing with codec-specific match/literal coding | **Partial** — LZ route | No QuickLZ token stream or parsing heuristics. |
| snappy / snappy, snappy-framed (default) | LZ match/literal tags; optional chunk framing and checksums | **Partial** — LZ route and independent CIX framing | No Snappy raw token codec or Snappy-framed stream; CIX framing is not Snappy framing. |
| wflz / wflz, wflz-chunked (1–2) | Fast LZ match parsing; optional chunked stream | **Partial** — LZ route | No wfLZ tokens or chunked format. |
| yalz77 / yalz77 (default) | Naive LZ77 longest-match search | **Partial** — LZ route | CIX's bounded hash-chain parser has different match search and costs; no YALZ77 decoder. |
| zlib / deflate, gzip, zlib (1–9) | DEFLATE LZ77 plus Huffman; gzip/zlib wrappers add checksums and headers | **Implemented / partial by representation** — CIXG1 DEFLATE coder/route; gzip not CIXG1 | Native raw DEFLATE substream is present. gzip and zlib wrapper compatibility is not the CIX format; only direct gzip CIXB1 is available. |
| zlib-ng / deflate, gzip, zlib (1–9) | Same DEFLATE coding family with a separate optimized implementation | **Partial** — zlib DEFLATE family; gzip direct wrapper | Rust links system zlib through flate2, not zlib-ng. No zlib-ng runtime dispatch or independent performance qualification. |
| zpaq / zpaq (1–5) | PAQ-style adaptive context mixing, recurrence-distance and periodic models, embedded ZPAQL model | **Untested / absent in Rust** | Direct ZPAQ 7.05/7.15 Dickens reproduction is measured in this programme, but it is not a Rust CIX backend or a native CIX model. See [results.md](results.md). |
| zstd / zstd (default) | LZ parsing, Huffman literals, FSE/ANS sequence coding, block modes and dictionaries | **Backend-only** — Zstandard CIXB1 payload | No CIXG1 inner FSE/ANS coder, Zstd parser, block-mode selection or dictionary. |

## Additional distinct methods in the pinned Squash inventory

These were present in Squash's 28-codec benchmark inventory even though not all were in the user's minimum list.

| Codec | Distinct principle | Rust coverage / gap |
|---|---|---|
| Doboz (default) | Codec-specific LZ and entropy coding in its own format | **Untested / absent**; plugin resolves to Doboz, no Rust encoder/decoder. |
| zling (0–4) | Codec-specific high-ratio LZ/entropy stream | **Untested / absent**; plugin source notes a decoder security issue; no Rust route or backend. |
| PAQ8px (other portfolio inventory) | Adaptive context mixing | **Partial model concepts only** in Rust `fixedmix`/`expertmix`; not PAQ, not a PAQ decoder, no PAQ8px Rust backend. |
| PAQ v216 (local benchmark inventory) | Large adaptive context model with SSE/mixer stages | **Partial research modules only**; no production CIXG1 native integration. Never attribute PAQ backend gains to CIX models. |

## Principle-level audit and selector blind spots

| Principle | Status | Current evidence and blind spot |
|---|---|---|
| Raw fallback and complete CIXG1 framing/checksum/footer | **Implemented** | `main.rs` emits each frame, block SHA-256 and final whole-stream SHA-256. Rust and Python independently decoded the 3,506,980-byte Dickens archive exactly. |
| Exact combinatorial rank / multinomial coding | **Implemented, route-limited** | `rank.rs` uses `BigUint`; no exact rank is narrowed to a fixed-width integer. Composition is a route/coder candidate, not a universal cost-minimal path. |
| DEFLATE coding | **Implemented, backend-limited** | `flate2`/system zlib raw DEFLATE is an inner coder. It does not provide all zlib-ng build/runtime variants. |
| Adaptive range coding and count-range | **Partial** | Byte models exist in `adaptive.rs`; count-range uses exact composition coding. No ANS/FSE coder and no verified common-frame comparison against each Squash entropy method. |
| BWT / MTF / zero runs | **Partial** | Rust BWT+MTF route exists; current transform sorts suffixes and adds metadata. No bzip2/BSC block heuristics or joint parallel transform. |
| LZ matching | **Partial** | `lz_encode` uses a bounded hash table retaining up to eight recent positions per key. It is not a cost-optimal parser and does not reproduce any listed library's tokens. |
| Prediction, periodicity, recurrence distances | **Partial** | Predictor, stride, fixed mixture, record/periodic and CIXM6 adaptive modules exist. CIXG1 BEST does not yet integrate the CIXM6 candidate families, ZPAQ recurrence search, or shared cross-block state. |
| Entropy backends | **Partial** | raw, RLE, exact composition, adaptive range, count-range and DEFLATE are present. Huffman exists only inside DEFLATE; standalone Huffman, ANS/FSE, universal integer code comparisons and substream-specific model choice remain absent. |
| Context mixing / calibration | **Partial / unqualified** | `fixedmix` and `expertmix` implementations are research routes in CIXM6. They are not a ZPAQ port; no calibrated mixer integration into CIXG1 BEST is verified. |
| Transforms and compositions | **Partial** | BWT/MTF, stride, predictor residual and phrase representations exist. Composition order/depth is narrow; no all-order two-transform tournament or complete metadata-aware region segmentation. |
| Packaging and block-size search | **Untested in the selector** | CIXG1 charges its full frame/footer size, but current BEST fixes the format and uses fixed 65,536-byte frames; it does not search CIXG1 vs CIXM6 packaging or a segmentation lattice. |
| Streaming, bounds, and backpressure | **Implemented with caveats** | One input block is held at a time, output is framed/flushed, and decode emits frame by frame. CIXG1 frames are independent; CIXM6 stateful routes are separate. Candidate workers are bounded to 1–4 and memory is divided per worker. |
| FAST/DEFAULT/BEST candidate budget | **Partial** | A deterministic profile shortlist and candidate-level work queue exist. `candidate_limit`, soft per-trial time, soft per-frame search dispatch, and per-worker memory gates are now enforced; over-budget trials and undispatched candidates are visible/countable. The search budget waits for in-flight work and is therefore soft. BEST remains broad finite search, not argmin over every legal encoding. |
| Selector overhead / exhaustive oracle | **Untested at this report point** | Rust BEST's wall/CPU cost is measured below. A dedicated verbose trial is in progress to record candidate count, summed trial time and route distribution. No small-block exhaustive-oracle miss analysis is complete. |

## Controlled reasons for rejecting ideas

One backend-composition hypothesis was rejected on Dickens: ZPAQ 7.15 method 5 over the complete Rust CIXG1 BEST archive produced 3,507,411 bytes versus the 3,506,980-byte input archive (+431 bytes), with exact nested decoding. This rejects this outer-wrap composition for this representation/input only; it does not reject direct ZPAQ or other representations. See [results.md](results.md).

The following mathematical constraint limits another experiment: applying BWT to one whole block is a permutation, so it preserves the block's global symbol counts and cannot reduce the number of sequences represented by a single whole-block multinomial rank. BWT is still useful when it creates local runs or local/conditional count structure; any claim must charge the BWT primary index, run/literal/count streams, and the coder. This is not a rejection of BWT or of the bzip2/BSC pipelines.

## Source identities

- Squash data import is pinned to `quixdb/squash-benchmark-web` commit `fed6ea3374155184672b71928d2b805463d156f0`; the CSVs are unmodified, 59,220 rows across nine machines and 28 datasets. Published times are upstream CPU seconds and are not compared to local timing.
- Squash plugin docs reviewed from `quixdb/squash` v0.7.0. The per-plugin source/version and options carried by the actual historical benchmarks are incompletely recorded by the CSV; see the settings JSON caveat.
- Frozen CIXG1 profiler/shortlist reference: Python commit `80b95427725ecf59d626b2982d50f6349abd56e1` as recorded in `selection.rs`.
- Dickens source: 10,192,446 bytes, SHA-256 `b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.
