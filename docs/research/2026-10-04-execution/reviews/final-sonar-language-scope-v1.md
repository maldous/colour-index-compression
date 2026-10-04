# Final Sonar language scope (RC47)

**Status:** planning evidence only.  This review did not start a scanner, a
container, a build, a network request, or alter source code.

## Decision

RC46's C/C++ result and RC47's final Rust/Python result are separate, fresh,
source-identity-bound analyses.  The CXX runner must finish first, then the
root scheduler must run a language-enabled Sonar server against the same frozen
integrated/exported source identity.  A successful CXX run cannot be described
as Rust or Python coverage.

The reason is explicit in the completed CXX registration proof:

* [`probe-v9/raw/omitted-core-extensions.json`](../sonar-preparation/probe-v9/raw/omitted-core-extensions.json)
  records a read-only empty mount over `/opt/sonarqube/lib/extensions`, omitting
  the Rust and Python analyzers along with the other built-in analyzers.
* Its [`languages.json`](../sonar-preparation/probe-v9/raw/languages.json)
  reports only `cxx`, and its result calls the outcome a CXX registration and
  null-pointer probe, not a product scan.
* The base-image inventory in
  [`probe-v6/raw/image-core-extension-inventory.json`](../sonar-preparation/probe-v6/raw/image-core-extension-inventory.json)
  does contain `sonar-rust-plugin-1.8.1.3395.jar` and
  `sonar-python-plugin-5.31.0.36502.jar`.  That inventory is evidence of what a
  normal image can provide; it is not evidence that those analyzers were present
  in the CXX-only server.

## Final source scope

Freeze a new manifest and SHA-256 tree digest after the last RC47 source edit
and before either final scan.  The manifest must list the scanner selections
below, their file hashes, the image digests, project properties, Clippy JSON
hash, issue export, completed-analysis receipt, indexed-file list, and quality
gate response.  Any selection changed after the manifest invalidates its scan.

| Project | Required final selection | Exclusions and interpretation |
| --- | --- | --- |
| `cix-final-rust` | `rust/cix-native/src/**/*.rs`; Rust tests selected for the final export | Exclude `target`, generated scanner work, research/evidence, vendor trees, and non-Rust files. Import the fresh root-owned Clippy JSON. This is required RC47 product-code coverage. |
| `cix-final-python-binding` | `rust/cix-native/bindings/python/src/**/*.py` and `bindings/python/tests/**/*.py`, if those files remain in the materialised full-engine export | The current allowlist includes `bindings/**`; the binding README states that it is an optional `ctypes` consumer of an installed native library. Scan it as an optional supported binding, in a separate project. It does not make Python a dependency of the `cix` executable. |
| `cix-final-python-adapter-tools` | Only Python adapter/example/qualification files actually selected by the final export manifest, such as `adapters/hdf5/examples/h5py_filter.py`, `adapters/squashfs/tools/qualify.py`, and `adapters/wasm/*.py` | Run when the matching adapter is shipped/claimed. Keep it separate from the binding and report the selected file list. Do not silently turn an omitted adapter into a product-runtime requirement. |

`packaging/export/*.py`, experiment drivers, fixture generators excluded by the
allowlist, private repository research, and prior `runtime/cix_runtime` are not
part of the above product scan unless a later final-export manifest explicitly
selects them.  In particular, the predecessor's `runtime-python` project must
not be revived: the controlling requirement says the finished CIX executable
runs without Python or a Python subprocess, while Python remains reference/test
tooling or an optional consumer binding.

C/C++ stays in the CXX runner's separate CIX-owned and vendor-visible projects.
Vendor findings remain visible but never authorize third-party edits.  Rust and
Python zero-issue claims must be made only for their own project key and frozen
selection; they do not claim C/C++ closure.

## Reusable execution basis, after CXX

Use `tools/sonar-cxx/repair.py` for the first, fresh CXX execution only, with a
new preparation/output directory and its existing authenticated stop, idle,
exclusive lease, four-core, 5 GiB no-swap controls:

```sh
python3 tools/sonar-cxx/repair.py prepare \
  --out docs/research/2026-10-04-execution/sonar-preparation/prepared-vNEXT
python3 tools/sonar-cxx/repair.py run \
  --prepared docs/research/2026-10-04-execution/sonar-preparation/prepared-vNEXT \
  --out docs/research/2026-10-04-execution/sonar-preparation/scan-vNEXT
```

