# PAQ supervisor integration receipt

`rust/cix-native/src/paq_supervisor.rs` is the parent-side implementation for
the established `--internal-paq-worker-v1` contract. It is intentionally not
wired into `lib.rs`, the CLI, or candidate selection by this change; the root
integration task owns that scope and aggregate scheduling.

The module accepts only an explicit absolute CIX executable, private packaged
library directory, temporary root and input path. It launches the current CIX
executable using native argument boundaries, with a cleared environment and
only explicit locale/thread/joint settings. It never invokes a shell, Python,
PATH lookup, or standalone PAQ executable.

Per-call validation covers input size, output/memory signed-64-bit limits,
levels, layers, joint modes and cancellation/deadline state. A separate
`parent_result_limit_bytes` caps the returned allocation; the full-engine
scheduler must reserve that result memory together with child memory and both
diagnostic captures before invocation. The supervisor never reads more than
that charged result bound.

The temporary root must be an absolute Unix directory owned by the effective
user, mode 0700, with no symlink and no group/other-writable or untrusted-owner
ancestor. Generic `/tmp` is deliberately rejected. Each worker receives a new
0700 directory created with the native `mkdir` mode, so the output pathname
does not exist when handed to the worker and cannot be raced by another user.
The parent drains both worker diagnostic pipes in parallel with bounded retained
transcripts, and kills plus reaps a child on cancellation, expiry, error or
supervisor drop. The temporary directory is removed on success and failure.
Aggregate worker admission, aggregate memory reservations and scheduling remain
the full-engine caller's responsibility.

Focused checks are embedded beside the module:

- closed PAQ level/variant arguments;
- bounded diagnostic capture that drains beyond its retained cap;
- private temporary-output cleanup plus symlink rejection;
- result-memory cap before a returned-output allocation.

The module also contains one opt-in parent lifecycle test. It remains inactive
when all of these test-only variables are absent, and fails rather than skips
when any supplied path is invalid or the variables are incomplete:

```text
CIX_TEST_EXECUTABLE=/absolute/path/to/fresh/cix
CIX_TEST_PAQ_LIBDIR=/absolute/path/to/staged/private-libraries
CIX_TEST_PAQ_WORKROOT=/absolute/path/to/owned-mode-0700-work-root
```

When staged by root, it encodes a deterministic 2,112-byte source and decodes
the returned archive in a fresh worker for v215, v216, joint-discount and
store-state. It also exercises a one-byte output-cap failure, cancellation
before launch, expired deadline cleanup and no leftover worker directories.
These variables are read only from `cfg(test)` code and cannot influence a
product supervisor request.

Root should add the module to the crate, then schedule focused checks including
`cargo test --lib paq_supervisor` with the three staged variables above. No
benchmark or PAQ qualification run is implied here.
