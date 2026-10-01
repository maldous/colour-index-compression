# CIX codec-method principle audit

**Audit date:** 2026-10-01.  This is a source and inventory audit, not a
benchmark result.  It maps the pinned Squash import and the local profile
inventory to mechanisms that a generic CIX selector may use.  It deliberately
does not treat a similarly named route or a wrapped library as equivalence to
the codec being reviewed.

## Evidence and terms

The source evidence is the active Rust tree, principally
`rust/cix-native/src/main.rs`, `selection.rs`, `adaptive.rs`, `rank.rs`,
`ppm.rs`, `fixedmix.rs`, `expertmix.rs`, `chain.rs`, and `external.rs`.
The codec/settings evidence is
[`squash-settings-inventory.json`](squash-settings-inventory.json), generated
from pinned Squash CSV commit `fed6ea3374155184672b71928d2b805463d156f0`.
An empty level in that CSV means that the level was not recorded; it does not
mean a library default, build flag, ISA dispatch choice, dictionary setting,
or plugin option has been recovered.

Status is specific to the *native stream selector* unless stated otherwise:

| Status | Meaning |
|---|---|
| Implemented | A bounded Rust CIX encode/decode path exposes the principle and charges the required CIX payload/frame bytes. |
| Partial | A related mechanism exists but its important parser, model, transform, parameters, or selector dimension is missing. |
| Backend-only | A complete external codec can be carried in a CIXB1 envelope, but its internals are not a native CIX route. |
| Untested | No source implementation or qualified result was found. |
| Rejected | A stated, verified experiment rejected the stated configuration only. |

## Native CIX mechanism inventory

| Area | Current state | Concrete boundary |
|---|---|---|
| Store, frames, integrity | **Implemented** | CIXG1/CIXG2 stream frames carry source length, route payload, per-block SHA-256 and a final whole-stream digest; decoding checks each frame then footer. CIXB1 carries a bounded complete payload and SHA-256. The final stream claim is valid only after footer verification. |
| Exact composition / count-rank | **Implemented** | `rank.rs` uses `BigUint`; ranks are not narrowed to machine integers. It is currently whole/substream count coding, not conditional composition by context or lane. |
| RLE | **Implemented** | `main.rs::rle` is a generic substream candidate. It is not bzip2/BSC run coding. |
| Adaptive range | **Implemented / bounded** | `adaptive.rs` provides byte arithmetic/range models; CIXG2 coder 6 adds bounded order/bucket contexts. It is not FARI, LZHAM arithmetic context coding, or ZPAQ's bit model. |
| DEFLATE | **Implemented as nested coder** | Raw DEFLATE is materialized for eligible CIX substreams through `flate2`; its LZ/Huffman parser is a library backend, not CIX's LZ route. |
| LZ representation | **Partial** | `lz_encode` uses 4-byte hash keys, at most eight recent positions/key, a 64 KiB distance limit and local score. It has no lazy/optimal/BT/HC parser, repcode, long-distance matcher, dictionary trainer, or codec wire compatibility. |
| BWT / MTF / runs | **Partial** | CIXG1 BWT+MTF zero-run route and CIXM6 legacy BWT decoder exist. Missing BSC LZP/qflc and bzip2 block sorting/RLE/Huffman choices. |
| PPM / contexts | **Partial** | Native PPM orders 0..8 are representable in CIXG2. It does not provide PPMD escape variants, sparse variable-order context pruning, or cross-block model history in the CIXG1 stream. |
| Prediction / mixing | **Partial** | Predictor, stride, fixed bit mixer, expert mixer, periodic/record and transform-chain research modules exist. Fixed-mix payload v2 includes an optional bounded recurrence-distance feature, but selector admission/ablation is absent; CIXG1 BEST does not admit all CIXM6 research modes, MATCH/ISSE/SSE, or calibrated adaptive mixing. |
| Transform/filter family | **Partial** | Stride, deltas/residuals, BWT/MTF, phrases and CIXM6 chains exist. No bounded generic transform-composition lattice, executable/text filter parity, or proven metadata-aware joint search. |
| Huffman, ANS/FSE, integer coders | **Partial / absent** | Deterministic canonical Huffman is now available as CIXG2 coder 7, with malformed-input tests; table reuse, ANS/FSE, Rice/Golomb/Elias comparison and measured per-substream coding choice are absent. |
| Dictionaries | **Partial** | Input-derived local LZ positions and phrase forms exist. There is no trained/shared dictionary selection, static text dictionary, block dictionary reuse policy, or preset dictionary envelope in native CIXG1. |
| Parallel / resource architecture | **Partial** | Candidate trials within a block have a bounded 1..4 worker queue and per-worker memory gate. Blocks are sequential and workers still materialize payloads. No mature per-worker buffer pool, block-parallel history/reset tradeoff, SIMD dispatch, PGO, or measured scaling result. |

### Deliberate non-equivalences

