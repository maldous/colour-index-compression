# C/C++ source annotation policy v1

Date: 2026-10-05
Scope: recommendation from the repository licence metadata and recorded CXX
findings, updated with the pinned plugin rule documentation and fresh
first-party `scan-v3` results. This is not a licence decision, source change,
scanner suppression, or ABI proposal.

## Evidence and ownership boundary

`rust/cix-native/Cargo.toml` declares `license = "MIT"`. Its sibling
`LICENSE` calls the MIT text a **proposed project licence, pending confirmation
by the copyright owner**, and says this private preparation copy is not a
public licence grant. That blocks a claim that the project has made a public
licence grant; it does not block ordinary, factual source hygiene. A short
purpose and ownership-boundary comment may say that a file is CIX-owned and
refer to the existing `LICENSE`, provided it makes no copyright assertion,
SPDX assertion, or new licence grant.

The scan has three materially different populations:

| Scan slice | `FileHeader` | `UndocumentedApi` | Ownership treatment |
|---|---:|---:|---|
| `cix-native-core` | 20 | 207 | CIX public headers, CIX bridge headers/TUs, CIX examples and qualification helper; document existing public APIs now, but configure legal FileHeader expectations only after the licence decision. |
| `cix-native-adapters` | 55 | 55 | CIX adapter, binding, packaging, integration, kernel-overlay and test files; split by host/adapter ownership. |
| `native-vendor` | 29 | 490 | Vendored libbsc/related material; do not add CIX headers or CIX API documentation. |
| `paq-*` reference slices | 1,315 | 7,352 | `benchmark-work/references/...`; external PAQ source, never bulk-edit for CIX scan findings. |

The original counts are from
`docs/research/2026-10-04-execution/sonar-preparation/scan-v2/result.json`.
Fresh first-party `scan-v3` results retain 21 core and 55 adapter `FileHeader`
findings, 207 core and 55 adapter `UndocumentedApi` findings, and report 39
core plus 26 adapter `cxx:ParsingErrorRecovery` issues. The producer status is
`SCANNED_WITH_RECORDED_FINDINGS`; authoritative
`scan-v3/qualification-review.json` reports
`ANALYSIS_GAPS_REMAIN_NOT_CLEAN`. This is evidence for prioritization, not a
clean-scan claim.

The qualification review distinguishes six **raw Cppcheck configuration
errors** in the first-party adapter slice (five `preprocessorErrorDirective`
and one `unknownMacro`) from the three imported
`cppcheck:preprocessorErrorDirective` rule issues. Those are not interchangeable
counts, and neither is a source-clean result.

## Licence decision, factual source hygiene, and `FileHeader`

The pending licence-grant confirmation applies to a copyright notice, SPDX tag,
or statement that grants or represents release rights. It does **not** prevent
ordinary reversible source hygiene: CIX-owned files may receive truthful
purpose/boundary comments, and existing public declarations may receive API
documentation, without making a legal claim.

That distinction does not make a purpose comment a `FileHeader` fix. The
pinned plugin contains these rule documents:

- `META-INF/lib/cxx-checks-2.3.0.1496.jar!/org/sonar/l10n/cxx/rules/cxx/FileHeader.html`
  says `cxx:FileHeader` **must** be supplied an expected copyright/licence
  `headerFormat`; its `regexCheckClass` default is empty.
- `META-INF/lib/cxx-checks-2.3.0.1496.jar!/org/sonar/l10n/cxx/rules/cxx/UndocumentedApi.html`
  documents Doxygen block `/** ... */` and trailing `///< ...` comments.

The enclosing pinned `sonar-cxx-plugin-2.3.0.1496.jar` is recorded with SHA-256
`95dd162a04d954a63713dd7cc6b4e14f1d361de6645dffdd8755069a12ea0197` in
`scan-v3/raw/tool-identities.json`; the nested checks JAR has no separately
recorded hash. The `scan-v3` profile activates all rules without rule
parameters. Its `FileHeader` issues therefore establish neither a missing
purpose comment nor a valid project legal template.

Configure `headerFormat` only after the copyright/licence authority chooses
truthful text and scope. Then apply that exact configured header only to
verified CIX-authored files, in the existing comment style and without
altering third-party notices. A blank line, an empty format, or a weakened
regex is not a valid workaround. Do not add “Copyright (c) 2026 CIX
contributors”, an SPDX marker, or an MIT grant merely because the draft
`LICENSE` contains those strings.

