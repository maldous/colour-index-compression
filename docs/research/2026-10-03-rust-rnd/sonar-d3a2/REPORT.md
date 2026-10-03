# Fresh Docker Sonar after helper refactoring

Source d3a2cd416e49f93403d1dbd348a3e9a45db66ec6; exact tree/image/Clippy hashes
in run-v1/manifest.json. Both scanner and compute-engine completed successfully.
82 files indexed with Rust Sonar-way profile. Current issues:0. Clippy importer
received0 current rule records, no dropped diagnostics. Earlier three S3776
findings from6ac are resolved at this source. Compiler dead-code notices remain
outside the zero-Sonar-rule claim. Experimental adapters and vendorC++ are
outside the Rust source scope.

Server/scanner are fresh pinned latest Docker images, not the locally installed
server. Frozen executable tmpfs and role/host-PID cgroup checks passed. Dedicated
containers stopped, token revoked and envfile removed. Inspect credential fields
are redacted before writing. CPU24,25/quota2/no swap; server4GiB/scanner1GiB,
root reserved6GiB and4decimalGB temporary ceiling. Final scan creates no public
service, GitHub Action or workflow change. See raw receipts and freeze for limits.
