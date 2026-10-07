# One CIX executable with integrated codec libraries

Status: release requirement accepted; user has stopped the benchmark to complete
the full RC source requirements first. Reconcile this provisional integration
approach with the coordinating acceptance ledger and SDK planning handoff before
implementation. This is a bounded design, not a claim that the proposed libraries
already build or pass. No new benchmark starts until the consolidated RC gate.

The coordinator verified the actual initial user message in task
`01a0f409-8b61-7eb3-9be6-0b7bd3817f94` ("Port CIX tools to Rust"):
"Implement the encoder, decoder, framing, checksums, selectors and supported
compression routes in Rust" and "The finished binaries must run without Python
or a Python subprocess." The earlier embedded-CPython
suggestion was an architectural inference, not user approval; it is withdrawn
from the proposed shipping design. A single executable does not waive the
no-Python runtime requirement. Python may remain reference/test tooling. The
ledger must map every successful Python specialist to native/library parity,
without dropping routes or presenting incomplete coverage as a finished RC.

The full-engine process-isolated design below is not itself a side-effect-free
native SDK. The SDK requires reusable contexts, explicit capabilities/resources
and error semantics, with no implicit subprocesses, global signal handlers,
process exits, resource-limit writes or unsolicited output in native embedding.
Provide separate explicit native and full-engine capability profiles; do not
claim that an embedded interpreter or a process API alone satisfies both.

The user's clarification is: **one CIX executable; integrated codec libraries
are acceptable**. Retain the successful specialists and codec implementations.
Keep their names, provenance and licenses visible. Changing a backend's filename,
hiding its process or extracting a separate program at runtime is insufficient.

## Current implementation and qualification boundary

The staged `bin/cix`, `bin/uncix` and `bin/cixcat` are shell launchers for Python
`cix_runtime.cli`. The runtime selects complete fresh-input archives and launches
native CIX and PAQ executables from `libexec/cix`. NumPy, imagecodecs/JXL and Brotli
are additional library dependencies. See maintained `runtime/tools/stage_runtime.py`
lines 45–60 and `runtime/cix_runtime/backends.py` lines 128–160 and 170–204.

This arrangement fails the new executable-packaging target. It does not invalidate
the measured archive sizes or exact-restoration receipts for its frozen identity.
Future executable integration requires separate correctness and dependency proof;
it cannot inherit a claim that its own timings or installation were measured here.

## Proposed first implementation

1. Build a compiled CIX host. Link the existing native Rust engine as a library,
   with CIX-owned argument/stream adapters. The native crate already emits rlib
   and cdylib artifacts. Remove the separate native CIX executable dependency.
2. Compile each required, unchanged PAQ source snapshot as a private codec library
   using a CIX-owned build recipe and narrow C ABI bridge. PAQ v215 exposes
   `processCommandLine(int, char**)` in `src/paq8px.cpp:421`; its executable `main`
   at line 1191 is a wrapper. A build-only rename of that otherwise unused entry
   point avoids a main-symbol collision without editing vendor bytes. Verify the
   analogous entry points in every retained variant before implementation.
3. Export only the CIX bridge and isolate private C++ symbols across PAQ variants.
   Preserve validated optimization/SIMD/floating-point flags. PIC, symbol binding,
   exception handling and library lifetime are actual prototype questions, not
   assumed equivalence. Never relax floating-point reproducibility to obtain a
   build. CIX's native ZPAQ/libbsc bindings remain separately attributed.
4. Preserve process isolation for global-state codecs and bounded candidate work.
   If a fresh process is needed, launch the same CIX executable in an internal
   worker mode and call its codec library bridge. That is multiple CIX processes,
   not a separate third-party compressor program. Keep exit/timeout/descendant,
   memory, output-size and temporary-space enforcement effective.
5. Map the 41 maintained Python modules and their qualified behavior to reusable
   native Rust/CIX-owned adapters and integrated codec library calls. Reuse
   already native algorithms where byte/state equivalence is demonstrated;
   translate remaining recognizers, transforms, framing, selection and decoding
   in bounded owned groups. Keep Python implementations as reference/test oracles,
   with golden fixtures and cross-decoding. Remove Python and its bindings from
   shipping execution, replacing imagecodecs/JXL and Brotli calls with native
   library interfaces. Retain archive metadata, exact arithmetic, canonical codec
   arguments, all successful specialists and historical decoding. Scope and file
   ownership must come from the consolidated ledger before this substantial work.

Compiler visibility controls can restrict exported symbols, but correctness of
this particular multi-variant integration must be demonstrated:
[official GCC code-generation options](https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html).

## Limitations to resolve explicitly

One executable does not mean one static file. Native codec libraries and required
runtime data remain explicit dependencies. Report installed size, supported
versions, discovery/loading rules and source-build recipe. The no-Python parity
work is substantial and must have an explicit per-model completion ledger;
the smaller executable-wrapper change alone cannot satisfy this RC.

The current worker implementation uses Linux fork, RLIMIT and procfs behavior.
Windows/macOS portability requires actual platform adapters and tests. PAQ's
Windows main reparses the operating-system command line; the CIX bridge should
instead supply the codec entry point with its own validated UTF-8 arguments.
Do not claim that passing Linux tests qualifies another platform.

PAQ's adaptive decoding cost remains. Its decoder reproduces bit predictions,
model updates and optional LSTM learning from decoded history. Library packaging
alone is not evidence of a substantial speedup or parallel decode capability.

## Focused qualification and stop conditions

- Inventory installed executable files and trace execution/loading. Only CIX may
  execute as application code; native codec libraries must load through the
  documented CIX interface. No Python interpreter library may ship in the runtime.
  Shell tools, Python, PAQ and separate native CIX
  programs may not be runtime fallbacks. Standard platform runtime loading is
  disclosed separately.
- Verify unchanged third-party source hashes, narrowly scoped CIX-owned changes,
  and full dependency/build identity. Preserve upstream names and notices.
- Exercise every retained archive ID and specialist family on existing focused
  fixtures; compare deterministic bytes, and cross-decode old/new archives in
  both directions. Byte differences require an explanation and new evidence,
  never silent replacement of frozen results.
- Test empty/arbitrary/structured inputs, malformed/truncated streams, bounded
  output/allocation, deliberate worker failure/timeout, cancellation, multiple
  candidates and global-state isolation. Confirm no research paths or cached
  outputs become runtime inputs.
- Record focused encode/decode cost and installed size under the shared scheduler.
  No competing work during the frozen pass. No automatic repeat of the full
  corpus tournament; report any need for further evidence with its exact scope.
- If library integration cannot preserve semantics without modifying vendor
  sources, preserve the failed attempt, identify the narrow CIX-owned alternative
  and report the limitation. Do not delete successful codecs to conceal the gap.

The first executable/library proof should cover the generic PAQ v215 path and
native CIX, then extend the same mechanism to the remaining PAQ variants and
specialist callers. All changes belong to CIX-owned host, bridge, build and test
files. Public distribution, other datasets and Sites remain outside this step.
