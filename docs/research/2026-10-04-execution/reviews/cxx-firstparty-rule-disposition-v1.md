# C/C++ first-party rule disposition v1

Date: 2026-10-05
Scope: `scan-v3` first-party C/C++ issue inventory only. No source change, build, scan, suppression, vendor change, or blanket closure is proposed.

The two first-party slices contain **1378** issues: core 612, adapters 766. The producer reports `SCANNED_WITH_RECORDED_FINDINGS`; authoritative `scan-v3/qualification-review.json` reports `ANALYSIS_GAPS_REMAIN_NOT_CLEAN`. This is triage, not a clean-scan claim.

The qualification review separately records six raw Cppcheck configuration errors in the first-party adapter slice: five `preprocessorErrorDirective` and one `unknownMacro`. The issue inventory imports three `cppcheck:preprocessorErrorDirective` rule issues. These counts have different provenance and must not be merged or treated as closure.

## Rule counts and disposition

| Rule | Core | Adapters | Total | Disposition |
|---|---:|---:|---:|---|
| `cppcheck:constParameterCallback` | 1 | 5 | 6 | maintenance; component-owned review |
| `cppcheck:constParameterPointer` | 2 | 4 | 6 | maintenance; component-owned review |
| `cppcheck:constStatement` | 0 | 1 | 1 | maintenance; component-owned review |
| `cppcheck:constVariableReference` | 4 | 4 | 8 | maintenance; component-owned review |
| `cppcheck:duplicateExpression` | 0 | 1 | 1 | correctness review required |
| `cppcheck:knownConditionTrueFalse` | 0 | 7 | 7 | correctness review required |
| `cppcheck:missingInclude` | 1 | 0 | 1 | analyzer-configuration or parser-dependent |
| `cppcheck:missingIncludeSystem` | 72 | 121 | 193 | analyzer-configuration or parser-dependent |
| `cppcheck:preprocessorErrorDirective` | 0 | 3 | 3 | analyzer-configuration or parser-dependent |
| `cppcheck:redundantAssignment` | 1 | 0 | 1 | correctness review required |
| `cppcheck:redundantPointerOp` | 0 | 1 | 1 | correctness review required |
| `cppcheck:shadowFunction` | 0 | 3 | 3 | maintenance; component-owned review |
| `cppcheck:shadowVariable` | 0 | 3 | 3 | maintenance; component-owned review |
| `cppcheck:shiftTooManyBits` | 0 | 1 | 1 | correctness review required |
| `cppcheck:toomanyconfigs` | 0 | 2 | 2 | analyzer-configuration or parser-dependent |
| `cppcheck:uninitvar` | 0 | 1 | 1 | correctness review required |
| `cppcheck:unknown` | 1 | 2 | 3 | analyzer-configuration or parser-dependent |
| `cppcheck:unusedStructMember` | 0 | 1 | 1 | maintenance; component-owned review |
| `cppcheck:useStlAlgorithm` | 4 | 2 | 6 | maintenance; component-owned review |
| `cppcheck:varFuncNullUB` | 0 | 10 | 10 | correctness review required |
| `cppcheck:variableScope` | 0 | 2 | 2 | maintenance; component-owned review |
| `cxx:ClassName` | 12 | 19 | 31 | public API / ABI compatibility constrained |
| `cxx:FileComplexity` | 2 | 0 | 2 | maintenance; component-owned review |
| `cxx:FileHeader` | 21 | 55 | 76 | licence-policy unresolved |
| `cxx:FileName` | 1 | 3 | 4 | public API / ABI compatibility constrained |
| `cxx:FunctionCognitiveComplexity` | 12 | 29 | 41 | maintenance; component-owned review |
| `cxx:FunctionComplexity` | 24 | 50 | 74 | maintenance; component-owned review |
| `cxx:FunctionName` | 4 | 46 | 50 | public API / ABI compatibility constrained |
| `cxx:MethodName` | 23 | 7 | 30 | public API / ABI compatibility constrained |
| `cxx:ParsingErrorRecovery` | 39 | 26 | 65 | analyzer-configuration or parser-dependent |
| `cxx:TabCharacter` | 0 | 3 | 3 | maintenance; component-owned review |
| `cxx:TooLongLine` | 24 | 17 | 41 | maintenance; component-owned review |
| `cxx:TooManyParameters` | 12 | 4 | 16 | public API / ABI compatibility constrained |
| `cxx:TooManyStatementsPerLine` | 145 | 278 | 423 | maintenance; component-owned review |
| `cxx:UndocumentedApi` | 207 | 55 | 262 | public API / ABI compatibility constrained |

## What can proceed safely

### `squash-contract-stream-write`

**Scope:** `rust/cix-native/packaging/squash/contract.c`.
**Finding:** cppcheck:uninitvar at line 171.
**Change:** Before memcpy, prove *used <= capacity; when size is nonzero require data != NULL; copy only when size is nonzero. This preserves the callback result and makes the test harness reject invalid callback output instead of relying on zero-length memcpy pointer behaviour.
**Check:** Run the existing Squash contract target after review.

The same bounded contract correction uses `(void *) 0` for the exact pinned
Squash 0.8 variadic sentinel positions. The source declarations carry
`HEDLEY_SENTINEL(0)` in
`benchmark-work/native-rc-check-v1/codec-hosts-v2/squash-prefix/include/squash-0.8/squash/squash-codec.h:145-167`,
`squash-stream.h:84-88`, and `squash-splice.h:56-64`; this covers the codec,
stream, and splice calls in `packaging/squash/contract.c`. It is a typed
pointer sentinel, not a mass replacement of `NULL`.

### `api-docs-cix-owned-headers`

