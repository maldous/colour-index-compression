# Multinomial CIX

## Core realization

Binary colour/index coding is the two-symbol special case of a more general type-class
code. For a byte block of length `n` with byte counts `n_0 ... n_255`, the number of
distinct byte sequences with exactly that composition is:

`n! / (n_0! n_1! ... n_255!)`

CIX now encodes the byte stream directly in that 256-symbol space instead of first
expanding it into independent bits.

A physical multinomial block contains three nested combinatorial indexes:

1. **Active alphabet** — the set of byte values present, ranked among `C(256,m)` sets.
2. **Composition** — the positive counts of those `m` symbols, ranked using
   stars-and-bars among `C(n-1,m-1)` compositions.
3. **Permutation** — the exact original sequence, ranked among
   `n! / product(n_i!)` multiset permutations.

Nothing is estimated here: all three indexes are exact and reversible.

## Context-conditioned multinomial CIX

The stronger extension partitions positions into deterministic context buckets. For each
input byte, a bounded context hash chooses a bucket from preceding decoded bytes. The
sequence of next bytes observed in each bucket is then independently encoded as a
multinomial type class.

The context bucket set and the bucket lengths are themselves encoded combinatorially:

- active bucket IDs: `C(B,q)`
- positive bucket lengths: `C(n-1,q-1)`
- each bucket payload: its own 256-symbol type class

During decoding, the already-decoded history selects the same bucket and the decoder
consumes the next symbol from that bucket's reconstructed stream. No per-byte predictor
selector is required.

This means the payload cost trends toward empirical **conditional** entropy instead of
only global byte entropy.

## Dynamic / streaming behaviour

The format is block-streamable and does not require a fixed model for the whole asset.

- input may arrive through repeated `feed()` calls
- `feed()` can immediately emit complete compressed frames; the final asset size is not required up front
- the encoder buffers only a bounded region
- candidate boundaries are reconsidered as statistics change
- block boundaries move when splitting materially reduces description length
- each emitted block independently selects:
  - raw
  - plain 256-symbol multinomial
  - one of several context-conditioned multinomial models
- prior decoded bytes are retained as context across block boundaries
- random/incompressible regions fall back to raw
- model-selection parameters do not need to be repeated globally; each block is
  self-describing
- an explicit end footer carries final byte count + CRC32; no block count or original length is required in the header
- `StreamDecoder.feed()` can emit restored bytes incrementally as complete frames arrive
- CRC32 verifies exact reconstruction

The compression search is therefore dynamic in both dimensions:

- **where** a block ends
- **how** that block is represented

## Why this does not violate Shannon

If all possible byte strings are considered uniformly, describing the active alphabet,
composition and permutation cannot make every string shorter. Random data therefore
selects the raw representation.

The opportunity appears when the source occupies a small statistical subset:

- skewed byte frequencies
- repeated contexts
- structured records
- sparse residuals
- changing regimes that are isolated into separate blocks

The context-conditioned form is especially important because it turns context
predictability into smaller per-context type classes while staying within the same
multinomial CIX framework.

## Current implementation

`cix/multinomial.py` is the canonical implementation on `main`.

The code currently prioritises mathematical correctness and physical byte accounting.
The large-integer rank/unrank operations are deliberately straightforward Python and will
need lower-level optimisation before throughput benchmarking is meaningful.

Next optimisation targets:

- faster large-integer type-class ranking
- adaptive/context-model shortlist profiling
- context bucket inheritance and merging
- LZ/match streams encoded as multinomial substreams
- Rice/Elias-Fano/FOR integer substreams
- dynamic context mixing
- content-defined boundaries
- byte-level container/CLI integration
