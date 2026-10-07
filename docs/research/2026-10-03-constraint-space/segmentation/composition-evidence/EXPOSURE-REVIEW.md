# Exposure review — `citytemp_f32` numeric composition input

Read-only preparation for the user-authorized composition work. This review did
not open the source file or either proposed candidate slice, generate a slice,
run a codec, or inspect source bytes.

## Identity and recorded exposure

The authorized source identity is:

| Field | Value |
|---|---|
| path | `/home/user/cix-datasets/originals/fcbench/citytemp_f32` |
| whole-file bytes | 11,625,304 |
| whole-file SHA-256 | `3f8ba1a80684edea13185934a2ec4a612715f1942f81e94d76c60e00b568ba7f` |
| declared layout | 2,906,326 raw `float32` values |

The acquisition cutoff and dataset manifest record that whole-file identity.
That is a hash/availability record. It does not itself show that a compression,
profiling, representation, or model-selection algorithm examined every byte.

Searching the evidence records by this exact whole-file SHA-256 and source path
found one algorithm-exposure receipt: the latent-layout real-prefix screen
froze and compressed `[0, 4096)`. Its `input-freeze.json`, `sources.json`, and
`results.json` record offset `0`, 4,096 input bytes, and the derived slice hash
`3cf1b7e2a0e1579055624033b530af956faae3f9291068f3004c4c559d4b666f`.
No other exact-identity-linked range or result record was found. This is an
evidence-record conclusion, not a statement that no unrecorded historical
whole-file operation occurred.

## Proposed reservation status

| Role | Proposed interval | Explicit overlap with recorded algorithm exposure | Status from available receipts |
|---|---:|---|---|
| qualification | `[1,048,576, 1,052,672)` | none; it is disjoint from `[0, 4,096)` | eligible for a new frozen slice |
| conditional replication | `[2,097,152, 2,101,248)` | none; it is disjoint from `[0, 4,096)` and the qualification interval | eligible only if the predeclared qualification rule triggers it |

Both offsets are aligned to 4,096 bytes and both intervals are inside the
11,625,304-byte source. They are new with respect to the explicit compression
and profiling exposure receipts found in this review. They should not be
described as historically untouched in an absolute sense: the whole-file
identity hash and availability records establish source identity, while the
available evidence cannot rule out undocumented or broad historical reads.

## Freeze requirements before any execution

Root should record, before extracting either slice: the whole-file identity,
offset, length, resulting slice SHA-256, source byte count, experiment ID,
frozen recipe, and the conditional rule that governs whether the replication
slice may be used. The qualification and replication slices must remain
separate records. The replication reservation must not be read by a codec or
used for selection unless that rule has already triggered.

No production path changes are indicated by this review. Root owns planning,
execution, and any future commit; this document is exposure preparation only.

## Deterministic fallback if a later receipt proves either range exposed

Use receipts tied to this exact whole-file SHA-256 to build the union of all
explicit algorithm-exposure half-open intervals. Starting at offset 0, inspect
successive 4,096-byte-aligned starts and choose the first interval
`[start, start + 4096)` that is within the source and disjoint from that union.
Record the receipt set and resulting slice hash before any codec operation.

With only the currently recorded exposure `[0, 4096)`, this rule would select
`[4096, 8192)`. It is a deterministic fallback based on receipts; it does not
claim protection against unrecorded historical full-file processing.
