# Final local Sonar and Clippy inventory — 0c6028

Frozen source is `0c6028e39fedb3f659bf5985ea0b16cb4ed1b58d`, tree
`314f7df6512da1436799c592ae3ce629fe57e8d2`. A clean local full clone at that
commit was scanned over unchanged source, examples, tests and benchmark paths;
82 files were indexed. The Clippy command used stable Rust, all targets and all
features, under CPU 24–25, 1 GiB and zero swap. It exited zero and its complete
423-line Cargo JSON is retained. It contains zero Clippy warning messages, so the
compact external importer report is empty and there are no importer drops.

The scanner ran in its own CPU 24–25, 1 GiB, zero-swap cgroup; it uploaded
successfully with the exact SCM revision. Current open Sonar findings are two
native `rust:S3776` issues. This is a local static-analysis inventory, not a
performance or codec qualification result. No source exclusions, suppressions,
or workflow changes were made.