`external.rs` supports bounded CIXB1 envelopes for gzip, bzip2, xz, zstd and
Brotli.  Those are **backend-only**.  An external codec is eligible only when
explicitly selected by the profile/portfolio policy; its gain must be recorded
as a backend result.  It does not make the corresponding parsing, dictionary,
entropy, checksum, or framing machinery a native CIX capability.

The one completed rejection is also narrow: ZPAQ 7.15 method 5 applied to the
complete Rust CIXG1 Dickens archive made it 431 bytes larger.  It rejects that
outer wrapper on that archive, not ZPAQ models, native recurrence models, or
ZPAQ over individual CIX representations.

## Squash codec-to-principle audit

This keeps codecs with a common LZ label separate when their parser, entropy
or framing is distinctive.  “Settings” is exactly the pinned plugin/codec
levels, not reconstructed upstream defaults.

| Plugin / actual codec (settings) | Distinct implementation choices to preserve in R&D | CIX state and evidence |
|---|---|---|
| brieflz / BriefLZ (unrecorded) | Compact greedy LZ tokens and literal/match decisions. | **Partial** LZ representation only; no BriefLZ parser/token framing. |
| brotli / Brotli (1–11) | Quality-dependent LZ parser, static dictionary, context-mode literal modelling, Huffman/context maps, metablocks. | **Backend-only** CIXB1; static dictionary and literal-context machinery absent. |
| bsc / libbsc (unrecorded) | Block sorting, optional LZP prepass, MTF/RLE, qflc entropy choices; optional threads/large pages/CUDA are implementation dimensions. | **Partial** BWT/MTF/runs. No LZP, qflc, BSC block decisions or equivalent resource design. |
| bzip2 / libbz2 (1–9) | BWT block sort, RLE stages, MTF, selectors and canonical Huffman; level controls block/work factor. | **Partial** native BWT/MTF and **backend-only** CIXB1 bzip2. No native Huffman/selectors/sorter parity. |
| copy / copy (unrecorded) | Literal storage. | **Implemented** raw route/fallback. |
| crush / Crush (0–2) | Its own LZ/match and entropy stream. | **Untested**; no native or envelope implementation. |
| csc / CSC (1–5) | Large dictionary, adaptive coding, optional delta/executable/text filters. Plugin docs disagree about an unrecorded level 6. | **Untested**; transform concepts only. |
| density / Density (1,7,9) | Chameleon/Cheetah/Lion dictionary/prediction variants, double dictionaries, shifted subword lookup and form/rank entropy. | **Partial** LZ/predictor/composition primitives; no Density double dictionary or joint rank model. |
| fari / FastARI (unrecorded) | Standalone arithmetic coder with its own update/bitstream tradeoffs. | **Partial** generic adaptive range; no FARI model/throughput validation. |
| fastlz / FastLZ (1–2) | Very fast LZ parser and compact token coding. | **Partial** LZ only; no fast parser benchmark or token compatibility. |
| gipfeli / Gipfeli (unrecorded) | Snappy-family fast matcher with different table/parse decisions. | **Partial** LZ only. |
| lz4 / LZ4 raw (1–14) | Fast LZ parser, literal/match token representation. Historical CSV level range conflicts with some plugin docs. | **Partial** LZ only; no LZ4 token/wire compatibility. |
| lz4 / LZ4 frame (0–16) | Framed blocks, block/checksum policy, xxHash, independent/block-linked choice. | **Partial** CIX frame/checksum is distinct; no LZ4F format semantics. |
| lzf / liblzf (unrecorded) | Small-window LZ with compact tags. | **Partial** LZ only. |
| lzg / LZG (1–9) | LZG-specific parse/ratio variants and marker coding. | **Partial** LZ only. |
| lzham / LZHAM (0–4) | LZ parsing coupled to adaptive binary arithmetic/context coding; parse graph/deterministic/decode-speed choices. | **Partial** independent LZ and range pieces; not integrated. |
| lzjb / LZJB (unrecorded) | Fixed-window matching and tag map. | **Partial** LZ only. |
| lzma / lzma, lzma1, lzma2, xz (1–9) | BT/HC LZ parsing, rep distances, range coding, lc/lp/pb literal contexts, filter chain; wire formats are distinct. | **Backend-only** XZ CIXB1; no native LZMA model, parser, filter or dictionary sweep. |
| lzo / lzo1b,1c,1f,1x,1y,1z (recorded variants/levels) | Multiple fast parsers and token dialects; 99/999 carry distinct effort meanings. Unsafe upstream lzo1/lzo1a are excluded due decoder availability. | **Partial** LZ only; variants must not be merged. |
| ms-compress / LZNT1, XPRESS, XPRESS-Huffman (unrecorded) | Three Microsoft formats; XPRESS-Huffman is not generic DEFLATE. | **Partial** LZ/Huffman concepts only; no format parser or tables. |
| ncompress / compress (unrecorded) | Adaptive-width LZW dictionary and `.Z` framing. | **Untested**; no LZW/dictionary-reset path. |
| pithy / Pithy (0–9) | Snappy-derived but distinct match finder/token decisions. | **Partial** LZ only. |
| quicklz / QuickLZ (unrecorded) | High-speed LZ parser and format-specific flags/tokens. | **Partial** LZ only. |
| snappy / Snappy raw (unrecorded) | Fast literal/copy tags with distinct copy forms. | **Partial** LZ only. |
| snappy / Snappy framed (unrecorded) | Chunk framing and masked chunk checksum. | **Partial** generic CIX frames only; no Snappy framing. |
| wflz / wfLZ raw (1–2) | Fast matching and endian-sensitive stream choice. | **Partial** LZ only. |
| wflz / wfLZ chunked (1–2) | Chunk size, chunk framing and endianness are separate settings. | **Partial** CIX stream framing only. |
| yalz77 / YALZ77 (unrecorded) | Naive longest-match search: useful as a simple parser baseline. | **Partial** bounded-hash CIX LZ has different candidate depth/cost. |
| zlib / raw deflate,zlib,gzip (1–9) | DEFLATE parser plus Huffman; wrapper, window bits, mem-level and strategy are independent settings. | **Implemented** raw nested DEFLATE; gzip envelope only. No native zlib strategy/window sweep. |
| zlib-ng / raw deflate,zlib,gzip (1–9) | Same wire family but a separate optimized implementation and dispatch story. | **Partial** system zlib via `flate2`, not zlib-ng; no independent performance claim. |
| zpaq / ZPAQ (1–5) | Embedded ZPAQL model, ICM/CM, ISSE/MATCH, MIX/MIX2, SSE, recurrence-distance and periodic model generation. | **Partial** broad model concepts in CIXM6; no ZPAQ backend/native equivalent. Source audit is recorded in `results.md`. |
| zstd / Zstandard (unrecorded) | LZ parsing, Huffman literals, FSE/ANS sequences, block modes and dictionaries. | **Backend-only** CIXB1; native ANS/FSE/parser/dictionary machinery absent. |

