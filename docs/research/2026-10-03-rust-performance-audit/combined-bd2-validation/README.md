# Combined BD2 native release validation

Exact detached source revision `bd2a0d97bb4bc5847b55113341ad8de94c269c7f`, tree
`73f6fefbe22fdeff0a2fe49d9a9251e4e25cc7ae`, was built and tested locally
with stable Rust 1.98.1, CPUs 10 and 11, a 2 GiB cgroup memory maximum, and
zero cgroup swap allowance. The evidence packet binds the locked all-feature
release-LTO build, the serialized suite, separate Criterion smoke test, actual
child membership and affinity observations, the resulting binaries, and their
native release metadata.

The complete readonly binaries and the byte-identical raw metadata are in
`benchmark-work/combined-bd2-validation/final/`. `raw/manifest.sha256` seals
the raw receipts after collection.
