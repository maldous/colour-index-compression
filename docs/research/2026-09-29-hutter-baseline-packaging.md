# Frozen p26 full-enwik9 baseline packaging

`benchmarks/hutter_baseline_package.py` is an evidence tool for the unchanged
portfolio-26 full-enwik9 baseline. It is deliberately separate from the codec
and must not be read as a submission builder or eligibility claim.

It builds one deterministic ZIP program artifact only after the baseline runner
has written a verified complete `status.json` and `complete.json`, and after the
physical `enwik9.cix` has been checked against their recorded size and SHA-256.
Until then `--allow-pending` produces only a report with null program, archive,
and total fields. It never estimates a score from a source archive or module
byte sum.

The program ZIP has fixed entry ordering, 1980 ZIP timestamps and preserved
source executable modes. It contains the frozen static Python closure, the four
actual p26 native dependencies (`native_ppm`, `native_ppm_decode`,
`native_mixer_rounding`, and `native_legacy_mixer`) and their C++ sources,
selected Python vendor packages including real file-module Brotli,
their `.dist-info` licensing metadata and private libraries, and both frozen
PAQ v215/v216 source trees and their binaries at the exact
`benchmark-work/references/.../build-local/paq8px` paths hardcoded by the
unchanged codec. The launcher changes into its extracted root and starts an
isolated `python3 -S` bootstrap: it supplies only the bundled tree, vendor tree
and CPython standard-library/extension paths, and clears inherited `PYTHONPATH`
and user site packages. Every runtime file is hash-checked against
`freeze-manifest.json`; absent, modified, symlinked, duplicate, or
path-escaping inputs fail closed. The ZIP contains no absolute host paths,
corpus bytes, run receipts, or benchmark artifacts.

The frozen static import inventory currently declares six non-standard roots:
`_brotli`, `brotli`, `imagecodecs`, `numpy`, `pydivsufsort`, and `zstandard`.
`pydivsufsort` is reachable from CIX's BWT/longest-previous-factor acceleration
paths; `zstandard` is reachable in the frozen closure's configured reference
and portfolio support. The tool includes both packages, their `.dist-info`
metadata and any package-private `.libs` directories, even where a particular
enwik9 path may not select them. Any extra, missing, or otherwise unresolved
non-standard root fails closed instead of silently producing a smaller package.

The baseline's split-form arithmetic is exactly:

```
2 * actual deterministic program ZIP bytes
+ actual verified complete enwik9.cix bytes
+ UTF-8 byte lengths of the required positional selectors `encode` and `decode`
+ sum(UTF-8 byte lengths of any additionally declared required options)
```

The multiplier is two total copies because the same program ZIP supplies both
compressor and decoder. This is byte accounting only. The archive's current
launcher requires a compatible external CPython 3.12 interpreter; that
interpreter is explicitly not bundled or counted. The repository also has no
public source release or root OSI license. Thus the output always carries
`BASELINE_ONLY_NOT_SELF_CONTAINED_OR_LICENSED`, even once the arithmetic is
available.

After the live baseline has reached `VERIFIED_COMPLETE_ARCHIVE`, run this while
holding the shared measurement lock and without recompression:

```sh
.venv/bin/python -m benchmarks.hutter_baseline_package \
  --runtime /home/user/src/cix-hutter-baseline-20260929/runtime \
  --freeze-manifest /home/user/src/cix-hutter-baseline-20260929/freeze-manifest.json \
  --static-imports docs/evidence/hutter-prize-20260929/current-cli-static-imports.json \
  --vendor-root /home/user/src/colour-index-compression/.venv/lib/python3.12/site-packages \
  --paq-root /home/user/src/cix-hutter-baseline-20260929/runtime/benchmark-work/references/paq8px-v215 \
  --paq-root /home/user/src/cix-hutter-baseline-20260929/runtime/benchmark-work/references/paq8px-v216 \
  --run /home/user/src/cix-hutter-baseline-20260929/run \
  --program-zip /home/user/src/cix-hutter-baseline-20260929/run/cix-p26-program.zip \
  --report /home/user/src/cix-hutter-baseline-20260929/run/cix-p26-package-accounting.json
```

The path to `site-packages` is intentionally explicit and must be checked on
the actual frozen interpreter before running. The tool charges `encode` and
`decode` even though they are positional operation selectors. It does not claim
that a Python source ZIP is an accepted Prize program form; interpreter,
toolchain and formal submission requirements remain unresolved.

After a verified archive and ZIP have been produced, a safe relocated
import-only preflight may be run after the measurement lock is free. It only
imports the archived command and prints argparse help; it performs no encode,
decode, corpus read, or recompression:

```sh
DEST=$(mktemp -d /tmp/cix-p26-import-preflight.XXXXXX)
unzip -q /home/user/src/cix-hutter-baseline-20260929/run/cix-p26-program.zip -d "$DEST"
"$DEST/cix-p26.sh" --help
```

This confirms only that the relocated Python import closure and CLI help load
under the same CPython ABI used to make the bundle. It does **not** execute a
native backend or PAQ path: those relative runtime paths remain untested until
a separately controlled backend execution check is made. It also cannot
establish that CPython is bundled, that a compiler/Makefile can reproduce all
native objects, or that the source form is publicly released and OSI-licensed.
Those remain explicit qualification gaps.
