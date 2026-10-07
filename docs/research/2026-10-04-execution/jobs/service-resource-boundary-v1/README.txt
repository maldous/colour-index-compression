CIX-132: managed export and zero-temporary-storage source candidate

Source phase only. No Rust compilation, Cargo resolution, dependency fetch,
service test execution, listener, codec job or benchmark ran under this lease.
The three newly authored tests are UNRUN. rustfmt parsed the four edited files
successfully with --emit stdout and skip_children=true; this checks syntax only,
not types, linkage, behavior or service security.

Exactly four product paths changed from the captured preimages:
  rust/cix-native/src/lib.rs
  rust/cix-native/src/service/contracts.rs
  rust/cix-native/src/service/engine.rs
  rust/cix-native/tests/service_contract.rs

The library exposes the already tested process-free managed_sdk module.
ResourceLimits::within accepts zero temporary storage as a prohibition, still
rejects a nonzero request above a zero cap, and keeps every other resource's
positive lower bound. Engine::validate refuses zero temporary storage because
this worker always creates temporary files. Jobs::submit invokes this validator
before repository admission; Engine::execute invokes it before object access,
temporary-directory creation or process launch. No global RSS guarantee follows.

Authored tests cover zero and nonzero temporary caps, unchanged positive-resource
requirements and upper limits, Config preserving zero, rejection before provider
lookup, no queue entry, and direct execution refusal before storage effects.
Their isolated fixture uses an in-memory metadata repository, synthetic identities,
no credentials, no provider directory and no input artifact. These are future
acceptance assertions, not successful execution results.

All original service tests and Principal fixture literals are byte-preserved.
Config/Principal/Job schemas, authentication, policy evaluation, Cargo manifests
and lockfile, repository, jobs, storage, CLI and other owners' source are unchanged.
Eighteen read-only bindings were verified. Full service dependencies are not yet
in the current Cargo.lock; actual compiled qualification needs a separately
admitted, pinned dependency closure and hard resource/scratch limits. No stub
implementation or default-feature build can qualify the server feature.

Read preimages.json, change.patch, source-checks.json, postimages.json and the
candidate manifest together. preimage/ and source/ preserve exact before/after
bytes independently of later working-tree changes. Captured rustfmt stdout is
parser output only and is not the product source.

Admission: 53398d37-2626-44ac-b318-fb0ecc07510b
Exclusive source claim: db850f34-530d-4c46-89bc-88de8dde306f
Contract: cd8eebc3-ba2d-40ea-904f-a5f2d1e8af9b
Prior dossier review: a4e8099c-c43a-49e3-8099-fbedec39dd02
Root integrator: 01a0f927-3e23-7cb1-bdc3-cb7d08783ade
Quinn independently reviews this exact source candidate after root release.
Morgan coordinates the next dependency/compiled-check contract. Original SDK,
service and localization owners retain their historical ownership records.
No broader authentication, confinement, complete service or RC acceptance.
