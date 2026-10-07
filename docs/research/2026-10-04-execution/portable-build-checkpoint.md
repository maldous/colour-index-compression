# Portable build and API documentation checkpoint

The CIX-owned runtime installer now stages a prebuilt native-only executable
without requiring a C compiler. Unix retains its command symlinks; Windows
uses identical `cix.exe`, `uncix.exe` and `cixcat.exe` copies. Windows command
name handling accepts mixed-case `.exe` suffixes. Full-engine companion
staging explicitly requires Linux; other targets remain unqualified.

`runtime-alias-layout-v2` passed Linux and synthetic Windows installation
layouts, byte identity, Unix symlinks, Windows copies, and explicit Windows,
Darwin and FreeBSD full-engine refusal. It compiled and exercised the exact
extracted Rust alias functions with warnings denied. This is not a whole CLI
build or native Windows execution result. Final CLI compilation remains part
of the final-source build.

Spatial bridge builds can use multiple explicit SDK roots while retaining
target-toolchain multiarch lookup and selected-library overrides. Compiler
settings now refuse unsupported compiler policies instead of assuming GNU
options. `bridge-build-policy-v1` configured all four PAQ bridges and found
their compiler arguments equal to the retained Linux baseline after removing
only source/object path differences. It did not rebuild PAQ or compare linker
arguments. The spatial bridge built against separate retained CharLS and
OpenJPEG roots and passed its optimized row-stride overflow and exact-roundtrip
contract. Retained SDK identities were unchanged. The new bridge has not been
selected into a final distribution provider closure.

Five public SDK headers and four PAQ bridge headers received factual API
documentation. The recorded source review found identical non-comment text
before and after. No declaration, numeric value, layout or license grant
changed. This does not close the separately unresolved legal file-header policy.

The Squash host contract now bounds callback output before copying and uses
typed pointer sentinels for its pinned variadic APIs. The optimized contract
passed against the retained plugin, including buffer, stream and splice
roundtrips. It does not establish new host or platform compatibility.

No compression ratio or throughput improvement is claimed by this checkpoint.
Final source export, language analysis, package qualification, target runners,
license/provenance closure and independent RC51 acceptance remain open.
Benchmarking and publication remain held.

The CLI helper subsequently received whitespace-only line wrapping; its non-whitespace bytes match the tested version. `sonar-tool-tests-v13` passed formatting on that exact updated file. See `reviews/cli-format-followup-v1.json`.
