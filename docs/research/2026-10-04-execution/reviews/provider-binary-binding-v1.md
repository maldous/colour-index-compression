# Provider binary binding v1

This read-only review compares retained rebuild outputs with the selected
provider hashes in `distribution-engineering-v4`; it does not select or stage
different libraries.

The retained `bridge-portability-v1` JXL bridge exactly matches the selected
hash. Its four PAQ bridge outputs do not. The v1 receipt is marked failed
because its later spatial step did not finish, but the PAQ and JXL install
artifacts remain available for this comparison. The PAQ source records still
provide reproducible input identity: each has a local root, README digest and
per-file source receipt. They do not demonstrate that this retained rebuild
reconstructs the selected PAQ binary bytes.

The selected spatial bridge is now source-to-binary traceable without changing
the closure. `spatial-counts-v2/source.json` fixes the older snapshot and its
spatial source-file hashes. Its recorded configure, build and install steps use
the codec SDK prefix and install to `spatial-prefix-v8`; that installed file is
the selected `51636…31cf` artifact. The build-directory copy has a different
digest because the retained CMake install script changes its RPATH to `$ORIGIN`;
both retain the same ELF build ID. The newer `bridge-portability-v2` rebuild is
also retained, but it has a different hash and is not substituted.

This closes the engineering trace from the recorded spatial source snapshot and
build/install evidence to the already-selected binary. It makes no legal or
release-acceptance conclusion.
