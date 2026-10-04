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
