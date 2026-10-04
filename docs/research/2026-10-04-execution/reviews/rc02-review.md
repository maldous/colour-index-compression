# RC02 extraction review

**Review scope:** static, read-only inspection of the current native source.
No build, test, codec, benchmark, or ABI-consumer run was performed for this
review.

## Finding: RC02 is not yet satisfied

`core.rs` supplies a useful process-free *facade*: `NativeOptions` is
caller-owned, `encode` and `decode` use `Read`/`Write`, and the limited writer
enforces its supplied output limit. `limits::LibraryGuard` also prevents the
CLI Ctrl-C flag from becoming an implicit library cancellation input. These are
good ingredients, but they do not establish the required library-first
boundary.

The library exposes `core::engine` as `pub`, and that module is the former CLI
implementation. It imports `std::env`, `std::fs::{File, OpenOptions}`, and
`std::process::{self, Command, Stdio}` at
`rust/cix-native/src/engine.rs:4-11`. It contains argument parsing, help and
diagnostic printing, file opening and atomic output replacement, `process::exit`
in `main_entry`, Ctrl-C handler installation, and `portfolio_cix_candidate`,
which uses `current_exe` and spawns a child CIX process. `core.rs` currently
exports that module and re-exports its `main_entry` and
`cix_squash_splice` (`core.rs:13-17`). `lib.rs` in turn exposes `main_entry`
and dispatches the PAQ worker through `std::env::args_os` and
`std::process::exit` (`lib.rs:9-16`).

This fails the RC02 acceptance boundary: native embedding can reach a public
module containing CLI/environment/filesystem/process behavior, and the
purported engine is not extracted from CLI behavior. The existing
`tests/native_context.rs` exercises buffers, limits and cancellation only. It
does not prove a C ABI consumer, absence of implicit children, or absence of
CLI side effects.

## Minimal corrective direction

1. Make a private, side-effect-free codec/container module the implementation
   target of `core::{encode,decode}`. It may use caller-provided `Read`/`Write`,
   options, time/cancellation context and explicit library callbacks; it must
   not import environment, filesystem, process, signal, stdout/stderr, or CLI
   option types.
2. Move `Opt`, parsing/help/version, `open_input`, file/atomic-output handling,
   stdout diagnostics, Ctrl-C setup, `run`, `main_entry`, and
   `portfolio_cix_candidate` to a private CLI adapter module. The binary alone
   calls that adapter. Keep same-CIX process isolation behind the full-engine
   job/supervisor interface, never on the native SDK encode/decode path.
3. Do not publicly export the CLI adapter through `core`, `codec`, or the crate
   root. Retain compatibility exports only for codec primitives that do not
   pull CLI behavior into their API contract.
4. Add the required focused evidence after the split: a Rust embedding test and
   C ABI consumer test that use buffer/stream APIs, exercise typed limits and
   cancellation, and establish that neither performs process exit, signal
   installation, unsolicited output, resource-limit writes, nor child spawn.
   A static forbidden-import check for the SDK module is a useful complement,
   not a substitute for those tests.

## Additional boundary issue to preserve in the follow-up

The core facade passes `engine::EncodeOptions`, which still carries CLI-oriented
fields (`input_fd`, `explain`, `verbose`, string route/backend/format fields).
The split should replace this with a typed native request or keep the adapter
translation entirely outside the SDK. This prevents later SDK calls from
quietly inheriting poll-on-file-descriptor or diagnostic semantics.

## PAQ supervisor

`paq_supervisor.rs` appeared during this review. Static inspection finds a
sound intended isolation shape: it names an absolute CIX executable, clears
the worker environment, starts the versioned internal worker switch rather
than an upstream executable or shell, drains both diagnostic pipes, checks the
result size, and kills/reaps its direct worker on cancellation or deadline.
`paq_worker.rs` applies Linux address-space and file-size limits before loading
the private bridge.

It must be a **private full-engine supervisor only**, never part of the native
SDK surface. Its public request permits any absolute executable and temporary
root, while `run` launches that executable and writes beneath that root. The
full-engine adapter therefore needs to supply a validated installed-CIX path
and a CIX-owned private temporary root; neither may be caller-controlled by an
embedding API. This is also needed to substantiate the “same-CIX worker”
claim.

Two bounded-resource details still need resolution before acceptance:

1. The supervisor reads a successful temporary output into a `Vec` after only
   checking `output_limit_bytes`. That value may be much larger than memory
   admitted for the parent. Add an explicit parent/result-memory reservation or
   stream the result through a bounded caller-owned sink; account for it in the
   full-engine scheduler.
2. `TemporaryOutput::create` uses predictable time/PID/counter names under any
   directory accepted by `is_dir`. Restrict the root to a private
   installation-owned directory (and reject an unsafe/symlinked root), or use
   a secure directory-creation primitive supplied by the platform adapter.
   The current check alone does not establish that a shared `/tmp` root is safe.

No process test, rlimit test, cancellation test, or PAQ invocation was run for
this review. The existing worker-only declaration in `paq_bridge.rs` is
necessary, but it does not remedy the `engine.rs` child-process path above.

## C API and JXL-provider follow-up review

**Method:** static source inspection only. Source comments and small Rust mock
tests are not ABI, library-loading, allocation-limit, archive-compatibility, or
cross-platform qualification evidence.

### C API

The recent C API repairs correctly avoid splitting a UTF-8 diagnostic, read the
options prefix before a complete-struct read, and reject overlapping input,
output and `needed` ranges. The buffer operation copies only after it knows the
caller buffer is large enough.

Two lifetime/embedding conditions remain to be made explicit or enforced:

1. `cix_context_destroy` can free the opaque `Box` while a separate foreign
   thread is executing a buffer call or `last_error` with the same context
   pointer. The internal mutex serializes operations but does not retain the
   allocation through destruction. Either document destruction as externally
   serialized after all calls have returned, or introduce a closing/refcount
   protocol. Do not claim concurrent destroy safety as written.
2. `catch_unwind` maps an unwind to a status, but Rust's process-global panic
   hook normally runs before that catch returns. A panic may therefore still
   emit to stderr. Prevent panics on the reachable ABI path and qualify the
   no-unsolicited-output claim; swapping the global hook per call is not a
   safe concurrent library remedy.

The installed C header and an independently built C consumer must establish
the opaque context lifetime rule, null-plus-zero buffers, options version and
trailing-size handling, no output write on too-small output, alias rejection,
error NUL sizing, and context ownership. A normal C function necessarily
relies on the caller to provide writable storage to `cix_options_v1_default`;
the header must say so.

The updated header documents the externally serialized destruction rule and
the installed-consumer harness covers the listed ordinary C cases. A transient
status-enum mismatch was corrected during review: the implementation now maps
context output-limit exhaustion to the header's resource-limit status. This
requires the scheduled installed-consumer run before it becomes acceptance
evidence.

### JXL provider and native LZMA

The provider's bridge interface has useful checks: it loads an explicit
absolute path, validates the pinned JXL version, probes paid pixel count before
the raw JXL output buffer, validates geometry again after decode, and checks
exact XZ input consumption and decompressed length.

It is not yet a bounded, portable image-provider acceptance:

1. `lzma_decompress_exact` checks `input + expected <= memory`, but passes the
   full `memory` as liblzma's separate internal allocation limit. Its total
   residency can therefore exceed the caller budget by the decoder state. Pass
   the remaining internal budget, or define and reserve an explicit combined
   estimate.
2. `lzma_compress_preset_9` accepts no resource ceiling and directly calls
   `Vec::with_capacity(lzma_stream_buffer_bound(input.len()))`. A large valid
   request can panic or exhaust memory before a typed error. Propagate an
   admitted compression limit and use fallible reservation.
3. The JXL `UINT8` decode path can have the raw `P`-byte plane and newly
   collected `2P` canonical plane live at once, before libjxl's own state. It
   currently admits only `2P <= memory`. Encoding also temporarily holds the
   C++ vector, bridge allocation and Rust copy of the output. Account for those
   simultaneous allocations before calling either bridge function.
4. This provider accepts only `depth == 1` and non-planar input. It cannot yet
   serve all retained CIXV1/CIXI2 multi-slice calls allowed by `ImageBackend`.
   It is a scoped 2-D provider, not image-route parity.
5. The native LZMA declaration uses `#[link(name = "lzma")]` without a target
   gate, whereas dynamic bridge loading is Linux-only. Once the module is
   wired, a non-Linux build can fail despite the non-Linux loader stub. Provide
   a platform implementation or explicit supported-target configuration.
