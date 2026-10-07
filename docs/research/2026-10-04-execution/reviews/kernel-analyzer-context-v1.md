# Kernel analyzer context qualification

The CIX-owned analyzer now preserves the retained Kbuild stage’s quoted-include
context for the decompressor. Only the decompressor and registration translation
units receive an 8 MiB preprocessing cap; the default remains 2 MiB. Current
stage headers and the retained successful build/source receipts are bound as
new analysis inputs, not retroactive build evidence.

The preserved progression includes the v3 2 MiB-cap failure, projection-v1’s
missing source-relative quoted header, projection-v2’s successful 14 compiler
projections, and adapter-v4’s remaining GNU `typeof` configuration error.
The v4 scan indexed 55 files, reported 746 issues and nine parser recoveries;
it is not a clean result.

The revised normalizer changes GNU `typeof` to its equivalent `__typeof__`
spelling only in the decompressor’s compiler-generated projection. It preserves
quoted text, directive operands, comments and identifier substrings. Existing
`__extension__` removal retains equal-width spaces. All 27 focused tool tests
passed; projection-v3 reproduced 14 of 43 translation-unit records under the
frozen 55-file scope. A direct pinned Cppcheck 2.13 run on the decompressor
completed with 1,334 equivalent keyword spelling changes and zero
`unknownMacro` or `preprocessorErrorDirective` diagnostics.

No product source or third-party source changed. The other diagnostics and
public-header/parser work remain open. The direct check does not qualify a
new complete Sonar run. Large compiler projection files are retained locally;
their full hashes and the reproduction inputs are checkpointed.
