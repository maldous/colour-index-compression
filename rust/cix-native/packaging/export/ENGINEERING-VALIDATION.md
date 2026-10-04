# Engineering full-engine export validation

This local dispatch recipe exercises the complete **selected Linux provider
closure** without claiming a release. It is intentionally separate from the
`full-engine-rc` profile: a successful run writes
`engineering_validation_not_release` and must never create or mark
`final-dependency-closure.json` accepted.

The scheduler first writes a private provider manifest from the exact selected
bridge and companion artifacts. Start with
`engineering-provider-closure.example.json`, replace every path, digest, and
source/package provenance field, and set its status to
`engineering_inputs_selected`. The manifest must name these actual inputs:

- all four PAQ bridge DSOs;
- JXL and spatial bridge DSOs;
- libjxl, libjxl_threads, libjxl_cms, all three Brotli libraries, CharLS, and
  OpenJPEG companions;
- an explicit `readelf`; and
- pinned source or reproducible package identities, licence expressions,
  notice locations, and provisioning records for each provider family.

Run only under the shared scheduler resource policy, using a new bounded work
directory:

```sh
python3 rust/cix-native/packaging/export/engineering_export_job.py \
  --source-root rust/cix-native \
  --manifest rust/cix-native/packaging/export/source-allowlist.json \
  --provider-closure /absolute/private/selected-provider-closure.json \
  --work-directory /absolute/new/bounded-work \
  --cargo /absolute/path/to/cargo \
  --cmake /absolute/path/to/cmake \
  --make /absolute/path/to/make \
  --jobs 2
```

The recipe materialises the same allowlisted two-crate workspace as a public
export, generates its root workspace lockfile offline, checks Cargo metadata
with `--locked --offline`, builds the selected LTO native executable and SDK,
stages it, installs the explicit provider closure into `usr/lib/cix`, verifies
selected input and installed hashes, and invokes the three installed command
aliases with `--version`.

It does **not** test provider encode/decode behavior, package-manager output,
non-Linux targets, host adapters, or release acceptance. Those remain separate
focused receipts and RC44/RC45/RC49 acceptance work.
