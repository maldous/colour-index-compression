# PPM rescale ceiling cleanup

## Change

`rust/cix-native/src/ppm.rs` replaces exactly three positive-count ceiling
halving expressions, `((x + 1) / 2).max(1)`, with `x.div_ceil(2).max(1)`:
one PPM model-count rescale and the two SEE state-count rescales. The change
does not alter payload framing, candidate selection, or context lookup.

## Pre-change fixture capture

Before applying the source change, the deterministic 20,000-byte fixture in
the PPM unit test was encoded from source revision `4e179a4ba`. Its v3 fixed,
v4 fixed, and v5 SEE outputs, including lengths and SHA-256 values, are in
`fixtures.json`. The post-change test checks those values and independently
restores each payload through `decode`.

## Focused verification

The PPM unit tests cover all ordinary model counts from 0 through 32768,
a wide `u64` oracle at the `u32` upper boundary, and the actual PPM and SEE
rescale transitions. They also retain malformed payload rejection checks.

Run with one Cargo job and CPU 15:

```sh
CARGO_BUILD_JOBS=1 taskset -c 15 cargo test --lib ppm::tests -- --nocapture
```
