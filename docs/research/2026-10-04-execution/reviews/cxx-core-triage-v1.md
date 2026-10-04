# C++ core triage v1

The scan reports 602 code smells across 13 translation units. It does not
report a vulnerability, bug, or security issue type. Of the 141 raw Cppcheck
diagnostics, 102 are include-model or checker-report artifacts and 27 point
inside the pinned libzpaq or CharLS headers. Those external headers remain
unchanged.

The first fix group should be a small spatial-bridge argument guard. Its
CharLS 16-bit path derives a 32-bit row stride as `width * 2`, while its byte
count check operates in `size_t`. Reject a width that cannot form that stride,
and add only boundary and ordinary 8/16-bit contract coverage. This is a
source-review finding rather than a current analyzer warning.

Do not remove the JP2 walker cursor assignment at line 161 merely to silence
Cppcheck. It advances the parser after a declared box and is likely a
path-insensitive warning. Revisit it only with malformed-JP2 coverage.

The JXL, spatial and ZPAQ functions deserve later maintainability work because
they carry decoding boundaries, output limits, exact consumption and
cancellation. Split side-effect-free checked helpers gradually, with focused
exact-decoding regressions. Large cosmetic reformats, exported ABI renames,
and vendor edits are not an appropriate response to this scan.

Kernel-overlay adapter triage confirmed that it will preserve the active scan
and recommend any include-root/compile-database correction separately. A later
analyzer-only follow-up may restore recorded system, SDK and project include
roots; it should not be represented as a product-source repair.
