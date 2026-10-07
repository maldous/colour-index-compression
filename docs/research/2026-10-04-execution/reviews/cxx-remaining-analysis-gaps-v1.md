# C++ analysis gaps — scan v3 (live snapshot)

**Status:** read-only triage of the retained `freshscan-v3` evidence. This is
not a source, tool, suppression, or qualification change. The completed scan
is not clean: its qualification review records `ANALYSIS_GAPS_REMAIN_NOT_CLEAN`.

## What the live reports show

| Area | Current diagnostic | Evidence | Classification |
|---|---|---|---|
| Native core | 39 `cxx:ParsingErrorRecovery` diagnostics, all in six installed-facing bridge headers | `codecs/jxl/cix_jxl_bridge.h` (13), the four `codecs/paq/*/*_bridge.h` files (4 each), and `codecs/spatial/cix_spatial_bridge.h` (10) | Sonar CXX header parser limitation, not a Cppcheck compiler-preprocessor failure |
| Adapters | 26 `cxx:ParsingErrorRecovery` diagnostics | Node binding (3); public Blosc2, GIO, and RocksDB headers (6); CIX SquashFS profile implementation (17) | Sonar CXX parser limitation on declarations/macros and C constructs outside a fully compiled translation-unit context |
| GStreamer | `G_DECLARE_FINAL_TYPE` unknown macro | `adapters/gstreamer/src/gstcixstream.c:6`; the recorded compile command supplies the GStreamer and GLib include paths | Cppcheck is not seeing the GLib macro expansion that the real compiler sees |
| Blosc2 | `#error Unable to detect platform` | selected Blosc2 header included by `adapters/blosc2` | Cppcheck preprocessor lacks the compiler/platform identity selected by the recorded C compiler invocation |
| Kernel adapter | `#error "Unknown compiler"` in `linux/compiler_types.h` | recorded kernel translation units use `gcc-13`, `-nostdinc`, kernel generated headers, forced kernel headers, and `-D__KERNEL__` | Cppcheck cannot substitute a Linux kernel compiler environment with generic platform settings |
| SquashFS user-space overlays | three `No header in #include` errors | `cix_squashfuse_decode.c:14`, `cix_sqfsng_compressor.c:16`, and `cix_sqfsng_read_super.c:16` | The include operand is deliberately supplied by an exact build definition such as `CIX_SQUASHFUSE_DECOMPRESS_SOURCE`; standalone analysis has no such definition |
| libbsc / libsais | `#error Your compiler, configuration or platform is not supported` | `vendor/libbsc/libbsc/bwt/libsais/libsais.c:119` checks `__GNUC__`, `__clang__`, `_MSC_VER`, or `__INTEL_COMPILER` | Vendored source requires a real compiler identity. This is not a CIX source defect and must not be patched or suppressed. |

The live adapter Cppcheck project has five compiler-projected inputs. They are
the earlier bounded GIO/7-Zip set, so none proves that the GStreamer, Blosc2,
kernel, or SquashFS contexts above have been projected. The recorded
`compile_commands.cppcheck.json` does contain the real command provenance for
these cases, including the SquashFS source-path definitions and kernel forced
headers. That is the evidence needed to test a bounded extension; it does not
mean generic Cppcheck understands those environments today.

## Header parsing versus compiler context

The native-core failures concentrate in C ABI bridge headers. For example,
`cix_jxl_bridge.h` opens an `extern "C"` block conditionally, declares exported
visibility attributes, and uses C types in a header consumed from both C and
C++. The bridge headers are valid inputs to their owning compiled sources; the
scanner's independent CXX parser reports recovery at the ABI declarations.
The adapter set has the same character: GObject declarations, SDK public
headers, and C profile code generate parser recovery without establishing that
the compiled translation unit failed.

This distinction matters. Adding project-wide definitions for `__GNUC__`,
`__KERNEL__`, `G_DECLARE_FINAL_TYPE`, or the three SquashFS source macros would
fabricate configuration for unrelated inputs. Removing headers from the
analysis scope or suppressing the diagnostics would hide the limitation rather
than analyse the shipped interface. Neither is an acceptable correction.

This is **not** evidence that header coverage is fundamentally unsupported.
The SonarOpenCommunity CXX compiler documentation says that a JSON compilation
database contributes `-D` and `-I` information per compiled file, and describes
a `__global__` database entry for compiler internal defines and include roots
needed by unconfigured headers. Its own page labels that description as valid
for plugin 1.x, whereas this scan pins CXX 2.3.0.1496. It is therefore a
supported configuration route to measure against the pinned analyzer, not an
assumption that can be applied without a receipt. See the
[SonarOpenCommunity compiler documentation](https://github.com/SonarOpenCommunity/sonar-cxx/wiki/Compilers#json-compilation-database-format-specification-support).

## Minimum bounded correction to evaluate after scan v3

Extend the existing **compiler-preprocessor projection** only for the specific
translation units that produce the Cppcheck preprocessing failures:

1. derive each projection from its recorded successful compiler argv and
   working directory, including all forced headers, include paths, and exact
   source-path macro values;
2. retain the original source and command hashes, raw preprocessor output,
   projected output hash, and the normalisation count; preserve source line
   mapping;
3. run Cppcheck on the projected translation unit only after the projection is
   accepted under the existing bounded evidence rules; and
4. leave a diagnostic as an explicit analysis gap when the compiler cannot
   produce a bounded projection or Cppcheck still cannot parse it.

The initial candidate set is the actual GStreamer source, the selected Blosc2
adapter source, the three SquashFS overlay sources, and each recorded kernel
adapter translation unit. A separate source-identity-bound candidate is needed
for `vendor/libbsc/.../libsais.c`; it must use its real vendor build command,
not a hand-written compiler macro. This is one focused preprocessor-context
test, not a new full scan and not a claim that all header-only Sonar parser
recoveries will disappear.

In the same bounded probe, extract compiler internal defines and include roots
from the recorded compiler command, bind them to their compiler identity and
use them only in a `__global__` compilation-database record for headers without
a translation-unit row. Do not hand-write the values. The probe must first show
that the pinned CXX 2.3 analyzer accepts this documented field and that the
resulting header parse findings change as expected. If it does not, retain the
header findings as an explicit analyzer limitation.

## Scope and disposition

* No source, vendor, macro, suppression, or scanner changes were made for this
  review.
* The missing Cppcheck context is actionable only through the exact recorded
  compiler commands. A generic `-D` workaround would make the result less
  trustworthy.
* The `cxx:ParsingErrorRecovery` counts are not proof of compile failure. They
  remain a release-quality analysis coverage gap until the per-file and
  measured `__global__` configuration route succeeds, or its unsupported
  outcome is accepted explicitly with this evidence.
* The PAQ projects also show their own platform-preprocessor diagnostics in
  the live report. They are outside this triage and need their own exact
  compiler-context review; this memo does not treat them as resolved.
