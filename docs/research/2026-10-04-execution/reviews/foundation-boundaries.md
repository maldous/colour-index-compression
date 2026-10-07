# Foundation boundary review

**Scope.** Read-only static inspection of the current planar JXL bridge and Rust provider, C buffer ABI, and PAQ parent/worker boundary. No build, test, codec, SDK consumer, cancellation, resource-limit, or RSS measurement was run for this review. The running qualification is execution evidence for its covered cases; it cannot establish a general process-memory or cancellation proof.

## Material finding: JXL UINT8 decode is not presently a hard caller ceiling

`JxlProvider::jpegxl_decode` accepts a request when its canonical u16 output is no larger than `memory` ([jxl_provider.rs:306-315](../../../../rust/cix-native/src/full_engine/jxl_provider.rs)). That is insufficient for the actual UINT8 path. `decode_cix_u16_gray_2d` allocates the raw one-byte plane, then constructs the two-byte canonical output with `raw.into_iter().flat_map(...).collect()` ([jxl_bridge.rs:540-554](../../../../rust/cix-native/src/jxl_bridge.rs)); the planar path repeats it at [jxl_bridge.rs:751-782](../../../../rust/cix-native/src/jxl_bridge.rs). The raw allocation remains owned by its iterator while the canonical vector is allocated. For `P` samples this is at least `P + 2P`, before libjxl decoder state and a retained compressed input.

A bounded known-buffer plan must reserve, for UINT8, raw `P` plus canonical `2P`; for UINT16, canonical `2P` only. It must also include the input if the enclosing memory budget retains that payload. Thus the CIX-owned-buffer floor is `3P` or `2P`, respectively, plus payload where applicable. The identical formula applies to planar data when `P` includes all planes. This does not establish a cap for libjxl’s internal state; that needs an independently enforceable bridge/API limit or an explicitly qualified process-level guard.

The LZMA copy path is different. Passing `memory - expected` to the bridge can account correctly for known buffers: the bridge admits source plus bridge output plus internal state within that remainder, and the Rust copy then consumes `expected`. This conclusion assumes the caller's `memory` includes source and all stated bridge allocations; it does not substitute for measured runtime overhead.

## JXL bridge and ABI observations

The planar bridge performs checked dimension products before output pointer arithmetic and accepts only the specified one-still-image optional-channel layout. It verifies basic information before registering output buffers ([cix_jxl_bridge.cpp:518-588](../../../../rust/cix-native/codecs/jxl/cix_jxl_bridge.cpp)). The final decoder checks geometry, bit depth, channel count, full-image completion, and unconsumed input before success ([cix_jxl_bridge.cpp:550-596](../../../../rust/cix-native/codecs/jxl/cix_jxl_bridge.cpp)). This is useful bounded-format validation, not a full libjxl-memory proof.

The C++ encoder caps produced codestream bytes but retains a `std::vector` and then separately allocates the bridge return buffer ([cix_jxl_bridge.cpp:277-297](../../../../rust/cix-native/codecs/jxl/cix_jxl_bridge.cpp), [cix_jxl_bridge.cpp:497-513](../../../../rust/cix-native/codecs/jxl/cix_jxl_bridge.cpp)); Rust subsequently copies it. An output-byte cap therefore is not a single-buffer allocation limit.

The provider uses Linux `dlopen` on an explicit absolute regular file, with no PATH or environment search ([jxl_provider.rs:85-141](../../../../rust/cix-native/src/full_engine/jxl_provider.rs)). It does not establish package ownership, inode identity, or a digest for that file; the trusted package-layout claim remains a caller/integration assumption. The private generic `Library::symbol<T>` uses `transmute_copy` from `void *` ([jxl_provider.rs:366-373](../../../../rust/cix-native/src/full_engine/jxl_provider.rs)). Current call sites use declared C function-pointer aliases, but the helper has no same-size assertion and should remain restricted to those aliases. The non-Linux implementation deliberately refuses to load ([jxl_provider.rs:385-396](../../../../rust/cix-native/src/full_engine/jxl_provider.rs)); portable Rust compilation is not macOS or Windows JXL route support.

## C buffer ABI observations

The C ABI validates option version and advertised size before reading the full v1 structure ([c_api.rs:107-127](../../../../rust/cix-native/src/c_api.rs)), rejects overlapping input, output, and `needed` ranges ([c_api.rs:298-350](../../../../rust/cix-native/src/c_api.rs)), and copies a completed result only after checking output capacity ([c_api.rs:203-230](../../../../rust/cix-native/src/c_api.rs)). The installed header explicitly documents whole-buffer semantics, unchanged output on `OUTPUT_TOO_SMALL`, externally serialized destruction, and that v1 makes no process-RSS hard-cap guarantee ([cix.h:51-78](../../../../rust/cix-native/include/cix.h)).

Those are source/API-contract properties. Raw C pointers still rely on the documented caller guarantee of readable/writable live storage; range arithmetic cannot validate arbitrary foreign addresses. `catch_unwind` converts a Rust unwind to a status, but it cannot itself suppress the process-global Rust panic hook. This review therefore does not certify an absolute no-stderr-under-every-panic property. The staged C consumer and Rust buffer tests are necessary execution evidence, but do not measure every host embedding behavior.

## PAQ parent and worker supervision

The parent uses an explicit executable path and an internal worker switch, clears the child environment, bounds retained diagnostics while continuously draining both pipes, polls cancellation/deadline, kills and reaps its direct child, and uses a fallible parent result reservation ([paq_supervisor.rs:177-252](../../../../rust/cix-native/src/paq_supervisor.rs), [paq_supervisor.rs:342-378](../../../../rust/cix-native/src/paq_supervisor.rs)). Its Unix temporary-root validation rejects symlinked, shared-writable, and non-private roots before `mkdir(0700)` ([paq_supervisor.rs:570-643](../../../../rust/cix-native/src/paq_supervisor.rs)). These are meaningful parent-side controls.

