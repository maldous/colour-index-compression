# CIX/Rust codec-principle coverage matrix

Scope: source and selector audit for the CIXG1 encoder under `rust/cix-native/`, with CIXM6 research modules called out separately. This is implementation coverage, not a claim of equivalent compression performance. The initial comparisons used the already verified Silesia Dickens member. The 2026-10-02 MR follow-up uses the existing verified MR input after the preserved Canterbury/Calgary/Artificial gate; see the dated update below. The upstream Squash import is an inventory/provenance source; its published sizes and CPU times are not ranked against local measurements.

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
| brotli / brotli (1–11) | LZ77, static dictionary, context-dependent literals, Huffman coding; quality 1–11 and generic/text/font modes | **Backend-only** — Brotli CIXB1 direct payload | Not a CIXG1 candidate inside per-block route/backend selection; CIXB1 eligibility is profile-gated (`external.rs::eligible`). No Brotli dictionary/context model in native routes. See [Brotli plugin options](https://quixdb.github.io/squash/api/c/md_plugins_brotli_brotli.html). |
| bsc / bsc (default) | Large-block BWT family, optional LZP prepass, MTF/run preprocessing, qflc static/adaptive entropy coding, optional threads/large pages/CUDA | **Partial** — BWT + MTF + zero-run streams | CIX has a suffix-sort BWT and MTF zero-run route (`main.rs::bwt_transform`, `bwt_encode`), but no libbsc LZP, qflc coder, block parser, or tuned parallel block format. See [bsc plugin options](https://quixdb.github.io/squash/api/c/md_plugins_bsc_bsc.html). |
| bzip2 / bzip2 (1–9) | BWT, MTF, run-length coding and canonical Huffman; level selects 100–900 KiB blocks and work-factor changes fallback sorting | **Partial** — BWT/MTF and separate bzip2 CIXB1 backend | The direct bzip2 payload does not establish that the CIX BWT route has bzip2's RLE/Huffman decisions. It is not an inner CIXG1 coder. The upstream plugin also cannot provide reliable flush semantics. See [bzip2 plugin options](https://quixdb.github.io/squash/api/c/md_plugins_bzip2_bzip2.html). |
| copy / copy (default) | Store source bytes verbatim | **Implemented** — raw route and raw fallback | Complete raw route is always retained; route ID 0 and stream raw coder. |
| crush / crush (0–2) | CRUSH's own LZ/match and entropy decisions | **Untested / absent** | Squash interface and level range are recorded; no native CRUSH parser/coder or CIXB1 backend exists. |
| csc / csc (1–5) | CSC adaptive coding with 32 KiB–1 GiB dictionary and optional delta, executable, and text filters | **Untested / absent** | Plugin name resolves to the CSC library, but the CIX tree has no CSC implementation/backend. The v0.7.0 docs conflict: option range says 1–5 while prose says 6 is highest; CSV records 1–5. See [CSC plugin options](https://quixdb.github.io/squash/api/c/md_plugins_csc_csc.html). |
| density / density (1, 7, 9) | Chameleon dictionary matching; Cheetah swapped double-dictionary lookup/prediction; Lion adds multiple predictions, shifting subword lookup, and symbol/form-rank entropy coding | **Partial** — LZ, predictor, and composition building blocks | No swapped double-dictionary predictor, Density format, or joint symbol/form rank model. Optional SpookyHash checksum is not represented. This is a high-value measured follow-up. See [DENSITY plugin options](https://quixdb.github.io/squash/api/c/md_plugins_density_density.html). |
| fari / fari (default) | FastARI standalone arithmetic coding with its own probability/update and bitstream implementation | **Partial** — adaptive range and count/rank coders | Arithmetic/range coding is present, but no FARI implementation, probability update, bitstream or speed result. See [FARI plugin](https://quixdb.github.io/squash/api/c/md_plugins_fari_fari.html). |
| fastlz / fastlz (1–2) | Low-cost LZ77 match parsing | **Partial** — CIXG1 LZ route | Different match finder, token costs, and framing; no FastLZ parity fixture. |
| gipfeli / gipfeli (default) | Snappy-family LZ parsing with optimized fast paths | **Partial** — LZ token/match concept | No Gipfeli parser, vectorized implementation, or framing. |
| lz4 / lz4 (CSV 1–14), lz4f / lz4f (0–16) | Fast LZ matching, literal/match tokens; optional LZ4 frame format with 64 KiB–4 MiB blocks and xxHash checksum | **Partial** — LZ route; no LZ4 wire format | No LZ4 parser or LZ4F frame support. v0.7.0 docs describe raw lz4 levels 7–14, while the CSV contains 1–14; preserve this historical settings discrepancy. CIXG1 frames are CIX frames. See [LZ4 plugin options](https://quixdb.github.io/squash/api/c/md_plugins_lz4_lz4.html). |
| lzf / lzf (default) | Small-window LZ match/literal coding | **Partial** — LZ route | No LZF match finder or raw-LZF format. |
| lzg / lzg (1–9) | LZ parsing with codec-specific fast/ratio settings | **Partial** — LZ route | No LZG token costs, settings, or decoder. |
| lzham / lzham (0–4) | LZ parsing with adaptive binary arithmetic/context coding; optional extreme parse graph, deterministic parse, and decompression-rate-for-ratio modes | **Partial** — LZ matches plus independent adaptive/range coder | No integrated LZHAM contexts, match/literal probability model, or exact LZHAM wire format. See [LZHAM plugin options](https://quixdb.github.io/squash/api/c/md_plugins_lzham_lzham.html). |
| lzjb / lzjb (default) | Simple fixed-window LZ matching and compact tags | **Partial** — LZ route | No LZJB parser/token format. |
| lzma / lzma, lzma1, lzma2, xz (1–9 each) | LZ77 with range coding, large dictionaries, configurable lc/lp/pb literal contexts, and optional filters; xz/lzma/lzma1/lzma2 are distinct wire formats | **Backend-only** — liblzma XZ payload in CIXB1 | CIXB1 wraps XZ only; no native LZMA1/2 routes, filter search, dictionary parameter search, or XZ framing as CIXG1 substreams. See [LZMA plugin formats/options](https://quixdb.github.io/squash/api/c/md_plugins_lzma_lzma.html). |
| lzo / lzo1b, 1c, 1f, 1x, 1y, 1z (recorded variant levels) | Several low-latency LZ parsers and token formats; levels 1–9, 99, 999 express increasing memory/search effort | **Partial** — LZ route | No variant-specific parse/token implementation; recorded levels are in the settings JSON. Unsafe lzo1/lzo1a are intentionally disabled upstream because safe decoders are unavailable. See [LZO plugin options](https://quixdb.github.io/squash/api/c/md_plugins_lzo_lzo.html). |
| ms-compress / lznt1, xpress, xpress-huffman (default) | Three distinct Microsoft formats: LZNT1, XPRESS, and XPRESS-Huffman | **Partial** — LZ plus Huffman/DEFLATE building blocks | No Microsoft-format parser, code tables, or decoder; do not collapse XPRESS-Huffman into generic DEFLATE. See [ms-compress plugin](https://quixdb.github.io/squash/api/c/md_plugins_ms-compress_ms-compress.html). |
| ncompress / compress (default) | Adaptive-width LZW dictionary coding | **Untested / absent** | No LZW encoder/decoder or `.Z` framing. |
| pithy / pithy (0–9) | Snappy-derived parsing with Pithy-specific match finder and token decisions | **Partial** — LZ route | No Pithy parser or byte-compatible stream. |
| quicklz / quicklz (default) | High-speed LZ77 parsing with codec-specific match/literal coding | **Partial** — LZ route | No QuickLZ token stream or parsing heuristics. |
| snappy / snappy, snappy-framed (default) | LZ match/literal tags; optional chunk framing and per-chunk checksums | **Partial** — LZ route and independent CIX framing | No Snappy raw token codec or Snappy-framed stream; CIX framing is not Snappy framing. See [Snappy plugin](https://quixdb.github.io/squash/api/c/md_plugins_snappy_snappy.html). |
| wflz / wflz, wflz-chunked (1–2) | Fast LZ match parsing; optional chunked stream, chunk size, and little/big-endian output | **Partial** — LZ route | No wfLZ tokens or chunked format; CIX does not search wfLZ's level, chunk-size, or endianness settings. See [wfLZ plugin](https://quixdb.github.io/squash/api/c/md_plugins_wflz_wflz.html). |
| yalz77 / yalz77 (default) | Naive LZ77 longest-match search | **Partial** — LZ route | CIX's bounded hash-chain parser has different match search and costs; no YALZ77 decoder. |
| zlib / deflate, gzip, zlib (1–9) | DEFLATE LZ77 plus Huffman; raw, zlib, and gzip wrappers; level, window-bits, mem-level and strategy are independent settings | **Implemented / partial by representation** — CIXG1 DEFLATE coder/route; gzip not CIXG1 | Native raw DEFLATE substream is present. gzip and zlib wrapper compatibility is not the CIX format; only direct gzip CIXB1 is available. See [zlib plugin options](https://quixdb.github.io/squash/api/c/md_plugins_zlib_zlib.html). |
| zlib-ng / deflate, gzip, zlib (1–9) | Same DEFLATE wire families with a separate performance-oriented implementation | **Partial** — zlib DEFLATE family; gzip direct wrapper | Rust links system zlib through flate2, not zlib-ng. No zlib-ng runtime dispatch or independent performance qualification. See [zlib-ng plugin](https://quixdb.github.io/squash/api/c/md_plugins_zlib-ng_zlib-ng.html). |
| zpaq / zpaq (1–5) | PAQ-style adaptive context mixing, recurrence-distance and periodic models, embedded ZPAQL model | **Partial model concepts; no ZPAQ backend** | CIXM6 `fixedmix`/`expertmix`, PPM and periodic modules overlap only in broad principle. They lack ZPAQ's recurrence-selected contexts, ISSE/MATCH graph and SSE calibration. Local ZPAQ is an external reference; see [results.md](results.md). |
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
| Context-conditioned range substreams | **Implemented experimentally; not size-qualified** | New CIXG2 coder ID 6 uses the existing adaptive byte model with bounded context buckets. Tiny round-trip and manual Rust/Python cross-decode passed; the automatic predictor trial chose DEFLATE on the tested synthetic block, so this is not a measured win. See [CIXG2 extension](format/CIXG2-extension.md). |
| BWT / MTF / zero runs | **Partial** | Rust BWT+MTF route exists; current transform sorts suffixes and adds metadata. No bzip2/BSC block heuristics or joint parallel transform. |
| LZ matching | **Partial** | `lz_encode` uses a bounded hash table retaining up to eight recent positions per key. It is not a cost-optimal parser and does not reproduce any listed library's tokens. |
| Prediction, periodicity, recurrence distances | **Partial** | Predictor, stride, fixed mixture, record/periodic and CIXM6 adaptive modules exist. Fixed-mix recurrence v3 now serializes a saturated configuration and uses causal saved features; v2 decoder semantics remain preserved for archive compatibility. It is not admitted by the production selector, and period-model ablations or cross-block state are unqualified. |
| Entropy backends | **Partial** | raw, RLE, exact composition, adaptive range, count-range, DEFLATE and deterministic canonical Huffman (CIXG2 coder 7) are present. ANS/FSE, universal integer-code comparisons and measured per-substream coder choice remain absent/unqualified. |
| Context mixing / calibration | **Partial / unqualified** | `fixedmix` and `expertmix` implementations are research routes in CIXM6. They are not a ZPAQ port; no calibrated mixer integration into CIXG1 BEST is verified. |
| Transforms and compositions | **Partial** | BWT/MTF, stride, predictor residual and phrase representations exist. Composition order/depth is narrow; no all-order two-transform tournament or complete metadata-aware region segmentation. |
| Packaging and block-size search | **Partial, package search absent** | Automatic FAST/DEFAULT/BEST currently produced CIXG1 for fast/default and CIXG2 for best in the frozen 1 MiB profile screen. Each active path charges its own full frame/footer, but the selector does not materialize CIXG1 versus CIXG2 versus CIXM6/CIXF1 packaging, block-size alternatives, or a segmentation lattice and compare complete archive cost. |
| Streaming, bounds, and backpressure | **Implemented with caveats** | One input block is held at a time, output is framed/flushed, and decode emits frame by frame. CIXG1 frames are independent; CIXM6 stateful routes are separate. Ordered block workers and shared memory permits are bounded. Real pipe tests cover idle flush, pre-EOF frame/output, slow consumer, corruption and truncation; latency distributions, sustained throughput/RSS, and persistent-history/reset tradeoffs remain unmeasured. |
| FAST/DEFAULT/BEST candidate budget | **Implemented bounded policies; not exhaustive** | The frozen 1 MiB automatic-profile screen has two exact-decoded repetitions per effort with zero memory/budget skips: FAST selected LZ, DEFAULT BWT, and BEST PPM. Candidate limits, per-trial deadlines, shared admission and visible skip accounting are enforced. BEST remains a finite native search, not argmin over all transforms, segmentation, history, packaging, or external codecs. |
| Selector overhead / exhaustive oracle | **Measured partially; bounded payload and CLI archive oracles** | `oracle.rs` materializes and fresh-decodes its declared payload universe; the CLI oracle additionally enumerates 35 CIXG1 route/backend constraints and complete archives on two tiny fixtures. Both explicitly exclude package competition, general transforms, segmentation/history, external codecs and some parameters. The eight-cell forced-PPM parallel study retained one archive hash: four block workers used 2.56–2.57 s versus 8.10–8.16 s for one worker, with higher RSS. This is not automatic BEST scaling or universal throughput evidence. |

## CIXM6 production-selector coverage

CIXM6 implements a selector portfolio separate from CIXG1. In the current
integration tree, `encode_m6` offers modes 3 (legacy LZ), 4 (BWT), and 5
(transforms), and the decoder dispatch handles those modes. Candidate gates,
model beams, framing and state history still differ from the frozen Python
selector; qualification therefore requires canonical payload parity where
defined and independent exact archive decoding. Selector coverage should not
be confused with global CIXG1/CIXM6/CIXF1 packaging selection.

## Controlled reasons for rejecting ideas

One backend-composition hypothesis was rejected on Dickens: ZPAQ 7.15 method 5 over the complete Rust CIXG1 BEST archive produced 3,507,411 bytes versus the 3,506,980-byte input archive (+431 bytes), with exact nested decoding. This rejects this outer-wrap composition for this representation/input only; it does not reject direct ZPAQ or other representations. See [results.md](results.md).

The following mathematical constraint limits another experiment: applying BWT to one whole block is a permutation, so it preserves the block's global symbol counts and cannot reduce the number of sequences represented by a single whole-block multinomial rank. BWT is still useful when it creates local runs or local/conditional count structure; any claim must charge the BWT primary index, run/literal/count streams, and the coder. This is not a rejection of BWT or of the bzip2/BSC pipelines.

## Source identities

- Squash data import is pinned to `quixdb/squash-benchmark-web` commit `fed6ea3374155184672b71928d2b805463d156f0`; the CSVs are unmodified, 59,220 rows across nine machines and 28 datasets. Published times are upstream CPU seconds and are not compared to local timing.
- Squash plugin docs reviewed from `quixdb/squash` v0.7.0. The per-plugin source/version and options carried by the actual historical benchmarks are incompletely recorded by the CSV; see the settings JSON caveat.
- Frozen CIXG1 profiler/shortlist reference: Python commit `80b95427725ecf59d626b2982d50f6349abd56e1` as recorded in `selection.rs`.
- Dickens source: 10,192,446 bytes, SHA-256 `b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`.

## Resolved plugin names, option dimensions, and other inventory methods

The Squash UI name is not itself a complete codec identity. The pinned CSV
records the plugin, codec selector, and level list in
[`squash-settings-inventory.json`](squash-settings-inventory.json); options not
recorded in that CSV remain **unknown**, not defaulted by this report. The
Squash v0.7.0 plugin interfaces reveal these additional method-specific
settings and distinctions:

| Plugin | Concrete method/option distinctions that must remain separate | Current CIX treatment |
|---|---|---|
| Brotli | Quality 1–11; generic, text, and font modes | Direct Brotli wrapper only; mode selection and dictionary decisions are not inner CIX candidates. |
| BSC | BWT or no-sort path, LZP hash/minimum length, qflc static/adaptive coders, fast mode, threads, large pages, optional CUDA | Only BWT/MTF/zero-run principles overlap; no LZP or qflc coder. |
| CSC | Dictionary 32 KiB–1 GiB; delta, executable, and text filters; docs conflict on maximum level (table says 1–5 while prose says 6) | No CSC route/backend. Preserve settings ambiguity. |
| Density | Level 1 Chameleon dictionary; level 7 Cheetah swapped double-dictionary prediction; level 9 Lion multi-prediction and symbol/form-rank coding; optional SpookyHash checksum defaults off | Generic LZ/predictor/rank pieces are only partial; no paired dictionary or joint symbol/form coder. |
| FARI | Standalone FastARI arithmetic coder | CIX adaptive arithmetic exists; no FastARI probability model or canonical payload. |
| LZ4 | Raw lz4 versus lz4f; raw levels in docs 7–14, frame levels 0–16; frame block 64 KiB–4 MiB and optional xxHash | CIX LZ is only a principle overlap. CSV has raw levels 1–14, inconsistent with the inspected docs; historical settings are not normalized. |
| LZMA | XZ, legacy LZMA, raw LZMA1, raw LZMA2 are distinct; raw streams need dictionary and lc/lp/pb | CIXB1 currently wraps XZ only; no native filter/dictionary search. |
| LZO | Safe variants 1b/1c/1f/1x/1y/1z; levels 1–9, 99, 999 express different speed/memory intent; unsafe 1/1a decoders disabled upstream | CIX LZ only; no variant tokens or level parity. |
| LZHAM | Levels 0–4; extreme/deterministic parsing and decompression-rate-for-ratio options | LZ plus adaptive coder are separate components only; no LZHAM parse graph or joint probability model. |
| MS Compress | LZNT1, XPRESS, XPRESS-Huffman are different wire methods | LZ/DEFLATE principles only; no Microsoft framing or decoder. |
| Snappy | Raw stream and `snappy-framed` with chunk checksums are separate | CIX framing is not Snappy framing; no Snappy token implementation. |
| wfLZ | Raw/chunked; levels 1–2; chunk size 4 KiB–UINT32_MAX in multiples of 16; endian choice | Generic LZ only; none of those option dimensions are searched. |
| zlib | Raw DEFLATE, zlib, gzip wrappers; strategy, memory level, and window bits vary | Inner raw DEFLATE exists; wrappers are separate candidates only in CIXB1. |
| zlib-ng | Same format family as zlib but separate optimized implementation/build | Current Rust uses system zlib via flate2, not zlib-ng; no equivalent-speed claim. |
| ZPAQ | Plugin level 1–5 (default 1); v0.7.0 docs conflict by describing level 3 as highest ratio while CSV includes level 5 | Local libzpaq 7.05/7.15 level-5 outputs are matched; Rust native model coverage remains partial. |

Documentation and settings references are the Squash plugin API pages linked
from the [v0.7.0 plugin index](https://quixdb.github.io/squash/) and the
[Squash benchmark codec details](https://quixdb.github.io/squash-benchmark/).
The latter records historical version, level, threading/flushing support and
build flags (`-O3 -flto -march=native -mtune=native`); its published metric is
CPU time (not published wall time or memory). These upstream measurements are
not compared with local wall-time results.

Other already-present benchmark inventories add Brotli mode, XZ/LZMA2,
Zstandard dictionary/block modes, gzip strategy, and PAQ v216 mixer/LSTM
profiles. These are represented in the local codec-profile evidence under
`docs/research/2026-09-30-codec-profiles/`; PAQ profiles above the shared RAM
ceiling remain excluded and unranked. Across inventories, additional distinct
mechanisms requiring explicit principle coverage are LZW dictionary growth,
ANS/FSE sequence coding, static versus adaptive Huffman, delta/filter chains,
match-length/distance parsing, dictionary-trained transforms, chunk checksums,
and CPU/SIMD implementation effects. They are not separate “wins” merely
because an inventory lists another codec.

The concrete settings/method map for the other already-pinned local inventory
is in [other-inventory-methods.md](other-inventory-methods.md). It records the
90-cell exposed 16 KiB profile screen and its PAQ memory exclusion without
promoting those rows to qualification evidence.

Current follow-up: source `ee6b4396df760d19005c4e0800783fef58d52334` adds implicit
stdin workflows, dash-prefixed names, output contradiction rejection and a
64-opportunity minimum for DEFAULT PPM admission. All 178 final release tests
passed. The corrected ABBA DEFAULT v2 run verified eight cells and retained
the exact 6.30%/6.27% complete-size improvements on the two exposed ranges;
see [current evidence](adversarial-parallel-results.md). This does not close
the broad model/transform/coder, PGO or corpus-qualification queue.


## 2026-10-02: qualified native FAST follow-up

The new source changes are at `8ffa2c391` (implementation), with the pipe
regression at `d66739120c40fc409f2bf011b165389fc1062c2b`. A build from that exact
integration revision produces binaries/library byte-identical to the frozen
`d5e7d4ba` candidate used in the local cells. See the
[new evidence ledger](../2026-10-02-fast-opportunity/README.md) and
[build attestation](../2026-10-02-fast-opportunity/release-build-attestation.json).

| Principle | Current status | Actual deployed behavior / qualification |
|---|---|---|
| Gipfeli/Snappy-style compact bounded match discovery | Partial, production FAST | `src/fast_lz.rs`: fixed 256 KiB table, one recent candidate, adaptive probe skipping, safe 64-bit match extension and four boundary insertions; same CIXG1 route-3 grammar. No Gipfeli codec wire format or compact literal/command entropy representation. |
| Low-latency selection | Implemented FAST | Automatic nested raw/RLE/DEFLATE trials exclude exact rank. Explicit advanced coder overrides remain honored. On MR accumulated candidate time fell from 22.388 s to 0.464 s. FAST complete size grew 3.45%; no universal Pareto win. |
| Fast native CLI / Squash ABI alignment | Implemented; ABI verified | Both share default blocks: FAST 64 KiB, DEFAULT 32 KiB, BEST 64 KiB. Squash is one worker; CLI normally up to four. Fresh partial callback encoding/decoding/error tests pass; external Squash SDK plugin build/load remains unverified because SDK is absent. |
| CIXG1 decoder compatibility | Verified native | The previous `938e8805` native decoder freshly restored the complete new FAST MR archive exactly. Existing route, coder IDs and framing remain unchanged. |
| Idle pipe flushing and memory bounds | Verified for declared cases | Actual release pipe first complete frame/data ~151 ms at 100 ms idle flush. A new integration test restores 20 MiB+313 through an 8 MiB worker budget with irregular chunks, producer held open and partial flush. Persistent FAST LZ dictionary history is not added. |
| Gipfeli backend | Not deployed | Successful local buffered diagnostic is 4,702,538 B after decoder-copy-only repair. Stream controls remain failed. No demonstrated size advantage; the imported 1,885,645-B Peltast row remains unreplicated, with cause unresolved. |
| Maximum historical compatibility | Verified MR BEST | The complete Rust BEST 2,441,327-B CIXB1/bzip2-level-9 archive is byte-identical to the rehashed historical Python size result. No Python codec process ran. |

This dated update supersedes the historical FAST implementation descriptions
above. Native Gipfeli command/literal coding, word-16 lane relationships and
persistent FAST LZ history remain separate unqualified hypotheses. No new
backend was admitted, no source-identity dispatch added, and no Actions ran.
