# Colour/Index Compression Research

CIX is an experimental **universal, lossless, streaming compressor**. The canonical
direction is direct 256-symbol multinomial/type-class coding combined with generic
byte-statistical models.

For a block with byte counts `n_0 ... n_255`, its exact order is represented inside the
multinomial type class:

`n! / (n_0! n_1! ... n_255!)`

Context-conditioned variants partition a stream into deterministic context buckets and
multinomial-code each bucket directly.

## Universal-codec rule

CIX must behave like gzip, bzip2 or xz: the same codec must work on arbitrary bytes.

The canonical encoder must **not** select models from:

- file names, extensions or MIME types
- magic bytes interpreted as a known format
- natural-language or source-code recognition
- image dimensions or media semantics
- executable instruction-set knowledge
- corpus member names
- constants chosen for one benchmark file

Model selection may use only generic properties measurable from the byte stream itself:
frequency distributions, runs, repetition, contexts, distances, deltas, autocorrelation,
candidate transform cost, and bounded resource budgets.

A reversible algebraic transform may compete only when its parameters are generic and its
complete physical representation wins by Minimum Description Length.

## Current architecture

- direct 256-symbol multinomial/type-class coding
- context-conditioned multinomial coding
- binary colour/index coding as the two-symbol special case
- arithmetic/range realization for large type classes
- LZ match/literal/length/distance substreams
- BWT + MTF + run substreams
- adaptive and persistent byte-context models
- generic byte/word XOR, delta, delta-of-delta and shuffle transforms
- bit-plane combinatorial coding
- sparse dominant-symbol and run models
- exact-block deduplication
- adaptive and content-defined streaming chunk boundaries
- raw fallback for incompressible regions
- optional bounded transform-chain search

Every block competes under complete physical size accounting. No claimed gain counts
unless the result is lossless, self-describing, round-trip verified, and includes all
selectors, model metadata, framing and checksums.

## Streaming

The CIX stream is open-ended:

- blocks can be emitted before final input size is known
- block boundaries can move as statistics change
- models can change from block to block
- decoder output can be produced as frames arrive
- history can persist across frames
- the footer verifies final byte count and checksum

## CLI

- `cix file` — automatic compression
- `uncix file.cix` — exact restoration
- `-1` through `-9` — increasing generic search effort
- `--extreme` — broad bounded search
- expert controls for chunking, history and generic model families

## Benchmark evidence stack

CIX uses a fixed evidence order. A result does not graduate to a stronger claim until it
survives the earlier tiers under the same format-agnostic codec policy.

1. Canterbury + Calgary + Artificial — fast architectural gate and pathological checks.
2. Silesia — primary heterogeneous general-purpose leaderboard gate.
3. Canterbury Large — large-file scaling, reported per member rather than as one average.
4. enwik8 — 100 MB long-context/text modelling gate.
5. enwik9 — 1 GB maximum-compression/text-modelling gate.
6. Pizza & Chili Repetitive Corpus — long-range repetition and deduplication stress.
7. Frozen modern CIX real-world corpus — immutable, hashed contemporary formats and mixed
   assets, used only after the public standard corpora.

Canterbury alone is not an optimization target. Improvements that merely trade one
corpus-specific trick for another do not count as architectural progress. Silesia is the
first benchmark used for an external leaderboard-style claim because its published
score is the total number of bytes from compressing its 12 files individually.
