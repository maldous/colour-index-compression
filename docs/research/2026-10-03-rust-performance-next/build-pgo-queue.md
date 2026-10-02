# Build and PGO screening queue

Nonexecuting queue after final validation. The prior `build-matrix` receipt is
for `15426f310`, so it is historical screening only. It does not qualify a
winner for the final source.

## Freeze before screening

- Record final and `99f4f7319` source hashes, dirty-tree absence, Rust/Cargo/
  LLVM versions, Cargo.lock hash, C/C++ compiler flags, CPU governor/model,
  resolved DSOs, cgroup CPU/memory/swap limits and exact fixture hashes.
- Build each arm from a clean detached worktree with the same lockfile and
  target directory policy. Record compile wall/CPU/memory, binary hashes and
  executable bytes separately from runtime results.
- Pin CIX policy to identical flags, one encoder thread, block size, memory,
  format, route override state, history and independent-block state. A build
  setting is implementation-only only when complete archive bytes match. Any
  route, selection, block, history or framing change is a policy experiment and
  needs a separate matrix.

## Phased matrix

1. Portable baseline: opt-level 2 and 3, no LTO, codegen-units 16 and 1.
2. At the winning portable opt/codegen point, compare ThinLTO and fat LTO.
3. Compare the retained portable winner with `target-cpu=native`; retain it
   only as a host-specific artifact, retaining portable deployment builds.
4. Train PGO only after hashing a disjoint frozen CCA development split;
   evaluate only frozen held-out CCA fixtures. The existing 15426 plan trained
   Alice29 and Calgary book1 and held out Kennedy/grammar; recreate a new
   split identity for final source rather than silently reusing its conclusion.

Illustrative build environment, after a cgroup lease:

```sh
CARGO_BUILD_JOBS=2 RUSTFLAGS='-C opt-level=3 -C lto=thin -C codegen-units=1 -C target-cpu=x86-64' \
  cargo build --locked --manifest-path rust/cix-native/Cargo.toml --profile release-lto --bin cix --bin uncix
# PGO: build -Cprofile-generate=DIR; run only declared development fixtures;
# LLVM_PROFDATA merge; rebuild -Cprofile-use=MERGED; evaluate held-out fixtures.
```

The exact `RUSTFLAGS` must be frozen in the generated manifest; Cargo profile
`release-lto` presently implies fat LTO/codegen-units=1, so use a separately
named target/build invocation for no-LTO or ThinLTO rather than claiming this
example changes that profile automatically.

## Required qualification

For every cell: five counterbalanced encode/decode repetitions, complete
archive bytes and SHA, own and fresh cross-native decode hashes, wall/user/sys
time, peak RSS and cgroup high water. Reject cells on changed output, missing
receipt, limit breach, or fixture mismatch. This queue neither runs builds nor
authorizes CCA/Silesia execution.
