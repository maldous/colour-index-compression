# CIX source export

`source-allowlist.json` defines the only files that may enter a public CIX
source tree. It deliberately excludes the enclosing private repository's
research, corpus data, benchmark output, job receipts and development build
products.

Validate first, then materialise a new source directory. The default profile
is `full-engine-rc` and refuses to export until the selected runtime dependency
closure has an accepted receipt:

```sh
python3 packaging/export/validate_source_allowlist.py \
  --source-root "$PWD" \
  --manifest packaging/export/source-allowlist.json \
  --profile full-engine-rc
python3 packaging/export/export_source.py \
  --source-root "$PWD" \
  --manifest packaging/export/source-allowlist.json \
  --output-directory /absolute/new/export-directory \
  --profile full-engine-rc
```

The exporter creates `/absolute/new/export-directory/cix-0.1.0` with a root
Cargo workspace and both required crates under `rust/cix-native` and
`rust/cix-portable`. The portable crate continues to use workspace-relative
imports of selected native core modules; it does not duplicate the algorithms.
It also projects `rust/cix-native/packaging/debian` to the conventional root
`debian/` directory and writes a member-hash manifest.

The workspace lockfile must be generated offline from these two exact member
crates and checked before `--locked` build or package commands are accepted.
The exporter does not create an archive, sign, publish, upload, build, or
install anything. `native-core-optional` is intentionally not a substitute for
the full-engine release candidate; it needs its own declared capability set.

For a bounded non-release build/install exercise with the selected Linux provider closure, see [ENGINEERING-VALIDATION.md](ENGINEERING-VALIDATION.md).