The worker applies Linux `RLIMIT_AS` and `RLIMIT_FSIZE` before loading the private PAQ bridge ([paq_worker.rs:220-277](../../../../rust/cix-native/src/paq_worker.rs), [paq_worker.rs:297-327](../../../../rust/cix-native/src/paq_worker.rs)). This is not cross-platform support: the non-Linux/x86-64 path explicitly returns an unsupported error. Nor does source inspection prove observed RSS, aggregate multi-worker budget enforcement, exact cancellation latency, or cleanup of grandchildren a third-party library might create. The contract supervises the direct worker; the full-engine scheduler must reserve worker, parent-result, and diagnostic budgets as the code comments state.

`PaqWorkerRequest` accepts arbitrary absolute executable and library-directory paths after basic `is_file`/`is_dir` checks ([paq_supervisor.rs:266-339](../../../../rust/cix-native/src/paq_supervisor.rs)). It does not bind those paths to an installed CIX identity. That is acceptable only while this private module is called exclusively with product-owned staged paths. It must not become a public embedding API or path-bearing archive control surface without stronger provenance validation.

## Acceptance wording supported by this review

The source supports: *a Linux-qualified direct-child PAQ worker protocol with per-worker rlimit setup; a CIX-owned planar JXL bridge that validates paid shape before caller output-buffer registration; and a whole-buffer C API with caller-owned buffers and documented lifetime limits.*

It does **not** support: *a universal hard RSS ceiling, cross-platform PAQ/JXL availability, exact cancellation latency, arbitrary-DSO trust, or a claim that all panic paths are silent.*

## Correction: v12/v13 qualification evidence

This correction supersedes only the earlier JXL known-buffer finding. The
original review's distinction between CIX-owned buffers and unmeasured codec or
process RSS remains in force.

### JXL known CIX-buffer admission is now implemented and exercised

The current bridge computes a checked retained-buffer total before the raw
output allocation: input payload plus raw transport plus canonical output for
UINT8, or input payload plus the single returned raw/canonical buffer for
UINT16 ([jxl_bridge.rs:148-170](../../../../rust/cix-native/src/jxl_bridge.rs),
[jxl_bridge.rs:562-596](../../../../rust/cix-native/src/jxl_bridge.rs)). The
planar decoder uses the same shared admission helper. The provider maps that
rejection to its resource-limit path and documents that libjxl internal working
state remains outside this CIX-owned-buffer claim
([jxl_provider.rs:339-365](../../../../rust/cix-native/src/full_engine/jxl_provider.rs)).

The relevant v12 source is recorded in
[jobs/foundation-v12/source.json](../jobs/foundation-v12/source.json):
`src/jxl_bridge.rs` SHA-256
`34997571175767b31013a1835532b40ef333b82f7b15ed2973d1885d5fa6b524` and
`src/full_engine/jxl_provider.rs` SHA-256
`4011b04cf449e7f124ad13d160ed80e6f9fc8e9773f5f891ff98eea2ec4abdbe`.
Its JXL bridge unit suite passed the simultaneous-UINT8-budget case, and the
provider suite passed the real packaged bridge canonical round trips; see
[jobs/foundation-v12/raw/cix-rel01-execution-foundation-v12.stdout.log](../jobs/foundation-v12/raw/cix-rel01-execution-foundation-v12.stdout.log)
(lines labelled `jxl_bridge::tests` and `full_engine::jxl_provider::tests`).
This validates the stated known-buffer accounting and retained-layout routes;
it is not an internal-libjxl or true process-peak measurement.

### Installed SDK relocation evidence

The v13 qualification completed successfully; its scheduler receipt records
child and supervisor exit code zero
([jobs/foundation-v13/scheduler-output.json](../jobs/foundation-v13/scheduler-output.json)).
Both relocated shared and static installed SDK consumer builds passed, with the
recorded pkg-config link flags in
[jobs/foundation-v13/sdk-results.json](../jobs/foundation-v13/sdk-results.json).
The raw command/output evidence shows the installed C consumer builds under
`-Werror` from the relocated prefix
([jobs/foundation-v13/raw/cix-rel01-execution-foundation-v13.stdout.log](../jobs/foundation-v13/raw/cix-rel01-execution-foundation-v13.stdout.log)).
This corrects the earlier v12 static-package consumer failure; it does not add
a streaming C API or change the header's explicit whole-buffer scope.

### PAQ parent lifecycle evidence

The opt-in v12 parent lifecycle test passed all packaged PAQ variants under the
private test root: `paq_supervisor::tests::opt_in_parent_lifecycle_exercises_all_packaged_variants`.
The same focused suite reports six passed tests, including diagnostic drain,
parent-result reservation, private-root rejection, and cleanup
([jobs/foundation-v12/raw/cix-rel01-execution-foundation-v12.stdout.log](../jobs/foundation-v12/raw/cix-rel01-execution-foundation-v12.stdout.log)).
The aggregate v12 phase itself was not a clean overall pass, so this is focused
supervisor evidence rather than a whole-foundation acceptance claim. It remains
Linux-qualified direct-child supervision; it does not establish cross-platform
PAQ availability, aggregate scheduler resource control, exact cancellation
latency, or arbitrary-library provenance.

### Remaining boundary limits

No evidence in v12/v13 changes the C header statement that v1 has no
incremental C API and no process-RSS hard-cap guarantee
([cix.h:51-78](../../../../rust/cix-native/include/cix.h)). The previously
stated platform limits, trusted package-path assumptions, and full-engine
scheduler obligations remain open until separately qualified.