## Method families, priorities, and evidence gaps

| Family | Why a codec count is insufficient | Required next artifact before promotion |
|---|---|---|
| LZ parsers | Greedy, lazy, optimal, hash-chain, binary-tree, repcode, long-distance and dictionary parsers trade parse CPU, metadata and ratio differently. CIX currently has one small bounded hash chain. | A frozen same-token-cost parser comparison on synthetic repeat/distance controls, then a paid-substream comparison; record parser time and memory. |
| Dictionaries | Static dictionaries (Brotli), external/preset dictionaries (zstd/LZMA), adaptive LZW, and input-derived phrase/LZ dictionaries have different generic-policy and stream-state costs. | Decoder-available input-derived dictionary proposal with serialized cost, reset/history rules and no corpus identity dispatch. |
| BWT family | BWT alone preserves whole-block counts. Gains require MTF/runs/local coding or conditioning; BSC LZP and bzip2 selectors are separate mechanisms. | BWT/MTF/run conditional-substream comparison and BWT-before/after valid transform experiments, charged metadata. |
| Entropy coding | Huffman, range/arithmetic, ANS/FSE and composition code the same frozen side stream differently; wrapping an entire archive cannot attribute the win. | Common frozen substreams (literals, lengths, distances, tags, counts) measured through each native coder with table/header costs. |
| Prediction/mixing | PPM, byte range models, bit contexts, recurrence/MATCH, mixer selection and calibration are separable. | Matched prediction-information ablation: byte PPM, sparse contexts, recurrence, periodic and calibrated mixing, each feeding the same coder. |
| Transforms/filters | Delta, XOR, lane/stride, BWT, phrase/base-edit, executable and text filters only matter with inverse/metadata and interaction costs. | Bounded transform beam that serializes order/parameters, tests both legal orders where relevant, and includes a raw fallback. |
| Framing/integrity | gzip/zlib/LZ4F/Snappy/zstd framing have independently meaningful checksums, block linkage and flush behavior. | CIX-only stream test matrix: partial writes, slow consumer, idle flush, corrupt/truncated frame and footer; external framing remains explicit. |
| Resource design | SIMD, native library calls, workers, queues, model reuse and allocation shape both throughput and RSS. | CPU/RSS/allocation profile with 1/2/4 leases, bounded worker buffers, history/reset penalties and release/LTO/PGO comparison. |

## Generic-policy and qualification guardrails

All candidate discovery must depend only on input bytes and declared resource
limits.  It may serialize input-derived dictionaries or relations, but may not
use file name, corpus identity, input hash, MIME/language label, fixed
source-specific dictionary, or ISA-specific input dispatch.  Runtime CPU
feature detection may select a verified equivalent acceleration path, never a
data-dependent codec policy.

No method in this document is promoted by source presence.  Promotion requires
a frozen manifest, complete archive bytes including all metadata, fresh exact
decode, encode/decode wall and CPU time, peak RSS, worker and streaming
metrics, plus replication on the authorised qualification path.  The local
four-core / 12 GB / 4 GB temporary / no-swap scheduler applies to every such
trial.  Current loss evidence, timeouts and resource exclusions remain part of
the result ledger.