Before that legal decision, a file may still have a short factual purpose or
ownership-boundary comment, for example:

```c
/* CIX-owned adapter implementation. Uses the documented host API without
 * modifying host or upstream source. */
```

Such a comment must preserve an existing third-party notice verbatim and must
not be represented as satisfying `cxx:FileHeader`. Do not alter generated
files, SDK headers received from a host, vendored `rust/cix-native/vendor/**`,
or `benchmark-work/references/**`; do not use an analyzer exclusion or
scanner-rule change to hide a finding.

## API documentation rule

`cxx:UndocumentedApi` is not a reason to rename, reorder, resize, or otherwise
change public declarations. Add a concise adjacent Doxygen-style comment to an
existing exported declaration or public type. For each function, state
purpose, parameter units/valid ranges, ownership, output/cancellation/error
meaning, and thread or lifecycle expectations when applicable. For a public
struct, document the struct once and each field only when its meaning, unit,
or ownership is not obvious. For enum values, document the value class and
failure semantics without changing numeric values.

Do not document private implementation methods simply to silence a rule.
Either keep them private and let the host/component owner decide whether the
rule applies, or document a genuine host-facing API. Generated host macros and
external SDK declarations must retain their host's conventions. CIX wrappers
must keep existing `extern "C"`, calling convention, visibility, ABI version,
and struct layout unchanged.

## Coherent, small implementation batches

1. **Public C API and native bridges — core/ABI owner.** Cover
   `include/cix*.h`, `include/cix.hpp`, the JXL and spatial bridge headers,
   and the four CIX PAQ bridge headers. Document existing exported C
   functions, status enums, versioned option structs, pointer ownership, and
   size/limit units now. Add the configured legal `FileHeader` only after its
   separate decision. Keep `.cpp` file
   comments in the same batch only when they are verified CIX-authored. Run
   installed C/C++ consumer and bridge contract checks afterward. No public
   symbol or layout change is allowed.

2. **Host adapters with standalone headers — individual adapter owners.**
   One small batch each for Blosc2, GIO, RocksDB, 7-Zip, WiredTiger, HDF5,
   libarchive, and GStreamer. Start with each adapter’s own public header or
   exported registration/factory surface; document host ownership and host
   callback semantics. Keep each contract-test source in the same batch only
   for its factual purpose comment; defer legal `FileHeader` work. Do not
   annotate host/upstream headers. This prevents a large cross-host
   comment-only change from obscuring host ABI review.

3. **CIX bindings and installed-consumer examples — binding/SDK owners.**
   Cover CIX-owned JNI/Node TUs and installed C/C++ consumer test sources.
   These have file-header findings but are not a reason to expand the native
   public ABI. Their factual comments should name the existing CIX header
   contract and clarify that they are consumers or test harnesses.

4. **SquashFS overlays — SquashFS owners, separated by environment.**
   Split portable profile/tools, kernel overlay, and userspace overlays.
   Their CIX-owned files can receive factual boundary comments, while kernel
   shim headers must preserve kernel include and licence requirements. Add API
   comments only for CIX-owned entry points that a replacement table or
   overlay calls. Never touch copied upstream SquashFS source or pretend a
   comment changes the experimental method/profile contract.

5. **Examples, generators, and tests — owning test area.** Apply only the
   factual boundary comments and comments needed to explain a real test/fixture
   interface. Avoid documenting internal test helper symbols as public API.

Each batch should contain a frozen file list, before/after issue counts from a
corrected scan, a source diff review for ABI-neutrality, and its existing
focused host/consumer tests. No production change is needed solely to satisfy
`FileHeader` or `UndocumentedApi`.

## Explicit non-actions

- Do not modify vendor or PAQ-reference files, even though their rule counts
  dominate the report.
- Do not convert licence uncertainty into a project-wide SPDX or copyright
  assertion.
- Do not add or alter exported declarations, wire fields, method IDs, ABI
  versions, calling conventions, struct members, allocation ownership, or
  host registration to satisfy documentation rules.
- Do not suppress `cxx:FileHeader`/`cxx:UndocumentedApi` or weaken the scan.
- Do not infer documentation completeness from fresh first-party v3 results:
  they still report 39 core and 26 adapter `cxx:ParsingErrorRecovery` findings.

This policy lets component owners add small, reversible factual comments and
Doxygen API documentation now. `FileHeader` closure is a separate template
configuration plus legal-text decision; it cannot be claimed through a canary,
an empty line, or a weakened regex. Neither path changes third-party provenance
or any public contract.
