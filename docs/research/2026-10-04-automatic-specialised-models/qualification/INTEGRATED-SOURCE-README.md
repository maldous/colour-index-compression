# CIX integrated qualification source snapshot

This is the frozen source layout for the Linux qualification release candidate.
It combines the native CIX command-line implementation with the maintained
Python runtime and the retained native backends needed for automatic,
input-derived specialised selection. It is private qualification material, not
a public release or portable installer.

The staged `cix`, `uncix`, and `cixcat` commands are the ordinary interface.
They accept arbitrary bytes, retain a generic fallback, and automatically
consider eligible specialised representations from the supplied input. They do
not consult corpus names, paths, hashes, saved archives, or result records.

`cix --fast` prioritises latency, the default policy is balanced, and
`cix --best` evaluates a broader bounded set of eligible candidates. All three
write self-describing archives; `uncix` and `cixcat` restore them. Resource,
time, and candidate limits for qualification are fixed by the accompanying
release-control record, not selected from a dataset.

## Layout

- `native/` — the current native CIX source candidate, including its Cargo
  lockfile, build support, manuals, package recipes, licence, and notices.
- `runtime/` — maintained runtime package, staging tool, focused tests, and
  backend provenance. It contains no benchmark scheduler, corpus, saved stream,
  or result certificate.
- `vendor/paq/` — retained source copies for PAQ v215, v216, joint-discount,
  and store-state backends used by this candidate.
- Root licence and third-party notices — distribution and attribution material
  for the snapshot and its retained components.

## Qualification staging

The current staging tool constructs a host-pinned Linux closure from the
qualification development host. It stages the frozen native executables, the
four retained PAQ binaries, and the installed Python 3.12 runtime dependencies
required by the enabled routes, including NumPy, imagecodecs/JXL, and Brotli.
It is intended for the controlled qualification environment only.

A native Cargo build by itself produces the native CIX utilities; it does not
install the integrated Python runtime, PAQ backends, or their staged dependency
closure. The staging receipt records the selected files and hashes. Run the
focused validation and the frozen qualification harness before treating a
staged tree as a release candidate.

## Limits of this snapshot

This snapshot does not claim a portable source build, distribution package,
Windows or macOS binary, or public-installation procedure for the integrated
runtime. Those require a separately qualified dependency closure, platform
build recipes, licence review, and package installation tests.

Research documentation, source datasets, benchmark orchestration, cached
outputs, and result certificates are deliberately excluded. This snapshot also
makes no public compression-rank or Silesia performance claim until its frozen
one-pass qualification has completed.
