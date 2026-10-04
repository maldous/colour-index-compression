# Mandatory PAQ portability design review v2

This is a read-only architecture review. It extends
`docs/research/mandatory-paq-platform-source-v1.md`; it is not evidence of a
build, a runtime launch, a benchmark, or platform qualification.

## Findings from the current CIX boundary

The four mandatory variants are the fixed `PAQ_VARIANTS` list in
`rust/cix-native/src/paq_bridge.rs`: v215, v216, joint-discount, and
store-state. Each is deliberately worker-only. The bridge contract rejects a
native-SDK invocation because upstream state persists for the process lifetime
and documented LSTM paths can terminate that process. This isolation rule must
remain unchanged on every target.

`full_engine::installed` already establishes a suitable same-CIX launch
identity: it canonicalizes an absolute regular executable and passes that
exact path through `TrustedBackendPaths`, without `PATH` lookup. The
supervisor launches that path with `Command`, an explicit argv, cleared
environment, null stdin, bounded diagnostic pipes, and a private output path.
That contract is portable as a *launch identity* and should remain the only
worker executable selection. It must not be replaced with an upstream PAQ
executable, shell command, or `current_exe()` inferred after startup.

The implementation is currently Linux x86-64 only:

* `paq_worker::run` is compiled only there. Other targets return a fixed
  refusal.
* The worker constructs `lib<bridge>.so`, rejects backslashes in input/output
  names, and has its own Linux-only `dlopen` wrapper.
* It forces `-simd AVX2`, performs the x86 AVX2 runtime check, and applies
  `RLIMIT_AS` and `RLIMIT_FSIZE` only on Linux.
* The parent checks cancellation, deadline, and context limits every 10 ms,
  drains each diagnostic pipe with a retaining cap, checks output size before
  allocation, and kills/reaps its direct child. It has no process-group or
  Windows Job Object ownership.

The independent `full_engine::dynamic_library::DynamicLibrary` is usable as a
shared *loader primitive*, subject to a small API adaptation. It accepts only
absolute paths; on Unix it uses `dlopen(..., RTLD_NOW | RTLD_LOCAL)` and on
Windows it uses `LoadLibraryExW` with only the selected DLL directory and
System32 in its dependency search. It also keeps the module handle alive while
symbols are used. Reusing it removes PAQ's duplicate Linux-only loader without
weakening the current explicit-path or handle-lifetime rule.

It is not a drop-in replacement today: PAQ's local loader exposes dynamic
symbol names and string diagnostics, whereas `DynamicLibrary::symbol` accepts
`&'static str` and returns a small error enum. The smallest safe change is to
make PAQ resolve its known static version/process symbols through that common
type and map its errors to the existing worker messages. Do not add a generic
bare-name search, caller-selected dependency directory, or loader fallback.

`paq_bridge::native_c_string` accepts arbitrary Unix filename bytes but on
non-Unix accepts only ASCII representable arguments. Therefore a Windows
worker may use a Unicode executable and DLL path at the Rust loader boundary,
but it must stage PAQ input/output under an ASCII-only private location until
the unchanged narrow-character upstream interface has a separately qualified
Unicode contract. This is an explicit product restriction, not a lossy path
conversion.

## Platform model and implementation slices

Introduce a private, pure `PaqPlatform` descriptor selected at compile time.
It returns the installed bridge filename, the allowed PAQ SIMD argument, and
the child-control implementation. It does not take a user supplied platform,
filename, or SIMD string. `installed::shared_library_filename` already has the
required naming rule: `<name>.dll` on Windows, `lib<name>.dylib` on macOS, and
`lib<name>.so` on other Unix. The worker must use that same single function or
a small common helper, rather than copy it again.

The work can be split without changing wire format or the public SDK:

1. **Path and loader slice.** Move bridge-name derivation to the shared helper;
   retain absolute path, ordinary-file, no-preexisting-output, variant-version,
   and level-zero checks. Replace only PAQ's local `Library` with
   `DynamicLibrary`. Unit-test all three filenames and reject a missing,
   symlinked, mismatched-version, or missing-symbol bridge before invocation.

2. **SIMD admission slice.** Replace unconditional AVX2 argv construction
   with `PaqPlatform::simd() -> Result<SimdProfile, PaqError>`. The descriptor
   records the chosen profile in the worker diagnostic/receipt. x86-64 may
   select AVX2 only after runtime detection. Arm must select an explicitly
   qualified ARM/NEON or non-SIMD profile. No architecture silently receives
   AVX2, and unavailable CPU features fail before `dlopen`.

