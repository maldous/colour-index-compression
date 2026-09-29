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

The program ZIP has fixed entry ordering, 1980 ZIP timestamps and modes. It
contains the frozen static Python closure, the four selected native
PPM/mixer artifacts and their source, selected Python vendor packages including
their `.dist-info` licensing metadata and private libraries, both frozen PAQ
v215/v216 source trees and their built binaries, plus a fixed launcher. Every
runtime file is hash-checked against `freeze-manifest.json`; absent, modified,
symlinked, duplicate, or path-escaping inputs fail closed. The ZIP contains no
absolute host paths, corpus bytes, run receipts, or benchmark artifacts.

The baseline's split-form arithmetic is exactly:

```
2 * actual deterministic program ZIP bytes
+ actual verified complete enwik9.cix bytes
+ sum(UTF-8 byte lengths of declared required options)
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
the actual frozen interpreter before running. No `--required-option` is used
for the current launcher: `encode INPUT ARCHIVE` and `decode ARCHIVE RESTORED`
are positional operations, so the reported required option count is zero.
