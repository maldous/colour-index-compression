# Adapter parser-context diagnosis v1

**Scope:** read-only diagnosis of the 26 `cxx:ParsingErrorRecovery` findings
in `scan-v3/cix-native-adapters`.  No source, scanner configuration, or tool
was changed.  The pinned plugin inspected is
`sonar-cxx-plugin-2.3.0.1496.jar`; its bundled parser is
`org.sonar.cxx.parser.CxxGrammarImpl`, a C++ grammar with its own
preprocessor, rather than the host compiler.

## Result

The 26 recoveries are not evidence that the affected CIX code is unsupported
by its qualified compilers.  The scan log records 662 include-directive errors
and states that its 26 syntax errors are typically caused by missing includes,
macros, or compiler extensions.  Four issue groups are missing-context cases;
one is a localized C-language grammar limitation.

| Locations | Count | Classification | Faithful next step |
| --- | ---: | --- | --- |
| `adapters/blosc2/include/cix_blosc2_adapter.h:29,32` | 2 | The CIX export macro expands to GNU `__attribute__((visibility("default")))`; this is the same visibility-annotation form that header-context-v2 normalized for JXL. | Add a generated analyzer-only header projection that removes only this ABI visibility annotation. Preserve the declaration, return type, and symbol name. |
| `adapters/gio/cix-gconverter.h:6,11` | 2 | Missing GLib/GObject preprocessor context. The log repeatedly reports undefined `g_macro__has_attribute` / `g_macro__has_feature`; the declaration uses `G_BEGIN_DECLS`, `G_DECLARE_FINAL_TYPE`, and `G_END_DECLS`. | Repair the mounted, exact GLib include closure and compiler predefined-macro context first. If the pinned parser still cannot digest upstream GObject macro output, use a generated CIX header projection containing the exact opaque types and declarations consumed by this header, not a product-code rewrite. |
| `adapters/rocksdb/cix_compression_manager.h:13,18` | 2 | Missing C++ standard and pinned RocksDB header context, not a CIX language extension. The scan log cannot resolve the RocksDB headers; the issue file also reports missing `<cstddef>`, `<cstdint>`, and `<memory>`. | Mount the exact compile-command include roots with their symlink targets and a usable C++ standard-header closure. If required, use a narrow analyzer-only declaration context for `std::shared_ptr` and `rocksdb::CompressionManager`; retain the real method signatures. |
| `bindings/node/src/cix_node.c:376` | 3 | Missing Node N-API registration macro context. All three recoveries are the one top-level `NAPI_MODULE(NODE_GYP_MODULE_NAME, init)` invocation; the recorded compiler command supplies `-DNAPI_VERSION=8` and the Node include root. | Preserve that define and mount the exact Node header closure. If the parser still rejects the upstream registration expansion, normalize only the one registration macro in an analyzer projection while retaining an explicit registration-to-`init` marker. Do not alter runtime registration code. |
| `adapters/squashfs/profile/src/cix_squashfs_profile.c:541–608` | 17 | A single cascading recovery from `MODEL_ALIGNMENT` in `cix_squashfs_profile_decode_with_workspace`. Its expansion is `offsetof(struct { char padding; model value; }, value)`: a C anonymous-structure type expression used to compute alignment. The function declaration is where recovery starts; its ordinary parameters and decoder logic are not independently unsupported. | Use an analyzer-only projection for this one alignment macro, with the replacement derived and recorded from the exact qualified C target ABI. It must preserve the workspace-alignment branch and must not change the portable decoder source or algorithm. Do not mark all subsequent `return`/`switch` locations as separate defects. |

## Concrete scanner-context evidence

`scan-v3/cix-native-adapters/scanner.log` reports unresolved include directories
under `/cix-external/7/arch/x86/include/uapi`, `/cix-external/7/include/uapi`,
and `/cix-external/7/ubuntu/include`, then warns that external RocksDB, Blosc,
GLib, kernel, and SquashFS headers cannot be found below `/usr/src`.  This
means the external-root rebasing loses required nested paths or their symlink
targets.  Repair that mount/closure mapping before adding language-specific
normalization.

The Cppcheck `missingIncludeSystem` findings for standard C/C++ headers in
Blosc, Node, RocksDB, and the profile are the same incomplete-header-context
signal.  They do not establish a product source error.

## Boundaries

The proposed projections are analysis input only and must be generated from
pinned headers and recorded compiler arguments.  They must not invent vendor
APIs, change CIX runtime behavior, or silence a recovery without retaining the
corresponding declaration/control-flow shape.  A subsequent bounded scan must
show each stated recovery count falling for the stated reason; it should not
reinterpret ordinary style/complexity findings as parser recovery fixes.