The retained language-enabled basis is
[`hygiene/run_scan.py`](../../2026-10-04-automatic-specialised-models/hygiene/run_scan.py)
and [`hygiene/final-scan-spec.json`](../../2026-10-04-automatic-specialised-models/hygiene/final-scan-spec.json).
They pin the already-recorded SonarQube image
`sha256:4905574ab8584dcac1a06c01cdc43a4ce9e369723ac4a7ab1d029c1bf71e6fe9`
and scanner image
`sha256:a3f4215076706c95a17a68c19322ee916e40a3acd081a8c1a1e839e0194afa57`,
read both images locally without pulling, generate/revoke a per-run token, and
write raw image, issue, gate, and completed-analysis receipts.

That harness is reusable for its resource/accounting behaviour, **not runnable
unchanged**: it hard-codes a retired standalone source and a retired
`runtime/cix_runtime` Python project.  The scheduler owner must make a new
CIX-owned final-scope configuration with the project table above and retain it
beside the new output.  It must not point that configuration at the historical
runtime tree.  Its invocation shape is:

```sh
python3 docs/research/2026-10-04-automatic-specialised-models/hygiene/run_scan.py \
  --lease <fresh-active-lease.json> \
  --native-source <frozen-final-export> \
  --runtime-source <frozen-optional-python-selection-root> \
  --freeze <new-final-scope-freeze.json> \
  --clippy-json <fresh-final-clippy.jsonl> \
  --cgroup-parent <leased-cgroup> \
  --out <new-unused-attempt-directory>
```

The adapted final-scope configuration must set Rust properties equivalent to:

```text
sonar.sources=src
sonar.tests=tests
sonar.inclusions=src/**/*.rs
sonar.test.inclusions=tests/**/*.rs
sonar.rust.clippy.enabled=false
sonar.rust.clippyReport.reportPaths=/out/clippy.jsonl
```

and one Python project per selected optional scope, with explicit
`sonar.sources`, `sonar.tests`, `sonar.inclusions`, `sonar.test.inclusions`,
`sonar.exclusions=**/__pycache__/**,**/*.pyc`, and the Python version recorded
from the actual final environment.  It must query `/api/languages/list` and
fail the respective required scan if `rust` or `python` is inactive.  Scanner
success alone is insufficient: record indexed files and reject missing selected
files before accepting issues/gate output.

## Resource and ordering constraints

No final source scan runs concurrently with a build, benchmark, or the other
Sonar server.  The CXX runner already reserves four cores and 5 GiB without
swap.  The reusable Rust/Python harness reserves four cores, a 4 GiB server,
and one 1 GiB scanner with swap capped at the memory limit; run its projects
serially against that server.  Its recorded mounts are read-only source, a
512 MiB executable `/tmp` scanner tmpfs, and bounded server tmpfs areas.  The
root scheduler must charge those allocations and the retained evidence/output
directory against the shared decimal 12 GB RAM, decimal 4 GB temporary-space,
and no-swap policy before acquisition.  A new cap/space receipt is required;
old directory-size observations are not sufficient.

Run final formatting and fresh Clippy first so the imported report has the
frozen source hash.  Then run CXX, then the language-enabled Rust scan, then
the selected optional Python projects.  Preserve every failed attempt in a new
directory and repair only CIX-owned code/tooling.  Re-run the affected project
after a repair and refresh the manifest; do not reuse a prior clean result.

## Stale predecessor evidence

The following stays useful as historical/tooling evidence but cannot close
RC47 for the current integrated source:

* `docs/research/2026-10-04-release-0.1/sonar-release/run-v1` and `run-v2`:
  their manifests bind earlier standalone-export tree hashes.
* `docs/research/2026-10-03-rust-rnd/sonar-6ac0/run-v8` and earlier Rust Sonar
  runs: different source identities and pre-integration code.
* `docs/research/2026-10-04-automatic-specialised-models/hygiene-plan.md` and
  `hygiene/final-scan-spec.json`: preparation based on the retired
  `runtime/cix_runtime` scope, not an execution receipt for this export.
* CXX probes `probe-v3` through `probe-v9`: useful plugin/configuration proof;
  intentionally CXX-only and explicitly not product-language coverage.
* `prepared-v1`, `prepared-v2`, and `prepared-v3` CXX plans: preparation and
  compiler-closure evidence, not a completed final-source scan.

This plan creates no Python runtime obligation.  It requires static analysis
only for optional Python surfaces retained and claimed by the final export.
