# Native core semantic findings v1

This is a read-only review of the preserved `scan-v3/cix-native-core` issue
export and the current first-party source. It excludes public-header
documentation already in progress, parser recovery, file-header policy, SDK
and vendor findings, and the qualified JXL drain change.

## One source-backed hardening candidate

`src/zpaq_ffi.cpp:43` uses post-decrement in the interpreter watchdog:

```cpp
if (g_instruction_budget-- == 0) return false;
```

When the counter is zero, this correctly returns `false`, but also wraps the
thread-local `size_t` to `SIZE_MAX`. The current patched upstream loop stops
immediately when it sees false, so this is not evidence of a demonstrated
archive-decoding failure. It is nevertheless a real terminal-state invariant
violation: a future caller that observes the counter, retries a charge, or
catches around the interpreter could turn the exhausted watchdog into an
unbounded one.

The minimal repair is:

```cpp
if (g_instruction_budget == 0) return false;
--g_instruction_budget;
```

It preserves the first one million successful charges after
`cix_zpaq715_instruction_progress`, the existing cancellation poll cadence,
and all wire behavior. Acceptance should use an owned private test seam for
charge/progress state, proving that exhaustion remains false until progress
resets it; retain the existing normal decode and trailing-data checks. Do not
add a public ABI function merely for that test.

## Scan-v3 signals that are not safe repairs

* The spatial JP2 walker `at = start + length` at
  `codecs/spatial/cix_spatial_bridge.cpp:170` is reported as a redundant
  assignment. It advances to the next declared box; removing it changes
  multi-box parsing. Keep it unless a separately designed malformed-JP2 test
  proves an equivalent rewrite.
* The four PAQ bridge suggestions (`constVariableReference` and
  `useStlAlgorithm`) concern local construction of a mutable argv required by
  upstream. They offer no correctness or resource-bound improvement.
* JXL decoder callback constness is an ABI callback signature question, not a
  safe analyzer-only change; its qualified drain behavior remains untouched.
* The dictionary example's missing include, system-header gaps, parser
  recovery, naming, complexity, and line-style findings are analyzer or policy
  matters. They do not establish a native codec defect.

No further high-confidence first-party core correctness defect is supported by
the scan evidence in this bounded review.
