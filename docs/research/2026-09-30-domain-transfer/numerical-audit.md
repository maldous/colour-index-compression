# Numerical-domain transfer: NOAA water levels

## Existing evidence transferred carefully

The selected São grid result used decoded quantized coordinates to form
decoder-reconstructible groups, then emitted **raw correction IDs before PAQ**.
It did not win by applying a rank coder: paid count/rank alternatives lost to
the raw grouped stream. The reusable lesson is to expose a causal numerical
residual representation only when its grouping state can be rebuilt during
decode, then let the fixed PAQ backend model the resulting byte stream.

The present adapter does not copy SAO's record detector or coordinate grammar.
It has one strict, documented CSV schema and makes all timestamp, decimal,
precision and flag state part of its returned frame. PAQ already has broad
general-purpose context capacity, so the experiment must compare the entire
physical pipeline, not a transform-size estimate or a rank-only comparison.

## Asset

[`numerical-asset.json`](numerical-asset.json) pins a new authoritative NOAA
CO-OPS verified water-level dataset: station 9414290 (San Francisco), MLLW,
metric units, UTC, 2024-01-01 through 2024-01-31. The acquired CSV has 7,440
six-minute records and SHA-256
`bd61d79fa90e4fe0817c9d702a7138c640c7e6ded5a0515e10a9fac13e4f1e97`.
It is neither a Silesia member nor a relabelled historical numerical benchmark.
The source is durably archived at
[`assets/noaa-water-level-202401.csv`](assets/noaa-water-level-202401.csv)
and rehashes to that value.

## Frozen candidate and packing ablation

`benchmarks.domain_numeric_noaa` exposes the root-harness contract:

```python
encode(data: bytes, variant: str) -> bytes
decode(frame: bytes) -> bytes
inspect(data: bytes) -> dict
```

The structural candidate is `numeric-delta-columns-v1`. It stores a strict
schema/rules header, first timestamp plus signed minute deltas, water-level and
sigma fixed-point decimal deltas with transmitted decimal precision, four flag
columns, and quality bytes. All values reconstruct their original lexical CSV
tokens exactly. The transform is self-contained (`DNM1`) and contains the
original byte length, rules, header, row count, and every stream.

`numeric-delta-rows-v1` is retained solely as a **layout ablation**. It has the
same values and predictors, but places transformed records adjacently and adds
per-record lengths. It can reveal a PAQ-context effect; it cannot be described
as recovered packing capacity and is not scheduled in the initial comparison.

The genuine packing ablation is
`numeric-delta-columns-packed-meta-v1`. It retains the exact column/delta
representation but jointly packs, for every known row, water precision
(`0..3`), sigma precision (`0..3`), and the four decimal flags (`0..9`) into a
fixed-width mixed-radix sequence (base 160,000). Quality bytes remain in their
own stream. The frame pays the exact packed-rank length and every stream
boundary; its rules and row count are embedded in the self-contained frame.
Only the six bounded metadata digits leave the numerical streams. Numeric
values themselves remain ordinary signed delta values, and PAQ is unchanged.

On this 7,440-row source, the six raw metadata bytes per row total 44,640
bytes. The complete fixed-width mixed-radix metadata stream is 16,078 bytes,
recovering 28,562 raw transform bytes before stream framing. This is not a
claim of equal PAQ archive savings: PAQ may already exploit much of the low
entropy in the separate precision/flag streams.

No variant uses an external dictionary, training state, filename recognition,
or a hidden original copy.

On the acquired complete bytes, the adapter reports 138 distinct water-level
deltas, 71 distinct sigma deltas, precision values 1/2/3, one quality symbol,
and a fixed six-minute timestamp delta. These are eligibility diagnostics, not
compression measurements.

## Required matched experiment

After archival, root's shared scheduler should run exactly these complete
pipelines under the global four-CPU, 12,000,000,000-byte RAM and
4,000,000,000-byte temporary-storage cap:

1. original CSV -> pinned PAQ v216 `-4 -simd AVX2`;
2. `numeric-delta-columns-v1` frame -> the same PAQ command;
3. `numeric-delta-columns-packed-meta-v1` frame -> the same PAQ command.

Each returned PAQ wrapper must charge the complete transform frame, native PAQ
archive and wrapper bytes. Decode must receive only the final archive and
restore the original CSV SHA-256 independently. No rank tournament, Silesia
run, large download, or independent scheduler is authorized by this audit.
