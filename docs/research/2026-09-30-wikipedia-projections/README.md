# Frozen Wikipedia projection track

The research variable is a complete, deterministic, reversible projection.
The previous matrix, its archives, failures, exposed inputs and holdout policy
remain intact. Its last longer-line trial finished normally: 165,765 bytes,
6,969 bytes above its matched 158,796-byte PAQ control; the permitted size
gate skipped decoding and it remains unverified. No legacy trial is restarted.

The pre-track checkpoint is `research-before-projections-20260930`.
See `continuity.json` and `retained-wins.json` for exact identities and sources.

## Evaluation fixed before execution

All projections use the existing `benchmarks.volume_image_codec` implementation
unchanged: CIXV1 mode 5, local axial differences, lossless JPEG XL effort 9,
one thread. There is no PAQ fallback or candidate selection. The one interface
adapter widens each projected byte to a uint16 pixel, sets width 256 and z=1,
and pads the last row with zeros. Dimensions and projected length are paid.
The complete projection frame, including BWT indices, wavelet counts and
reconstruction metadata, is fed to this same codec. Model reset is empty per
contiguous input; no context or dictionary passes between trials.

The 29-byte outer header and 37-byte fixed metadata are identical in size
across projections. The existing CIXV1 frame's dimensions, checksum, metadata
and JPEG XL payload are additional paid bytes. Padding is encoded and its
extent is checked by the decoder. Source/runtime/program hashes are recorded
separately; an installed runtime inventory is not a minimized Hutter package.

The raw control stays PAQ v216 `-4 -simd AVX2`, same input bytes, basename
`candidate.source.bin`, empty initial predictor with state preserved throughout
the input. Its verified cached archives and restored inputs must be rehashed
before use. On the fixed 4 MiB development controls, their CIXSTR1 framing
also costs 29+37 bytes. We preserve their original archive and decoder rather
than re-encode or repackage them. Historical control times remain labelled
cached; this is not a fresh matched timing contest.

The older synthetic correctness control has 64 rather than 66 bytes of outer
framing; this two-byte difference remains charged to the projection candidate.
Correctness cells decode regardless of size. Real development controls and
projection candidates both have 66 bytes of outer framing.

## Recipes and priority

1. **P1:** whole supplied input BWT, reset move-to-front, eight MSB-first packed
   bit planes. Original length, BWT primary index and all plane padding are paid.
2. **P2:** causal order-1 successor recency ranks, then eight packed bit planes.
   The 257 rank lists start in byte order. Actual-byte ranks update only the
   already-decoded previous-byte context. No trained model is supplied.
3. **P3:** whole supplied input BWT, then an eight-level stable wavelet matrix.
   Every level's zero count is transmitted, along with the primary index and
   lengths. No final permutation or original corpus is consulted by decoding.

These are research priorities, not a measured ranking. P4 context tiles,
P5 transition planes and P6 neighbour residual projections remain deferred.
No width, predictor, coder or backend sweep is authorized by this plan.

## Gates and resource budget

Small empty, odd-sized, all-byte and randomized cases test both projections
and the complete adapter. One fixed locality diagnostic compares a 64x256
gradient raster with a seeded permutation preserving its exact value counts;
it establishes only that the selected path responds to local arrangement.

Independent bounded correctness runs use the existing deterministic paragraph
fixture. The first real comparisons use the already-exposed, hash-pinned
4 MiB development regions, beginning at offsets 0 and 400,000,000. These
include ordinary prose, markup and incomplete boundary fragments; every byte
is retained. No structural eligibility filtering or new holdout exposure occurs.

Each projection trial has a combined 300-second encode/decode ceiling, one
physical core, 3,000,000,000 bytes RAM, 1,000,000,000 bytes temporary space,
and zero swap. The existing global scheduler allows two such lanes for this
first wave, conservatively within the shared four-core/12 GB/4 GB ceiling.
Failed verification or budget exhaustion stops the cell. A completed archive
larger than a verified matching control may skip decoding; it is not promotable.

Only complete physical size plus independent archive-only SHA-256 restoration
can establish a win. A win would still require frozen holdout and justified
larger-scale evidence. No full-enwik9 compression, Hutter score or submission
is authorized. Revisions must state what changed and preserve the old results.

Run preparation and reports with `python -m benchmarks.hutter_projection_research`.
Every run retains its manifest, immutable source snapshot, exact commands,
30-second progress, terminal receipt and physical archive. The projection
report separates synthetic correctness, fixed development and any future
holdout strata. It includes every candidate before selection.