**Scope:** `rust/cix-native/include/cix.h`, `rust/cix-native/include/cix_stream.h`, `rust/cix-native/include/cix_dictionary.h`, `rust/cix-native/include/cix_formats.h`, `rust/cix-native/include/cix.hpp`, `rust/cix-native/codecs/jxl/cix_jxl_bridge.h`, `rust/cix-native/codecs/spatial/cix_spatial_bridge.h`.
**Finding:** cxx:UndocumentedApi (core 207).
**Change:** Add Doxygen /** */ or ///< comments to existing exported declarations describing existing units, ownership, status and bounds; no signatures, numeric values, ABI versions or layouts change.
**Check:** Use installed C/C++ consumer and bridge contract checks. This is source documentation, not a FileHeader remediation.

### `adapter-api-docs-cix-owned-headers`

**Scope:** `rust/cix-native/adapters/blosc2/include/cix_blosc2_adapter.h`, `rust/cix-native/adapters/gio/cix-gconverter.h`, `rust/cix-native/adapters/rocksdb/cix_compression_manager.h`, `rust/cix-native/adapters/sevenzip/cix_7zip_coder.h`, `rust/cix-native/adapters/squashfs/profile/include/cix_squashfs_profile.h`, `rust/cix-native/adapters/squashfs/userspace/include/cix_sqfs_userspace.h`.
**Finding:** cxx:UndocumentedApi (adapters 55).
**Change:** Document only genuine CIX/host integration surfaces with Doxygen comments and preserve host macro and ABI conventions.
**Check:** Run each affected host contract; do not document kernel compatibility shims or host-generated macro declarations merely to reduce count.

## Findings that must not be superficially “fixed”

- **cppcheck:shiftTooManyBits, squashfs profile get_varint line 307:** The uint32_t loop admits shifts 0, 7, 14, 21 and 28 only; the fifth-byte payload guard rejects values above 15 and a continuation then increments to 35 and exits. The reported 34-bit path is infeasible. Keep the bounded guard; do not alter wire parsing to satisfy the diagnostic.
- **cppcheck:redundantAssignment, spatial JP2 walker line 170:** The cursor advance is consumed by the next loop iteration when it forms start and is part of exact box traversal. Do not delete it without malformed-JP2 contract coverage.
- **GObject macro findings in gio/cix-gconverter.{c,h} and gio/contract.c:** duplicateExpression, redundantPointerOp, shadow/const and known-condition findings arise in G_DEFINE_TYPE/G_DECLARE_FINAL_TYPE or g_assert macro expansion. They are not direct source corrections; scan with GObject macro context and retain host idioms.
- **cppcheck:knownConditionTrueFalse in Node receiver helper:** The comma expression deliberately reports a N-API error then returns false; refactor only if a Node owner can preserve the exact N-API error path.
- **cppcheck:unusedStructMember in profile contract:** The union aligned member is an alignment/storage fixture; removing it would change what the contract exercises.
- **cppcheck:varFuncNullUB in packaging/squash/contract.c:** The pinned Squash 0.8 declarations use `HEDLEY_SENTINEL(0)` at the invoked positions, so this bounded contract now supplies `(void *) 0`. Other host variadic calls still require their own declaration-level review; do not mass-replace `NULL`.

## Category guidance

### Correctness review required

`cppcheck:uninitvar`, `varFuncNullUB`, `shiftTooManyBits`, `duplicateExpression`, `redundantPointerOp`, `knownConditionTrueFalse`, and the core JP2 `redundantAssignment` need local semantic review. Only the Squash contract callback guard above is ready as a small bounded correction. The other occurrences are macro/host-API/parser-sensitive or have an existing exact-decoding role.

### Public API / ABI compatibility constrained

`cxx:UndocumentedApi` is productive documentation work because the plugin accepts `/** */` and `///<`. Naming, parameter-count, class-name and filename rules are not permission to rename C APIs, host callbacks, 7-Zip COM methods, GObject identifiers, N-API conventions, exported structs, or CIX ABI versions. Document first; change a name only under a separate compatibility design.

### Analyzer-configuration or parser-dependent

The 39 core and 26 adapter `cxx:ParsingErrorRecovery` findings, 193 imported missing-include diagnostics, and imported `unknown`, `preprocessorErrorDirective`, and `toomanyconfigs` rule findings require the matching host SDK include roots, macro definitions and compilation database. Separately, the qualification review records six raw Cppcheck configuration errors (five preprocessor and one unknown macro) in the adapter slice. Header parser recovery around `extern "C"`, visibility declarations, GObject macros and conditional kernel/profile code does not establish a source defect.

### Licence-policy unresolved

The 21 core and 55 adapter `cxx:FileHeader` findings remain unresolved until a truthful copyright/licence `headerFormat` is configured. The pinned CXX rule requires that legal expected text; an empty line, empty template or weakened regex is not closure. Factual purpose comments remain useful source hygiene but must not be counted as `FileHeader` remediation.

### Maintenance, separately owned

Statement-per-line, line-length, complexity, constness, STL preference, variable scope and tab findings are maintainability signals. Do them only in small component-owned diffs after contract coverage is available; dense codec and host glue should not receive a bulk formatter rewrite.

## RC47 closure order

1. Establish a correctly parameterized legal `FileHeader` policy after the existing licence decision; rescan to obtain a meaningful rule result.
2. Add Doxygen documentation to existing CIX-owned public ABI and host integration headers in the two bounded batches above.
3. Correct the Squash contract callback guard and run its host contract.
4. Restore each host compiler context for parser/include/macro findings, then review the remaining correctness candidates one by one.
5. Defer names and large complexity/formatting changes unless their owner supplies compatibility and regression evidence.

The JSON companion contains the machine-readable per-rule/per-scope counts and the same disposition rationale.
