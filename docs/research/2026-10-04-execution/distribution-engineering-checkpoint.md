# Distribution engineering checkpoint

This is private preparation, not publication or final release acceptance. Benchmarks remain on hold.

The source export has a conventional root workspace, Makefile, build/install README and allowlisted native/portable crates. Development-only export generators, research, evidence and corpus assets are excluded. Export staging preserves PAQ source identities and selected provider notices. Four validation attempts are retained; [v4](jobs/source-export-sanitization-v4/raw/result.json) passed recursive checks for private home, work, research and development-checkout paths after correcting development-tool and receipt-field leaks.

[Engineering v4](jobs/distribution-engineering-v4/) provides the earlier actual optimized source-export build and runtime/SDK staging. [SDK/runtime contract v1](jobs/sdk-runtime-contract-v1/) subsequently validates real Linux installation and a synthetic Windows DLL/import-library layout, including required-pair rejection and imported CMake target properties. The Windows layout is not a native Windows execution result.

[Bridge portability v1](jobs/bridge-portability-v1/) rebuilt four PAQ libraries and the JPEG XL bridge. Its spatial configuration failure is retained; [v2](jobs/bridge-portability-v2/) fixes library discovery and builds the spatial bridge. Rebuilt artifacts are not silently substituted into the selected runtime. [Provider binding review](reviews/provider-binary-binding-v1.md) distinguishes matching JXL bytes, different PAQ rebuilds and the selected spatial source-to-install trace including RPATH changes.

Debian/RPM/macOS/Windows build files now follow the root workspace and SDK layout. Package-manager and actual non-Linux execution checks remain pending. External provider licensing identities/notices and explicitly unresolved origin/package metadata remain visible. This checkpoint does not certify an undocumented upstream identity or give a final legal conclusion.

Final quality checks, final binary/source/dependency freeze, actual package tests, required platform evidence and independent RC51 review still precede compression benchmarking.
