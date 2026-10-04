# Frozen native build continuation

The source snapshot is based on `8d143466274ad2aaaadbf6f1ef0b9c7ec23c3cc8`.
The release and benchmark gates remain open. None of these steps is a corpus
benchmark or a claim that the distribution is ready.

`native-final-source-v1` completed the allowlisted engineering export but its
format command omitted `--all` for the virtual workspace. It stopped before
compilation. The v1 export, logs and receipt are retained; only its unused,
byte-identical copy of the separately retained LTO cache was reclaimed after
full comparison in `native-final-v1-cache-reclaim`.

`native-final-source-v2` passed workspace formatting. Clippy then rejected the
runner's `CARGO_PROFILE_RELEASE_LTO_DEBUG` setting before compilation: Cargo
interpreted it as a nested release-profile setting. The product source did not
change. A continuation removes that runner setting and reuses v2's immutable
export and qualified workspace lock, with hashes checked before and after.

The attempted v2 cache reclamation correctly stopped because the copy was no
longer identical. Inspection found one changed Cargo metadata file,
`.rustc_info.json`; the original retained cache was unchanged. The failed
reclamation receipt remains evidence, and reclamation requires preserving the
changed member before removing any duplicate data.

`native-final-v3-cache-reclaim` subsequently preserved and verified that member,
then reclaimed only the duplicate cache. `native-final-source-v3` reused the
unchanged v2 source and passed all-target Clippy with Rust warnings denied,
the optimized `release-lto` build of all three CLI binaries, and seven focused
integration tests (one ZPAQ, two full-engine constraints, four CLI smoke tests).
It completed in 104.68 seconds; this is a build/check duration, not compressor
throughput. External compiler warnings remain recorded.

The alias-test filter in v3 selected zero tests. The independent review marks
that gap explicitly despite the producer's successful exit. The continuation
`native-alias-filter-v1` ran the exact
`cli::policy_tests::program_name_normalization_is_platform_specific` test
against the same hash-bound test binary and verified that one test ran and
passed. This checks platform-name logic on Linux, not Windows execution.
The integration and unit tests used the default test profile; the CLI binary
build used the optimized profile. Neither is a full regression rerun or final
provider, package, platform or RC51 acceptance.

Before these jobs, `preserve-debug-cache-v1` preserved the former shared debug
cache in a verified archive before reclaiming it. The archive is 28,738,602
bytes with SHA-256
`1b70bff84b27e31b2f7628ee5297458029b8558aa3e6e189d1afe6264dadb5c8`.
Every member's content, mode and link identity was verified. Its manifest and
receipt remain under the job directory; the archive remains in shared work.
Compiler records referencing the old live debug-cache paths must use a new
capture or explicit verified restoration, not silently assume those paths
still exist. Guard and archive-round-trip fixtures passed in
`cache-preservation-tests-v1` and `cache-preservation-tests-v2`.
