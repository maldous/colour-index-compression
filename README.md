# Colour/Index Compression Research

Experimental lossless compression research based on:

**Current canonical direction:** direct 256-symbol multinomial CIX on `main`.
For a block with byte counts `n_0 ... n_255`, sequence order is represented inside the
exact type class `n! / (n_0! n_1! ... n_255!)`. Context-conditioned variants partition
the stream into deterministic context buckets and multinomial-code each bucket directly.


- direct 256-symbol multinomial/type-class coding
- context-conditioned multinomial coding
- majority/minority ("colour") representation of fixed-width bit blocks as a binary special case
- combinatorial/enumerative ranking of minority-bit positions
- mixed-radix pooling across blocks
- adaptive reversible pre-transforms
- entropy-coded metadata
- raw fallback for incompressible regions
- optional recursion as a measured configuration candidate, never assumed

## Current findings

- Random 50/50 data correctly remains effectively incompressible.
- Biased Bernoulli and Markov sources can approach their Shannon entropy rates.
- Predictor selection is more valuable than unconditional recursive compression.
- Lag/XOR predictors perform strongly on repeated and correlated data.
- Numeric delta + shuffle helps structured integer streams but needs stronger integer models.
- BWT/MTF/zero-run style preconditioning materially improves text.
- Adaptive per-region transform selection is the most promising general architecture.
- CIXM3 is open-ended and streamable: blocks are emitted before the final source size is known, and an end footer carries final length/checksum.
- Recursion should be retained only as an optional candidate and accepted only when exact encoded size improves.

## Candidate architecture

1. Segment input into fixed/adaptive/content-defined regions.
2. Cheaply profile entropy, runs, periodicity, lag correlation, numeric stride and repetition.
3. Generate a transform shortlist.
4. Evaluate reversible transform chains.
5. Encode residuals with the combinatorial/enumerative backend.
6. Entropy-code metadata and transform selectors.
7. Choose exact smallest representation, including all framing overhead.
8. Store original extension, length, codec version and checksum once in the file footer.
9. Fall back to raw data whenever compression does not pay.

## Planned CLI

- `cix file` — automatic compression
- `uncix file.cix` — exact restoration
- effort levels similar to gzip: `-1` through `-9`, plus `--extreme`
- expert flags for research/tuning
- `--recursion=off|auto|N`
- `--chunk=fixed|adaptive|content`
- `--block=auto|15,31,63,127,255`
- `--transforms=auto|...`
- `--memory=...`
- `--threads=...`

## Research rule

No claimed gain counts unless the resulting representation is fully reversible and its complete physical size includes selectors, framing, footer, checksums and all required metadata.
