# Same-CIX PAQ worker checkpoint

`src/paq_worker.rs` is private to the CIX library crate and reached only by
`main_entry`, before ordinary CLI signal handlers or threads are created.
The process-free SDK does not launch or expose this worker. This checkpoint
implements the child codec invocation; it does not yet implement the full-engine
parent supervisor, candidate admission, cancellation/progress protocol or RC23.

The versioned internal CLI control is `--internal-paq-worker-v1`, followed by
variant, encode/decode, absolute package library directory, absolute input,
absolute output, memory bytes, output bytes, level, LSTM layers and joint mode.
Paths are separate native arguments, never shell commands. Level is `-0` through
`-12` with optional `L`; LSTM layers are 1 through 5; joint mode is `none` or
0 through 3 only for the joint-discount variant. Unsupported platform/CPU
profiles fail explicitly. The present qualification is Linux x86-64 AVX2 only.
Higher levels and LSTM options are parsed but not qualified by this tiny test.
No external learned-state file, arbitrary upstream option or hidden executable
fallback is admitted by this interface.

The worker validates paths and output nonexistence, including dangling symlinks.
Upstream PAQ rewrites backslashes and interprets a trailing slash as a directory,
so those file paths are rejected. Extensionless files are valid and tested.
Before loading the exact packaged DSO, the worker clears inherited environment
entries and installs locale, one-thread and explicit joint-mode settings. It
sets non-increasing Linux address-space and file-size limits. Its parent must
still launch with a clean environment: this child-side cleanup cannot undo
loader initialization that occurred before the executable's entry point.

Each DSO is an ordinary file with its distinct variant name. The loader checks
the exact CIX bridge ABI/variant string and process symbol, retains the handle
through the call, and loads no PATH executable, Python runtime or wheel library.
The CIX bridge enforces one call per process. PAQ stdout/stderr remain diagnostic
streams. File-size limit failures terminate the dedicated child with SIGXFSZ;
the parent must map this to a typed failure and remove its temporary output.
These per-child limits do not substitute for aggregate product scheduling.

## Evidence

- Each of v215, v216, joint-discount and store-state built from its unchanged
  frozen source and passed eight C ABI/reference checks. Their exports contain
  exactly the two expected CIX ABI symbols.
- `jobs/paq-cix-worker-v1` compiled and passed four unit checks, then failed its
  first encode: CIX emitted `-lstmlayers` for a non-LSTM run. The failed logs and
  source remain preserved. Emission now occurs only for LSTM encoding; decoding
  reads its layer configuration from the archive.
- `jobs/paq-cix-worker-v2` passed all-target compilation, four worker unit checks
  and 35 fresh-process cases through the compiled CIX executable. Each variant
  produced the reference archive exactly; both directions of cross-decoding
  restored the generated 2,112-byte fixture exactly. Overwrite/symlink rejection,
  inherited research-setting removal, output limits, insufficient memory,
  path rejection and ordinary CLI version dispatch were checked.

This is a debug CIX build with Release PAQ libraries, level 1, without LSTM.
It is component/integration evidence, not an optimized RC, benchmark, all-mode
parity proof or distribution claim. No upstream source was edited. The existing
standalone reference executables were test controls only and are not product
runtime dependencies of the new worker.
