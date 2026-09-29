# Post-run PyInstaller packaging recipe for frozen CIX p26

This recipe is a bounded way to **measure** a self-contained Linux x86-64
program form for the unchanged p26 baseline. It does not make the current
archive eligible, and it must not run until the existing full baseline has
completed and released its measurement boundary.

PyInstaller 6.22.3 is the planned bundler. Its official documentation states
that it packages the active Python interpreter and collected modules into a
folder or a single executable; it is OS/Python/word-size specific. It also
documents that imports made dynamically need explicit collection. The generated
plan therefore uses one-file mode with an explicit data mapping of the frozen
static closure and passes the same closure as hidden imports, rather than
trusting automatic discovery. This deliberately lets PyInstaller collect the
standard-library imports needed by source modules loaded from the extracted
runtime. See the official
[operating-mode documentation](https://pyinstaller.org/en/stable/operating-mode.html)
and [usage reference](https://pyinstaller.org/en/stable/usage.html).

The local host has no PyInstaller executable now. After the baseline, acquire
the exact 6.22.3 wheel in a fresh, recorded packaging environment; retain the
download URL, wheel filename, SHA-256, installer Python version, platform and
`pip --version`. Then install only from that retained wheel with
`--no-index --require-hashes`. Do not change the frozen measurement virtualenv.
The initial wheel SHA-256 is deliberately not guessed in advance; it becomes a
recorded immutable input at acquisition.

Run the preparation tool only after `run/status.json` and `run/complete.json`
both say `VERIFIED_COMPLETE_ARCHIVE` and the physical archive still matches
their SHA-256:

```sh
.venv/bin/python -m benchmarks.hutter_selfcontained_package \
  --runtime /home/user/src/cix-hutter-baseline-20260929/runtime \
  --freeze-manifest /home/user/src/cix-hutter-baseline-20260929/freeze-manifest.json \
  --static-imports docs/evidence/hutter-prize-20260929/current-cli-static-imports.json \
  --vendor-root /home/user/src/colour-index-compression/.venv/lib/python3.12/site-packages \
  --paq-root /home/user/src/cix-hutter-baseline-20260929/runtime/benchmark-work/references/paq8px-v215 \
  --paq-root /home/user/src/cix-hutter-baseline-20260929/runtime/benchmark-work/references/paq8px-v216 \
  --run /home/user/src/cix-hutter-baseline-20260929/run \
  --output /home/user/src/cix-hutter-baseline-20260929/package-plan
```

It writes a hash-bound entrypoint, PyInstaller spec and plan; it does not invoke
PyInstaller, copy the payload, or report executable bytes. The entrypoint
resolves input and destination to absolute paths before changing into its
extracted `runtime` directory, clears caller `PYTHONPATH`, makes PAQ v215/v216
executables runnable after one-file extraction, then invokes the unchanged
`benchmarks.competitive_cli`.

The later build must first use `--onedir` and validate it before one-file mode.
PyInstaller itself recommends this order because one-file debugging is harder.
The spec has no `COLLECT`, so it is one-file; use `upx=False`, because current
PyInstaller documentation says UPX does not process Linux collected binaries
and modern Linux libraries can break under it.

Required post-build evidence:

1. Hash the generated executable and record its physical byte count. Count it
   twice for split compressor/decompressor accounting, plus the measured
   archive and UTF-8 bytes of the `encode`/`decode` selectors.
2. Run from an empty temporary working directory with `PYTHONPATH` and user
   site deliberately poisoned, then verify `--help` imports only the bundle.
3. Run isolated tiny backend smoke fixtures that actually execute each bundled
   native PPM/mixer library and both PAQ binaries; help output alone does not
   prove those runtime paths.
4. Run an isolated full decode of the measured baseline archive and confirm the
   canonical SHA-256. A later encode check must have its own whole-process
   resource evidence; do not reuse baseline timing.
5. Record the one-file extraction directory's peak temporary bytes and process
   tree RSS. PyInstaller extracts support files to a temporary `_MEI...`
   directory, which counts toward the Prize temporary-disk limit.

The frozen vendor inventory is large, but its raw file sum is not a measured
executable size or proof of infeasibility. The actual one-file executable size
must be measured after the controlled build. PyInstaller normally relies on
standard Linux `/lib` and `/usr/lib` libraries rather than bundling them. For
the present host, the CPython/native closure uses system ABI components
including the ELF loader, glibc, libm, libz, libexpat, libstdc++, libgcc and
libgomp. Whether those system components may remain external must be resolved
conservatively against the Prize rules; if bundled, their exact bytes and
licenses must be added to the counted program form.

Remaining gaps are not fixed by bundling: CIX lacks a root OSI license and
public source release; third-party license notices and source/build provenance
need an audit; the PyInstaller bundle does not by itself establish a preferred
submission form; and only the Prize reviewers can grant approval.
