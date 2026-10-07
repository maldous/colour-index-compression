# Integrated backend closure

The staged runtime places ordinary `bin/cix`, `bin/uncix`, and `bin/cixcat`
wrappers over `cix_runtime.cli`; native CIX binaries live below `libexec/cix`
for the native candidate adapter. PAQ v215, v216, joint-discount and state-only
binaries are likewise staged there under stable identifiers. The stage tool
copies installed NumPy/imagecodecs/JXL libraries as the qualified host closure.
It has no benchmark or results import path.

Staging is scheduler-only. It refuses to overwrite a destination and records a
file hash receipt. The resulting closure still needs focused correctness checks
before the single Silesia pass.
