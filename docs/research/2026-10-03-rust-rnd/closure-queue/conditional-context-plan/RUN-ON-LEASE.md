# COND-CONTEXT-1 lease recipe

This is a preparation record only. Do not run it without root's scheduler
lease and a sealed release build. It does not modify Cargo manifests or CIX
production formats.

Compile the unregistered driver against the sealed native rlib. The lease
holder supplies exact paths for the rlib and its two direct BigUint
dependencies, then records their SHA-256 values in the execution receipt.

```sh
rustc --edition=2021 \
  rust/cix-native/experiments/conditional-context-closure/conditional_context_closure.rs \
  --extern cix_native="$RLIB" \
  --extern num_bigint="$NUM_BIGINT_RLIB" \
  --extern num_traits="$NUM_TRAITS_RLIB" \
  -L dependency="$DEPS" \
  -o "$DRIVER"
```

First materialize `strong`, `weak`, and `absent` once with `generate`, SHA-256
each input and compare it to the generator/driver binding in `freeze.json`.
This step is outside timing and does not substitute an input after the freeze.

For each of the 12 `CASE x {global, context-1-4, context-2-8, raw}` rows,
run exactly one timed `encode` and one timed, newly started `decode`. Retain
the archive, restored bytes, both SHA-256 values, JSON emitted by the driver,
GNU Time receipt, cgroup read-back and temporary-storage high water. The
`best` command is a deterministic finite-selector smoke path and must be
reported separately if scheduled; it is not a substitute for the four matched
candidate rows.

Malformed checks use copies of a completed archive and `reject`; at minimum
check header mutation and truncation. They must not write a restored output.

The decoder starts a fresh process but links the same sealed native rank rlib;
it is archive-only process separation, not an independently reimplemented
rank decoder.
