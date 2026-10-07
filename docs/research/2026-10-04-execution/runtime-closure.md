# Runtime companion closure

The ordinary relocated runtime install has already established one physical
`cix` binary with `uncix` and `cixcat` aliases. Full-engine staging deliberately
remains stricter: it accepts six explicit bridge paths and, on Linux, eight
explicit companion library paths. It installs every accepted item in
`<prefix>/lib/cix`, exactly where native installed-provider discovery expects
it. There is no `PATH`, environment, build-tree, or directory-scan fallback.

The companion set and observed ELF dependencies are recorded in
[runtime-closure.json](runtime-closure.json). It includes JXL/JXL threads/JXL
CMS, the three Brotli libraries, CharLS, and OpenJPEG, with only required SONAME
links created next to selected real files. System and further transitive
libraries are deliberately not copied or represented as closed.

The CMake staging rule receives an explicit absolute `readelf` path and uses
read-only dynamic-section inspection. It requires `$ORIGIN` on both bridges and
every JXL/Brotli companion, without using CMake `file(RPATH_CHECK)`, which can
remove a mismatching input. The installed `jxl-prefix-v3` bridge and inspected
JXL/Brotli companions meet this input-layout condition; the previously observed
absolute RUNPATH was the separate build-tree artifact, not the installed bridge.
A staged provider-load and archive-only round-trip receipt, package dependency
evidence, and platform-specific loader work remain required. macOS and Windows
full-engine staging are intentionally unimplemented.