3. **Child-control slice.** Keep `PaqWorkerRequest` admission, private output,
   pipe draining, deadline/cancellation polling, and atomic cleanup. Put
   target lifecycle/resource controls behind a small private `WorkerChild`
   interface: spawn, poll, terminate-and-reap. Linux keeps its tested rlimits;
   macOS needs a target-specific address-space/file-size policy plus process
   group termination; Windows needs a Job Object that limits the process and
   terminates the assigned job on cancellation/deadline. A direct-child kill
   alone is insufficient as the portability contract because it cannot prove
   descendants are reclaimed.

4. **Target packaging slice.** Keep the current native-only Windows package
   separate. Full-engine staging remains refused until all four target bridges,
   their dependencies, and target loader policy are qualified. The installer
   must stage exactly the descriptor filenames beside the selected CIX
   executable's `lib/cix` layout and prove hashes/architectures; it must not
   reuse the Linux ELF companion list for Mach-O or PE.

## Upstream SIMD facts and compatibility boundary

Pinned joint-discount and store-state source trees contain both a
`build-mingw-w64-generic-publish.cmd` claiming runtime SIMD dispatch for x86/x64
and `build-linux-cross-compile-aarch64.sh` naming Cortex-A73/ARM NEON. Their
source lists include SSE2, AVX2, and Neon mixer files. The pinned CIX bridge
documentation also fixes safe floating-point flags and prohibits
`-march=native`. These are useful upstream/platform indications, but they do
not prove the CIX shared bridges build, load, or decode correctly on a target.

The source facts do **not** establish a common baseline argument for every
variant. In particular, no source review here proves that `-simd NONE`, NEON,
or automatic dispatch is accepted by all four bridge entry points. The first
qualified profile for each `(target, variant)` must therefore be explicit and
fail closed. It must include a decoder matrix: archive produced on x86-64
AVX2, x86-64 baseline, Linux ARM64, macOS x64, macOS ARM64, and Windows x64 is
decoded by every qualified target for that variant. Encoded-byte identity is a
separate assertion and must not be presumed from SIMD selection.

The existing seven-byte level-zero archive rejection remains required for all
profiles. It happens before native loading and must be retained verbatim in
every target implementation.

## Decisive qualification tests

Run these focused tests for every mandatory variant and each target; record
the selected CIX/bridge/source/compiler hashes and test fixture hashes.

| Contract | Decisive test |
| --- | --- |
| Same-CIX launch | Rename the installation directory and use paths containing spaces; confirm the canonical staged CIX executable, not `PATH`, receives the internal switch. |
| Loader | Load the exact staged `.dll`, `.dylib`, or `.so`; reject an absent, symlinked/replaced, wrong-version, and missing-process-symbol bridge before PAQ invocation. On Windows also prove a sibling dependency resolves while a `PATH`/current-directory substitute is ignored. |
| Paths | Exercise Unicode CIX/bridge paths at the Rust loader boundary. On Windows separately prove ASCII staging for PAQ argv, and reject a non-ASCII PAQ work path until a compatible upstream adapter is qualified. |
| SIMD and decoder | For every target/variant profile, encode one small fixture and cross-decode it on every qualified target. Deliberately request an unavailable CPU profile and prove rejection before loading. Preserve level-zero rejection for crafted `paq8px\\0` input. |
| Bounds | Produce output at the limit and one byte above it; prove no result allocation or retained output exceeds the request. Fill stdout and stderr past their caps and prove draining continues without unbounded retention. |
| Lifecycle | Use a controllable bridge fixture that blocks, creates a descendant, or exceeds the configured memory/file-size limit. Cancellation and deadline must terminate and reap the entire worker ownership unit, leave no output, and preserve typed failure. |
| SDK boundary | Invoke PAQ through the native SDK API and prove `NotSdkSafe` before any load/spawn. Then verify one worker invocation per bridge process and fresh-worker success. |

Runner allocation is narrow: Windows x64 must use a real Windows hosted runner
or supported VM; macOS x64 and ARM64 require hosted macOS runners; Linux ARM64
may use a native runner or a QEMU runner that executes the staged target
artifact. A cross-compile or package-layout-only check does not qualify worker
lifecycle, loader, or decoder behavior.

## Decision

The existing generic loader can be reused, while the same-CIX launch identity,
bounded pipe/output handling, and worker-only SDK boundary are retained. The
required CIX work is bounded to platform descriptor/filename selection, common
loader adoption, target child control, and target bridge packaging. Full PAQ
availability on Windows x64, macOS x64/ARM64, and Linux ARM64 remains blocked
until the decisive per-variant runner evidence exists.
