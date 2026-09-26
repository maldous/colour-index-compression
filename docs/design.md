# CIX universal compression design

## Goal

Build a general-purpose lossless compressor in the class of gzip, bzip2 and xz, with a
single format-agnostic encoder that performs strongly across heterogeneous inputs.

No lossless compressor can be strictly smaller than every other compressor on every
possible input. CIX therefore targets broad, reproducible dominance across standard
general-purpose corpora while retaining raw fallback on incompressible data.

## Non-negotiable universality constraint

The encoder may not make decisions based on semantic or external knowledge of the input.

Forbidden selection signals:

- filename, extension, MIME type or path
- known file-format signatures
- language/source-code recognition
- media dimensions or format fields
- CPU instruction-set interpretation
- corpus member identity
- benchmark-specific offsets, row widths, periods or constants

Allowed selection signals are functions of the byte sequence itself:

- byte and bit distributions
- conditional distributions
- run statistics
- repeated substrings and match distances
- generic autocorrelation / lag correlation
- local entropy change
- reversible byte/word algebra under generic candidate widths
- exact candidate output size
- bounded CPU and memory budgets

The same candidate generator and MDL selector must be used for every input.

## Core representation

For a block of length `n` with byte counts `n_i`, the exact type-class cardinality is:

`n! / product(n_i!)`

CIX encodes:

1. active alphabet
2. symbol-count composition
3. exact sequence position within the multinomial type class

Context-conditioned CIX applies the same representation independently to deterministic
byte-context buckets.

## Generic model portfolio

### Repetition

- LZ match extraction
- literal, match-length and distance substreams
- exact-block deduplication
- generic match prediction

### Ordering / locality

- BWT
- move-to-front
- zero/run streams
- byte contexts of multiple orders
- adaptive and persistent contexts

### Algebraic residuals

Candidate widths/endian choices are generic competitors, never format diagnoses:

- byte/word XOR
- subtraction/delta
- delta-of-delta
- ZigZag residual mapping
- byte shuffle / transpose
- bit-plane decomposition

### Sparse / run structure

- dominant-symbol exception positions
- gap coding
- Rice/Golomb integer streams
- combinatorial bit planes
- run-symbol and run-length streams

### Search

- fixed, entropy-change and content-defined chunking
- beam-limited transform chains
- raw fallback
- Minimum Description Length over the complete physical representation

## Streaming model

CIX is open-ended and incrementally decodable. Models and chunk boundaries may adapt
over time, but adaptation must derive only from bytes already observed and deterministic
codec state.

## Compression effort

- `-1`: raw + cheap generic models
- `-3`: common contexts, runs, LZ and simple residuals
- `-6`: broader adaptive chunk/model portfolio
- `-9`: larger history and deeper generic search
- `--extreme`: maximum bounded generic search

Higher levels may spend more time, but they do not enable format-specific logic.

## Benchmark policy

A change is not accepted merely because it improves Canterbury.

Required general-purpose gates:

- Canterbury: fixed 11-file aggregate
- Calgary: fixed 14-file aggregate
- Canterbury Artificial: report every member individually, especially random input
- Canterbury Large: report each fixed member individually rather than an overall average
- Silesia
- enwik8 / enwik9 when runtime permits
- generated incompressible, biased, Markov, repetitive, numeric and mixed-regime streams

The Canterbury project itself describes Canterbury as the main comparison corpus,
Calgary as an older fixed corpus, Artificial as pathological/outlier testing, and Large
as individual large-file tests rather than an aggregate. CIX follows those distinctions.

For every benchmark:

- physical bytes only
- exact round-trip verification
- complete framing/model metadata included
- compression and decompression time
- peak memory where measurable
- no trained/shared dictionary unavailable to the decoder
- identical encoder policy across all files

Reference compressors include gzip/DEFLATE, bzip2/BWT, xz/LZMA, Brotli, Zstandard,
PPMd and context-mixing research compressors where available.

## Research objective

The research target is not “win one corpus.” It is to discover a generic model-selection
and multinomial representation architecture whose aggregate performance approaches or
exceeds the strongest general-purpose compressors across diverse data without semantic
special cases.
