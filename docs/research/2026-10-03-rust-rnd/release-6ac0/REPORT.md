# Current-host release qualification

Source: `6ac05f8e9fd78ff01e2f8d71e6557c5dc66bb8bb`.
Portable all-feature release-lto binaries are sealed in
`benchmark-work/release-6ac0/final/`; paths and SHA-256 are in native-release.json.
The metadata scope was written before subsequent streaming qualification and
is retained unchanged; qualification-6ac0/REPORT.md records that later evidence.

Build succeeded. Eight focused CLI checks passed: old M6 archive decoding,
valid CIXF1 metadata, invalid filename length/UTF-8/trailing data rejection,
explicit unsupported parallelism and decode compression-option rejection,
and kept-open footer interruption (exit 2, about 1.1 ms, no forced kill).
The exact rank byte-equivalence/malformed test passed at f579; rank.rs is
unchanged here. Large streaming rows and old Rust compatibility are separately
bound to these binary hashes in qualification-6ac0/.

Clippy all targets/all features exited zero: no Clippy-rule or unused-variable
diagnostics, but 241 dead-code compiler warning target instances remain.
This is not an all-warnings-clean or full-suite claim. Latest Docker Sonar
qualification is separate and was not completed by the initial launch.

Live receipts include cgroup identity/path, CPU quota 200000/100000, CPUs 8,10,
no swap, 2 GiB build/Clippy memory and 256 MiB focused-CLI memory caps.
Toolchain/hardware/hash capture occurred during the build, not before it;
do not describe it as a pre-bound toolchain freeze. No Actions were used.
