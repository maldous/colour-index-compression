# Exact transformed-byte dedup: production insertion audit

This is an implementation audit, not a promotion decision. The qualified `representation-search-dedup-v1` screen found two duplicate transformed byte sequences: candidates 7 and 3, and candidates 8 and 4. The duplicates had identical nested CIXG1 archives and complete candidate sizes. The screen retained candidate order and first-candidate tie selection.

## Existing production paths

The relevant production path is CIXM6 mode 7:

1. [`m6_try_chain_and_numeric_candidates`](../../../rust/cix-native/src/main.rs) calls `chain::encode(data, EncodeOptions { beam, effort })` when `data.len() >= 32`, effort is at least 8, and the existing `available >= 128 * data.len()` admission succeeds.
2. [`chain::encode`](../../../rust/cix-native/src/chain.rs) materializes all nine reversible transforms, ranks them by a type-class estimate and transform ID, then calls `consider_transform` for the first `beam` transformed byte vectors.
3. [`consider_transform`](../../../rust/cix-native/src/chain.rs) invokes the same inner coders for every selected transformed vector: multinomial, the frozen context set, LZ, BWT, bitplane, sparse and runs as eligible. `record_candidate` then adds the three-byte chain header `(version, transform_id, inner_mode)` and compares the complete chain payload using strict `<`.

There is no transformed-byte candidate cache in this path. The only related production mechanism is CIXM6 mode 9: `m6_try_recent_reference` compares **original blocks** after all candidate work and emits a stored inter-block reference. It cannot avoid repeated coding of two distinct transform instructions that yield equal bytes. `chain.rs` also has an LZ distance cache, which is an encoded-data model and is unrelated.

## Smallest safe change

Refactor `chain.rs` locally, without changing the CIXM6 wire format:

* Split `consider_transform` into a materializer that returns its ordered inner candidates and a recorder that calls `record_candidate` for a specified `transform_id`.
* In `chain::encode`, immediately before the existing selected-transform loop, create a per-call exact cache keyed by `(transformed_bytes, options.effort)`. A `HashMap<Vec<u8>, Vec<MaterializedInner>>` is exact because `Vec<u8>` equality resolves hash collisions. The key must own bytes or use a collision-safe retained reference; a digest alone is insufficient.
* On a hit, replay the cached ordered inner candidates through `record_candidate` with the **current** `transform_id`. Do not reuse a completed mode-7 payload: its transform ID is reconstruction data.
* On a miss, materialize exactly as today, record it, then cache the inner payloads only if the declared cache reservation admits their combined key and payload bytes. If it does not fit, do not cache and continue with the current uncached behavior.

The cache is valid only inside one `chain::encode` call. That scope fixes backend and coding parameters: the current `EncodeOptions` exposes only `beam` and `effort`; all context and LZ calls use empty history, and no adaptive persistent state is shared. It must not cross CIXM6 blocks, CIXG candidate workers, format versions, backend options, or calls with a different effort. CIXG candidate evaluation can run in parallel and has deadline-based omissions, so it is outside this first insertion.

## Resource and selection contract

Pass an explicit cache-byte allowance from `m6_try_chain_and_numeric_candidates` through `chain::EncodeOptions`; it must be subtracted from the already admitted CIXM6 `available` bytes. The current mode-7 admission is `128 * data.len()`, and `m6_memory_plan` already charges history, source/candidate buffers, reference queue, and persistent state. The cache must have a hard byte counter covering key capacity plus each retained inner payload capacity. It must stop admitting new entries before the allowance, never expand the CIXM6 memory envelope, and release at the end of the block.

Every replay must still call `record_candidate` in the original transformed-order and inner-order. This preserves:

* `CandidateSize` observations and `--explain` descriptions;
* complete stored cost: three-byte chain header, transform ID, inner mode and inner payload;
* strict `<` first-declared tie behavior;
* selected archive bytes, decoder instructions and CRC input.

The cache changes encoder work only. It cannot add a decoder cache, archive reference, selector metadata, or timing-dependent candidate choice. If cache admission fails, it is an observed uncached execution, not a candidate omission and not a size change.

## Concrete acceptance for the next implementation

1. Fixed duplicate controls must show fewer inner codec calls and byte-for-byte identical mode-7 payloads, candidate tables and selected complete CIXM6 archives.
2. A distinct-transform control must show no cache hit and identical archive bytes.
3. For both controls, fresh independent decoding restores the source SHA-256; malformed mode-7 frames retain current rejection behavior.
4. Run with the same effort, memory and block size both cache-admitted and cache-full. Cache-full must produce the current uncached bytes and report no false reuse.
5. Verify CIXM6 serial history and mode-9 reference behavior across at least two blocks. The cache must not survive the block boundary or change the current block-reference decision.
6. Measure one encode and one decode per declared configuration, charging cache reservation separately from peak RSS and temporary storage. No score, corpus, or selector-wide claim follows from this mechanism test.
