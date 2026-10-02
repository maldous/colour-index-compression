# PPM hotspot investigation: frozen 886 DEFAULT Kennedy profile

## Evidence

This is read-only analysis of
`benchmark-work/rust-performance-audit/preliminary-perf/combined-886-default-kennedy*`.
It sampled the frozen `8865bfbcc` DEFAULT encode of Kennedy with Linux `perf`:
549 core-cycle samples, zero lost samples, and an approximate event count of
12,586,217,643. It is one profile, so percentages locate candidate work rather
than predict a universal speedup.

| Sample share | Symbol | Interpretation |
|---:|---|---|
| 25.20% | `num_bigint::BigUint::div_rem_cow` | exact-rank arithmetic, addressed separately by the merged colex work |
| 9.07% | `ppm::observe_from` | PPM context update and table maintenance |
| 8.04% | `bwt_transforms::sort_unstable_by_key` | BWT route work |
| 6.64% | `BigUint::scalar_mul` | exact-rank arithmetic |
| 5.41% | `ppm::eligible` | filtered-context vector construction |
| 3.44% | `ppm::encode_fixed_from_state` | fixed PPM candidate encoding |

The same report attributes allocator activity to PPM: `malloc` samples include
0.90% below `observe_from` and 0.55% below `eligible`; `_int_malloc` includes
1.28% below `eligible`; and `realloc`/`RawVec::finish_grow` accounts for 1.46%
overall. The report also observes `RandomState::hash_one` at 2.36%, consistent
with repeated context-table lookup.

`perf annotate` could not read the root-owned perf data in this session, so
this record intentionally does not claim instruction-level attribution.

## Source audit

`rust/cix-native/src/ppm.rs` has two allocation-heavy mechanisms:

1. `context` at lines 15--21 copies every looked-up history suffix into a
   `Vec<u8>`. Read-only paths in `prime_see`, fixed/secondary encode,
   estimation and both decoders use it for `HashMap<Vec<u8>, _>::get`.
2. `eligible` at lines 23--28 allocates a filtered `Vec<(u8, u32)>` for every
   tested context. Fixed PPM then computes mass, escape statistics and symbol
   position from that temporary in `encode_fixed_from_state` (lines 309--371).

The current code deliberately keeps count vectors sorted by symbol and applies
excluded-symbol filtering in that order. Any replacement must retain that
order, mass, escape method, arithmetic intervals, update order, rescaling, and
the canonical winner tie order.

## Smallest proposed exact-semantics change

**Owner:** `rust/cix-native/src/ppm.rs` only.

First evaluate borrowed context lookup. Change the lookup helper to return a
history slice, and call `tables.get::<[u8]>(suffix)` instead of allocating a
`Vec` before every lookup. In `observe_from`, allocate `suffix.to_vec()` only
when inserting a previously unseen key; use a mutable borrowed lookup when the
key already exists. `Vec<u8>` implements `Borrow<[u8]>`, so this uses the
same bytes and the same `HashMap` hash/equality semantics as the present key.
It does not alter serialized data or selection policy.

If profiling still shows `ppm::eligible`, evaluate a second, independent
fixed-encoder-only patch: replace its temporary eligible vector with one
ordered scan that returns total mass, number of eligible symbols, singleton
count and the hit interval for the current symbol. On escape, make the same
ordered scan to set exclusions. This exactly reproduces escape methods 0--3
and interval arithmetic while removing the temporary allocation. Do not apply
it to SEE or decode until the borrowed-context result is qualified.

## Qualification plan after benchmark CPUs are released

1. Establish an AB/BA three-run release-LTO micro/end-to-end PPM fixed-route
   control on CPU 18, then record wall/CPU/RSS and archive SHA-256.
2. Require byte identity for deterministic PPM v3/v4 fixed payloads, fresh
   old/new native cross-decoding, malformed-input regression checks and the
   existing PPM tests.
3. Measure allocation counts/bytes with the audit's supported allocation
   profiler or DHAT; retain the change only if the measured reduction survives
   a held-out CCA input and complete DEFAULT output size remains unchanged.
4. Keep the feature out of route-selection changes. BWT and BigUint remain
   separate measured tracks.

No production source or benchmark dispatch was performed by this investigation.
