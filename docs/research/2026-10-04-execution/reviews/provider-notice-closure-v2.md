# Provider notice closure v2

The selected-provider closure has fourteen runtime providers. This review adds
deterministic staging input at `rust/cix-native/packaging/notices/` with seven
verbatim notice texts and provider-to-notice/hash bindings.

PAQ bridge identities are bound to their four existing source receipts and the
exact GPL-2 text. JXL, skcms, Brotli and Highway texts come from the existing
JXL build evidence. CharLS and OpenJPEG use the exact package copyright files
from the selected SDK prefix.

This is provenance and notice material only. It does not decide licensing,
confirm redistribution rights, or close the missing source-package provenance
for JXL/Brotli, CharLS, or OpenJPEG. The unresolved entries in the manifest must
flow to final package review.
