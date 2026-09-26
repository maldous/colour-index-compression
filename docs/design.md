# CIX expert-search design

## Goal

Beat the xz-9 aggregate ratio on the canonical Canterbury corpus while keeping every
selected representation lossless, self-describing, round-trip verified, and fully
accounted for.

There are two scoreboards:

1. **CIX Expert** — may select mature model families as interchangeable backends.
2. **CIX Native** — only original/native CIX transforms and entropy coding.

XZ/LZMA is comparison-only and may not be selected by either scoreboard.

## Search hierarchy

### Segmentation

- whole file
- fixed chunks
- adaptive entropy-change chunks
- content-defined chunks (Gear/Rabin)
- hierarchical chunks with model inheritance

### Predictors and transforms

- identity/raw
- bit XOR lag
- byte XOR lag
- byte subtraction lag
- delta / delta-of-delta
- ZigZag residual mapping
- frame-of-reference / patched FOR
- byte shuffle / bit-plane transpose
- periodic/stride predictors
- zero-run / general run coding
- sparse gap coding
- Elias-Fano candidate for sparse positions
- Golomb/Rice integer residual coding
- BWT + MTF + RLE
- LZ match extraction / optimal parsing
- token/dictionary transform for text/JSON/source
- record-column transpose
- executable branch/address normalization
- floating-point XOR and exponent/mantissa separation

### Statistical models

- order-0 empirical
- KT/Bayesian smoothing
- PPM/backoff contexts
- CTW-style variable-order contexts
- match prediction
- run prediction
- context mixing / mixture of experts
- model inheritance between chunks

### Coding backends

Native:
- binary combinatorial/enumerative ranking
- multinomial enumerative coding
- mixed-radix pooling
- rANS/range coding for model/selector streams
- Rice/Golomb/universal integer codes

Expert/reference:
- Brotli
- PPMd
- Zstandard
- bzip2/BWT family
- ZPAQ/context mixing

Comparison only:
- xz/LZMA

## Recursive mode

Recursion is an optional search edge, not a default stage.

A recursive candidate is retained only if:

- complete physical size decreases after all chain metadata;
- round-trip reconstruction is verified;
- it beats the best non-recursive candidate.

More promising than whole-stream recursion is **substream recursion**: separately
re-model transform IDs, match lengths, match distances, minority counts, ranks, run
lengths, and exception streams.

## Optimizer

Use Minimum Description Length as the universal objective:

    total_bits =
        container
      + transform_description
      + transform_parameters
      + model_description
      + selectors
      + coded_payload
      + checksum

Search strategy:

1. cheap profiling (entropy, runs, lag correlation, periodicity, stride, match density);
2. shortlist transform/model families;
3. beam search through reversible transform chains;
4. exact physical coding of finalists;
5. choose the smallest verified representation;
6. raw fallback if no candidate pays.

## Compression effort

- -1: raw + very cheap predictors; small search
- -3: common lag/delta models
- -6: adaptive chunks, dictionaries, PPM/BWT candidates
- -9: broad model/block/chunk search
- --extreme: context mixing, large dictionaries, beam search, optional recursion

## Benchmark policy

Every result must include all framing and model metadata required to decode.

Modelled entropy estimates are reported separately from physical byte streams.
A modelled estimate cannot be used to claim a production compression ratio.

Primary gate: canonical 11-file Canterbury aggregate.
Secondary gates: Calgary, Canterbury Large, Silesia, enwik8/enwik9, mixed real-world
file sets, already-compressed media, numeric/time-series datasets, source trees.

The codec must also report compression/decompression speed, peak memory, and exact
round-trip hashes.
