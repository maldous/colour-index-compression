# Distinct methods in the other pinned local benchmark inventory

The existing local codec profile screen at `docs/research/2026-09-30-codec-profiles/`
contains 90 settings cells. Its inputs are exposed 16 KiB slices, so this is
method/settings coverage only, not new qualification evidence or a holdout.
Exact settings include:

| Codec/settings | Distinct principle | Rust CIX coverage and remaining gap |
|---|---|---|
| gzip levels 1 and 9 (`fast`/`size`) | DEFLATE plus gzip wrapper/checksum; effort-specific canonical framing | Raw DEFLATE substream exists; gzip wrapper is separate CIXB1 only, not an automatically compared inner candidate. zlib strategy, window-bits and mem-level remain unexplored. See [zlib options](https://quixdb.github.io/squash/api/c/md_plugins_zlib_zlib.html). |
| bzip2 levels 1 and 9 | BWT, MTF, runs, Huffman and level-dependent 100–900 KiB block sorting; work-factor controls fallback sort | Related BWT/MTF/runs exist; no matching block parser/Huffman choice or inner payload parity. Upstream bzip2 does not provide reliable flush semantics. See [bzip2 options](https://quixdb.github.io/squash/api/c/md_plugins_bzip2_bzip2.html). |
| XZ presets 0 and 9e | LZMA2 dictionaries, range coding, extreme preset, checksums | CIXB1 can carry XZ; no LZMA2/filter/dictionary or preset search in native CIX. Raw LZMA1/LZMA2 and lc/lp/pb are distinct paths. See [liblzma formats/options](https://quixdb.github.io/squash/api/c/md_plugins_lzma_lzma.html). |
| Brotli qualities 0 and 11 | LZ77, static dictionary, context modes, quality-controlled parsing | Direct CIXB1 wrapper only; no generic/text/font mode or dictionary route. The Squash plugin documents levels 1–11; quality 0 in this local screen is an external tool setting, not a Squash CSV level. See [Brotli options](https://quixdb.github.io/squash/api/c/md_plugins_brotli_brotli.html). |
| Zstandard `--fast=131072` and `--ultra -22` | LZ parsing, block modes, Huffman literals, FSE/ANS sequence coding, dictionary/block settings | Direct CIXB1 wrapper only; no inner sequence parsing or native ANS/FSE. |
| PAQ8px v216 levels -1 and -8 | Adaptive context mixing and richer predictor/mixer portfolios | `fixedmix`/`expertmix` overlap at the principle level only; no PAQ-equivalent model or backend. |
| PAQ v216 `-12L`, 5 LSTM layers | Deep recurrent/context mixing at high memory | Not run because it exceeds the shared 12 GB cap; explicitly excluded and unranked. |

Other inventory dimensions to keep distinct are LZW dictionary growth, static
versus adaptive Huffman, match-length/distance coding, filter chains, trained
dictionaries, chunk checksums, and implementation SIMD/ISA choices. The local
Rust tree currently has exact rank, adaptive range, DEFLATE, BWT/MTF, PPM,
prediction, periodic, transform-chain and context-mix modules, plus deterministic
canonical Huffman as CIXG2 coder 7 and a recurrence feature in fixed-mix payload
v2. It still has no native ANS/FSE sequence coder or ZPAQ-compatible mixer/model.
The recurrence addition is not a ZPAQ port or a qualified selector win. These are
principles to cover or explicitly exclude, not independent codec-count wins.

Prior benchmark records must not be compared by upstream CPU time to local wall
time. `FINDINGS.md` identifies the repeated 16 KiB exposure and the measured
settings and resource exclusions.

## Provenance boundary and actual local settings

The local settings screen and Squash import answer different questions. The
local screen records pinned commands on exposed 16 KiB slices. The Squash CSV
records plugin, codec and level only. It does not preserve every library
revision, compiler/ISA, dictionary, wrapper flag or non-level plugin option.
An empty level remains **unrecorded** rather than a reconstructed default.

| Local profile codec | Fast / normal / maximum setting | Distinct mechanisms | Native CIX relationship |
|---|---|---|---|
| CIX | frozen fast / balanced / frozen maximum | selector, representations, coders and CIX framing | Native baseline; source and selector identity must be frozen per trial. |
| gzip | `-1` / existing `-9` / `-9` | DEFLATE parser/Huffman and gzip trailer | Raw DEFLATE is native; gzip is CIXB1-only. |
| bzip2 | `-1` / existing `-9` / `-9` | BWT, RLE, MTF, selectors, canonical Huffman and work-factor | BWT/MTF overlap; CIXB1 bzip2 is backend-only. |
| XZ/LZMA2 | `0` / `6` / `9e` | LZMA parser, range contexts, dictionaries, filters and XZ index/checksum | CIXB1 XZ only. |
| Brotli | `0` / `6` / `11` | Static dictionary, literal contexts/maps, quality parser, Huffman/metablocks | CIXB1 Brotli only. |
| Zstd 1.5.5 | `--fast=131072` / `3` / `--ultra -22` | LZ parser, Huffman literals, FSE/ANS sequences, dictionaries and blocks | CIXB1 Zstd only. |
| PAQ8px v216 | `-1` AVX2 / `-8` AVX2 / `-12L` five LSTM | Bit contexts, mixer/SSE and memory architecture | Concept overlap only; `-12L` needs about 29 GB, exceeds the 12 GB cap and is unranked. |

The completed cells verify restoration, not a new corpus score or global
optimum. Imported Squash CPU time must never be ranked against local wall time.

## Alias and plugin resolution

| Plugin | Actual codec identities | Material distinction |
|---|---|---|
| `lz4` | raw `lz4`; framed `lz4f` | Raw versus frame changes wire format. LZ4F has block/checksum/linkage controls. CSV raw levels 1–14 conflict with some historic docs; retain the discrepancy. |
| `lzma` | `lzma`, `lzma1`, `lzma2`, `xz` | Distinct raw/container formats with filters, checksums and headers. |
| `lzo` | `lzo1b`, `lzo1c`, `lzo1f`, `lzo1x`, `lzo1y`, `lzo1z` | Different parsers/tokens and irregular 11/12/15/99/999 levels. Unsafe lzo1/lzo1a were unavailable due decoder safety support. |
| `ms-compress` | `lznt1`, `xpress`, `xpress-huffman` | Three formats; XPRESS-Huffman is not generic DEFLATE/Huffman. |
| `snappy` | raw `snappy`; `snappy-framed` | Framed checksums/chunks are separate. |
| `wflz` | `wflz`; `wflz-chunked` | Chunking, chunk-size and endianness are independent of matching level. |
| `zlib`, `zlib-ng` | raw `deflate`, `zlib`, `gzip` | Wrapper/window/mem-level/strategy are independent; zlib-ng is a separate optimized implementation. |
| `bsc` | `bsc` | Unrecorded level does not remove LZP/minlen/qflc, threading, large-page or CUDA dimensions. |
| `csc` | `csc` | CSV has 1–5; documentation has a level prose/range discrepancy. Dictionary and filter settings are unrecorded. |
| `density` | `density` | 1, 7 and 9 are Chameleon/Cheetah/Lion method families, not just a continuous effort knob. |
| `lzham` | `lzham` | Parse graph, deterministic parse and decode-rate controls are distinct and unrecorded. |
| `zpaq` | `zpaq` | Level alone does not recover model program, recurrence scan or block configuration. |

BriefLZ, Brotli, bzip2, copy, Crush, FARI, FastLZ, Gipfeli, LZF, LZG,
LZJB, ncompress, Pithy, QuickLZ, YALZ77 and Zstandard retain individual
method entries in [method-principles.md](method-principles.md). Similar LZ
names do not establish parser or format equivalence.

## Cross-inventory opportunity map

| Family | Inventory leads | Native CIX state | Required comparison before promotion |
|---|---|---|---|
| LZ parser cost | BriefLZ, FastLZ, LZ4, LZO, Pithy, QuickLZ, YALZ77, LZMA/Zstd/LZHAM | One 4-byte hash table, eight candidates and 64 KiB distance in `main.rs::lz_encode`. | Same CIX tokens/coder; charge parse CPU, metadata bytes and RSS. |
| Dictionaries | Brotli static dict, Zstd/XZ presets, CSC large dict, LZW growth, Density doubles | Input-local LZ/phrase only. | Generic input-derived dictionary with serialized cost and reset/history semantics. |
| BWT family | bzip2, BSC | BWT/MTF/zero-runs only. | Conditional/local BWT streams and valid transform order, charged metadata. |
| Entropy coding | DEFLATE/bzip2 Huffman, FARI/LZHAM/LZMA range, Zstd FSE, Density ranks | rank/count-range/adaptive range/DEFLATE. | The same frozen literal/length/distance/count streams through each coder, with headers/tables. |
| Prediction/mixing | Brotli contexts, LZMA lc/lp/pb, PAQ/ZPAQ, Density | PPM, adaptive byte context, fixed/expert mix and periodic modules. | Matched prediction-information ablation with state/calibration cost. |
| Reversible filters | CSC, XZ, BSC LZP and stride/delta/record relationships | stride/delta/predictor/BWT/phrase/CIXM6 chains. | Bounded generic transform beam with IDs/parameters and exact inverse. |
| Framing/integrity | gzip/zlib, XZ, LZ4F, Snappy framed, wfLZ, Zstd | CIXG1/G2 frames+footer and CIXB1. | CIX pipe, slow consumer, idle-flush, truncation/corruption tests. |
| Resource design | zlib-ng, LZ4/Snappy, BSC threaded/CUDA | Bounded candidate workers only. | Release/LTO/PGO and 1/2/4-core CPU/RSS/allocation profile before SIMD/native-call work. |

## External-codec attribution policy

CIXB1 wraps a declared complete backend payload and charges header and
SHA-256. A CIXB1 result is an **external backend** result, never evidence of a
native CIX representation, parser, predictor or entropy-model improvement. It
is bounded whole-payload processing and rejected for `--stream`; it cannot
silently replace a native candidate.

Current gaps are native Huffman, ANS/FSE, LZW, LZMA, Zstd parsing,
static/trained dictionary policy, BSC LZP/qflc, and a qualified CPU/RSS/
allocation/PGO/stream-latency profile. These remain queued rather than inferred
from source presence.