6. The Linux `dlsym` helper is generic and uses `transmute_copy` from `void*`
   to arbitrary `T`. Keep that conversion limited to same-size declared
   function-pointer aliases (or assert size) rather than exposing an unsound
   generic conversion pattern.

No actual JXL bridge, native LZMA, malformed archive, memory-limit, or
cross-platform test was run in this review.

### PAQ supervisor update

The later supervisor revision adds a caller-reserved result limit with a
fallible reservation and validates a Unix private temporary root plus its
ancestors before `mkdir(0700)`. That addresses the two earlier structural
findings. At the time of this static read, `read_result` has a compile-time
struct-literal error: `PaqSupervisorError::OutputTooLarge` supplies `limit`
twice. Remove the duplicate field before scheduling checks. The revised source
still needs actual worker, cancellation, resource-limit and cleanup evidence.

## Follow-up: core boundary and specialist decoder review

**Method:** a later static, read-only pass over the current source. No build,
test, codec, benchmark, or SDK-consumer run was performed.

### Core boundary

The earlier public `core::engine` exposure and direct CLI-option dependency are
no longer present in the inspected `core.rs`: `engine` is crate-private, and
the public buffer/stream API supplies fixed `explain=false`, `verbose=false`,
`list=false`, and a `LibraryGuard`. The remaining `engine.rs` diagnostics are
guarded by those flags; its memory-budget diagnostic also checks that it is
outside library scope. I did not find a demonstrated reachable unsolicited
output path from `core::{encode,decode}` in this static pass. `engine.rs`
remains a broad internal implementation dependency, so the required embedding
and installed C-consumer tests remain necessary behavioral evidence; source
structure alone cannot prove the absence of later side effects.

### SDFG/SDFH exactness and bounds

`graph_residuals.rs` retains the historical `SDFG\x01` and `SDFH\x01` raw
formats, parses record flags before using transformed coordinate state, and
keeps unsupported records as skeleton literals. Its reconstruction validates
the skeleton-derived record/atom count and computes the bounded reconstructed
size before allocating coordinate vectors. Coordinate arithmetic in restore
and the hydrogen path uses checked operations at the reconstructed-value
boundaries. The palette decoder derives each stream length from the validated
skeleton atom groups and rejects unused tokens or residual state. I found no
specific malformed-frame path that silently changes a literal record in this
static read.

The result is source-level parity evidence only. The raw-vector fixtures and
scheduled real backend qualification, rather than this review, establish
historical byte compatibility.

### MYCS/MYCC and SAGR/CIXS admission finding

There is a material resource-bound gap shared by the record and grid physical
frame wrappers. `record_ordering::unpack` admits `n <= memory`, passes the
whole `memory` allowance to the backend, retains the returned transformed
`Vec`, and then invokes an inverse that can materialize a separate output of
up to `n`. `strided_values::{decode_wcs_grid_transpose,decode_wcs_grid}` use
the same pattern. Consequently a backend-valid member can keep transformed
data live while inverse reconstruction allocates output, exceeding the
caller-supplied memory value before any final check.

The outer declared length is also verified only after inverse reconstruction.
For example, SAGR numeric inverse reads its raw `records` count and allocates
the record matrix before the CIXS outer `length`/checksum is verified. MYCS and
MYCC similarly rebuild literal/column output before `verify_frame`. A malformed
but backend-valid raw stream can therefore demand reconstruction that is
inconsistent with the outer declared length; rejecting it after allocation is
too late.

The minimal correction is to pass an expected-output and combined-live-memory
budget into each inverse. Validate the raw shape and a checked reconstruction
size before allocating, reserve output plus transform/backend state in one
plan, and pass only the residual backend budget to the expansion callback.
This may require an explicit larger route admission where a legitimate
historical transform expands before inverse; it must be an accounted policy,
not an implicit overage. Existing raw transform functions can remain
byte-compatible when their bounded decode wrappers gain those arguments.

The MYCS/MYCC fixed-column fallback retains the original column as a nested
literal (`0 || original-column`) and rewraps it during inverse, matching the
Python reference's paid literal behavior. The SAGR inverse rejects an unknown
mode, tail, malformed declared extent, and post-reconstruction non-WCSTools
shape. Those correctness checks do not substitute for the pre-allocation
combined resource check above.
