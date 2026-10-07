# Compiler build matrix

This is a bounded, matched local compiler-setting audit for source revision
`15426f310f40b9a3d753313741c28e718f7aceb6`. It isolates code generation from
the selector by pinning CIX itself to one thread and pins each process to CPUs
20 and 22. It runs only cached Canterbury inputs, retains no corpus copies,
uses a 2 GB address-space limit, and refuses a build directory over 1 GB.

The screening matrix compares opt-level 2/3, no LTO, ThinLTO and fat LTO,
codegen units 1/16, and portable `x86-64` against `target-cpu=native`.
Compile time and executable size are recorded separately from runtime.
For each generated executable it runs five counterbalanced repetitions of
ordinary FAST, ordinary DEFAULT, and a clearly labelled BEST constrained to
`CIXG1/LZ`. Archives are complete output streams. Every result is decoded by
its owning build and every build in the matrix; hashes must match the input.

Run locally:

```sh
python3 docs/research/2026-10-02-rust-performance-audit/build-matrix/run.py --run
```

The harness writes `freeze.json` before doing work and `results.json` only if
all builds, repetitions, and cross-decodes succeed. It does not collect
Silesia, download inputs, alter production sources, launch Actions, or assert
that any compiler configuration wins before variance is examined.

PGO is intentionally not started by `--run`: it needs a separately frozen,
disjoint CCA training/evaluation split. Rust's matching LLVM 22 `llvm-profdata`
is already installed. Once the split is reviewed, build a profile-generate
portable candidate, train only on the declared development inputs, merge with
that exact tool, build with `-Cprofile-use=…`, then run the held-out inputs
through the same five-repetition and cross-decoding procedure. A PGO result
without that split is unqualified.

`run-pgo.py` is the executed version of that disjoint experiment. It trains
only on cached `alice29.txt` and `book1`, then evaluates the three held-out
workloads five times against a portable fat-LTO baseline. See `RESULTS.md` for
its bounded conclusions.
