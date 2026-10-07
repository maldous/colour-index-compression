# C++ core next batch v1

This is a read-only review of `scan-v2/cix-native-core` and the current
first-party sources.  It deliberately excludes the completed spatial stride
guard, vendor files, SDK headers, and a formatting-only rewrite.

## What the preserved scan supports

`scan-v2` indexed 13 CIX translation units and reported 602 code smells.  Its
largest groups are profile policy findings: 207 undocumented APIs, 142
multiple-statements-per-line findings, 24 long lines, and complexity/naming
thresholds.  They do not establish a codec defect.

The raw Cppcheck signals do not produce another confirmed core bug:

* `knownConditionTrueFalse` and `nullPointerArithmeticRedundantCheck` are
  reported through `src/zpaq_ffi.cpp`, but their locations are in the pinned
  `vendor/libzpaq715/libzpaq.h`.  They are not CIX source-edit candidates.
* The spatial `redundantAssignment` at the JP2 box walker assignment is not a
  safe deletion.  `at = start + length` advances to the next declared box;
  deleting it changes multi-box parsing.  It needs a malformed-JP2 regression
  before any refactor, not a scan-driven cleanup.
* Missing standard, CharLS, OpenJPEG, JXL, and project include diagnostics are
  compiler-model gaps.  They should be revisited only after the refreshed
  compiler metadata supplies their existing read-only include roots.

The stride check was the one concrete spatial arithmetic concern in the
earlier review.  Its focused qualification has passed, so it is intentionally
not part of this batch.

## Recommended bounded batch

### 1. Share the JXL encoder drain path

Extract the duplicated bounded output loop at
`codecs/jxl/cix_jxl_bridge.cpp:276-291` and `:496-508` into a private helper,
for example:

```cpp
int drain_encoder(Encoder* encoder, size_t max_output_bytes,
                  cix_jxl_buffer* output);
```

The helper must retain the existing observable order: collect at most the
4 KiB scratch chunk, reject `produced > max_output_bytes - encoded.size()`
before insertion, map every non-`JXL_ENC_NEED_MORE_OUTPUT` status through
`encoder_status`, then allocate/copy only after `JXL_ENC_SUCCESS`.  Both gray
and planar entry points keep their distinct image setup; only the common drain
and final ownership transfer move.

This is the smallest useful extraction because it keeps the same output-limit
rule in both public encoders.  It reduces duplicated correctness-sensitive
code without changing the C ABI, libjxl configuration, output bytes, or error
codes.

Acceptance should extend the retained JXL bridge checks rather than add a
new broad suite:

1. Existing gray 8/16-bit and planar exact round trips still pass.
2. For both encoders, a cap one byte below the produced archive returns
   `CIX_JXL_OUTPUT_LIMIT` with a null/zero output buffer.
3. A successful archive still decodes exactly and a one-byte trailing suffix
   remains rejected by the existing exact-consumption decode checks.

`jobs/jxl-bridge-v3/check_jxl_bridge.py` already exercises gray fixtures and
`planar_fixture.py` exercises planar encode/decode.  Those are the natural
places for the first two targeted assertions; no codec benchmark is needed.

### 2. Make the ZPAQ watchdog non-wrapping, with an owned test seam

`src/zpaq_ffi.cpp:43-52` uses `if (g_instruction_budget-- == 0)`.  The call
that returns `false` changes zero to `SIZE_MAX`.  The patched upstream loop
currently raises immediately after a false return, but the guard should remain
terminal if that caller changes or if an exception path observes the state.

The safe narrow change is:

```cpp
if (g_instruction_budget == 0) return false;
--g_instruction_budget;
```

Keep the cancellation cadence and `SliceWriter` progress reset unchanged.
Before changing it, first add a private, allocation-free owned test seam for
the counter state (not a public C ABI export).  Its test must demonstrate that
after progress reset, the first 1,000,000 charges pass and every later charge
fails until another progress reset.  Continue to cover a normal large level-5
round trip and the existing trailing-data rejection in
`tests/zpaq_backend.rs`.

This is a correctness hardening identified during source review, not an
analyzer defect.  It should be a separate micro-patch if the private test seam
would disturb the Rust/C++ build boundary; do not expose an ABI merely to
satisfy a unit test.

## Deliberately deferred

* Do not split the spatial JP2/JPEG-LS decoder or reformat its dense public
  functions merely to lower the scan totals.  Those functions enforce exact
  terminal markers, dimensions, output caps, and C ABI status mapping; their
  current scan findings are mainly style and complexity thresholds.
* Do not rename public C functions or structs to satisfy naming rules, change
  callback constness, or bulk-add API/file headers without an approved project
  header policy.  Each can change a public consumer contract or license text.
* Do not modify `vendor/libzpaq715`, CharLS, OpenJPEG, JXL, or system headers.
  Their reported warnings belong in refreshed scanner provenance, not a CIX
  source patch.

The JXL drain extraction is ready to schedule after the fresh scanner result.
The watchdog hardening is worthwhile only with the stated private test seam;
otherwise it remains a documented follow-up rather than an untested edit.
