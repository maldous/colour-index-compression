# Final BD2 local Rust Sonar and Clippy inventory

Source is `bd2a0d97bb4bc5847b55113341ad8de94c269c7f`, tree
`73f6fefbe22fdeff0a2fe49d9a9251e4e25cc7ae`, scanned from a clean local clone.
The unchanged scope is native Rust source, examples, tests and benches; the scanner
indexed 82 files and recorded the exact SCM revision.

Stable Rust Clippy ran all targets and features under CPU 24–25, 1 GiB memory and
zero swap. Its complete 439-line Cargo JSON and compiler stderr are retained. It
contains zero Clippy warnings, so the compact importer report is empty and there
are no importer drops.

The local scanner ran under CPU 24–25, 1 GiB and zero swap; its compute-engine task
succeeded. The raw `resolved=false` API response has zero issues. Sonar reports one
separate notice that a C++ file is outside this edition’s analysis capability. This
packet records Rust static analysis only and makes no claim about unanalyzed C++ or
non-Rust project content.
