# Distribution engineering v1 — prepared dispatch

This is a **prepared, not executed** source-export/build/install exercise. It
uses the concrete selected Linux x86-64 providers in
`selected-provider-closure.json` and deliberately remains an engineering
receipt. It cannot accept RC44, RC45, RC49, or the full-engine release gate.

## Inputs bound before dispatch

- Native source root: `rust/cix-native`.
- Export manifest and engineering runner:
  `rust/cix-native/packaging/export/{source-allowlist.json,engineering_export_job.py}`.
- Selected providers: `selected-provider-closure.json`.
- Existing evidence: runtime closure v2 and relocated providers v4, named in
  that manifest. Their bridge/companion hashes are inputs, not proof that the
  fresh exported build is compatible.
- Cargo registry/cache may be reused offline. No built native target output may
  be reused: the runner uses a fresh `CARGO_TARGET_DIR` under its work root.

## Scheduled command

Run only from the project root after the scheduler has created a new work
location with the shared resource policy:

```sh
python3 rust/cix-native/packaging/export/engineering_export_job.py \
  --source-root rust/cix-native \
  --manifest rust/cix-native/packaging/export/source-allowlist.json \
  --provider-closure docs/research/2026-10-04-execution/jobs/distribution-engineering-v1/selected-provider-closure.json \
  --work-directory /absolute/new/distribution-engineering-v1-work \
  --cargo /absolute/path/to/cargo \
  --cmake /absolute/path/to/cmake \
  --make /absolute/path/to/make \
  --jobs 2
```

The runner materialises the engineering profile, creates the root workspace
lockfile with `cargo generate-lockfile --offline`, verifies Cargo metadata with
`--locked --offline`, builds the LTO CLI/SDK from exported sources, stages the
SDK and aliases, verifies every selected PAQ source file against its recorded source receipt, then
copies only those files with the recorded GPL-2 text and staged-file identity metadata, stages the 14 selected provider files through the runtime
CMake contract, and records input/installed hashes. It does not run corpus
work, a benchmark, package-manager build, or provider compression tests.

## Capacity admission

The current aggregate temporary-work allowance is 4,000,000,000 bytes. The
source trees excluding existing targets are about 6.15 MB; the prior selected
provider prefixes total about 53 MB. The fresh LTO `CARGO_TARGET_DIR` is the
unknown dominant allocation and must not reuse `rust/cix-native/target` as
proof of an exported build. The existing native target is about 6.85 GB and
therefore cannot fit in this work allowance.

The scheduler must admit the job only while the one-gigabyte temporary-work
reservation in `spec.json` is available. Do not dispatch if concurrent work makes
that reservation unavailable; create the fresh bounded work root and monitor its
combined source-output, target, runtime-build, and stage size. The
runner's `--jobs 2` limits Cargo parallelism, but a filesystem quota or
scheduler reservation is still required to enforce the aggregate byte cap.

## Known closure gaps recorded, not waived

The selected PAQ bridge artifacts, source roots, receipt-verified per-file hashes,
and GPL-2 text are bound for this engineering staging exercise. This
records source text and identity only; it does not make a legal determination or
accept a public release closure. libjxl/Brotli and CharLS/OpenJPEG have local licence-source
records, but a release still needs selected source/package provenance and
redistributable notice handling. None of this authorizes a project licence or
final dependency-closure acceptance.
