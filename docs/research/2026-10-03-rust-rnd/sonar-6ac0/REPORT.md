# Current native Rust Docker Sonar checkpoint

Scan v8 completed successfully and compute-engine status is SUCCESS for source
6ac05f8e9fd78ff01e2f8d71e6557c5dc66bb8bb, tree9b3cd2a8abec9fcdbd64e2f48b5bc9bb49f46133.
Latest Linux-amd64 Docker images were resolved then pinned by digest; exact
server/scanner versions and identities are in run-v8/manifest.json. This is not
the locally installed Sonar server. Only dedicated CIX containers were used,
then stopped. Token revocation succeeded. No GitHub Actions or publication.

82 files indexed, Rust Sonar-way analysis completed. Clippy import had zero
current rule records and zero importer drops; the separate all-target/all-feature
Clippy log retains241 compiler dead-code warning target instances. Vendor C/C++
was outside this Rust scan. Experimental sources outside src/tests/examples/
benches are not qualified by this scan.

Three Rust S3776 complexity findings remain: chain.rs:1247 (25), main.rs:2886
(17), main.rs:3830 (31), threshold15. These are not zero-issue results; quality
gateOK with no conditions is not a waiver. Small behavior-preserving helper
refactors are being prepared under a new source identity before release.

The live Docker and host-PID cgroup receipts prove server4GiB/scanner1GiB,
CPUs24,25/twoCPUquota/no swap. Bounded tmpfs caps: data1GiB, logs128MiB,
servertemp1536MiB, scannertmp512MiB (executable for provisionedJRE). Aggregate
declared temporary capacity is below4decimalGB; image-declared extensions
volumes and Docker image storage are not codec temporary spooling. The root
WaveScheduler lease covers the aggregate scan and is released after cleanup.

Preserved failed attempts: v3 cgroup-parser identity failure; v4 servertemp
plugin extraction ENOSPC; v5 password policy400; v6 missinghostname executable;
v7 provisionedJRE blocked by noexec tmpfs. None was a completed analysis.
Failure descriptions are in sonar-4af6/HARNESS-FAILURES.md. Their frozen harness
hashes are preserved but not every early mutable harness snapshot was durably
copied; do not claim fully reconstructable historical failed launchers. Final
v8 source and scheduler bytes were copied before dispatch and match the freeze.
Logs are scrubbed of credentials; credential files were removed.

Scanner Docker inspect environment token values were redacted after revocation
before committing. Historical executed harness snapshots stay unchanged. A
future harness now redacts credential environment fields before writing them.
