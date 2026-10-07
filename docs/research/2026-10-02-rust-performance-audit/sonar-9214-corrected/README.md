# Corrected local Sonar scan: 9214e2f8b

The frozen source scan completed without a Clippy JSON parse error. It used
compact normalized NDJSON, retaining the original Cargo output separately.
The quality gate **failed**: 39 native complexity findings and 51 imported
Clippy findings remain. `gstream.rs` has no remaining native complexity issue;
`main.rs` has 14. This is not complete cleanup or full code correctness proof.

Sonar does not import the entire compiler diagnostic set. The 183 normalized
diagnostics include 102 `dead_code` and 12 `duplicate_mod` diagnostics. Newer
`chunks_exact_to_as_chunks` (3) and `manual_isolate_lowest_one` (5) diagnostics
are explicitly reported as unsupported by this scanner. Example/alias paths
and compiler-only diagnostics remain visible in the raw export even when the
Sonar source/test inventory does not represent them. Use the manifest's complete
code counts and raw export when reviewing all warnings, rather than treating
the 51 imported findings as the entire warning set.

`manifest.json` records the source tree, hashes, exact counts and server Docker
resource readback. `scan.log` records the scanner result; `issues.json` retains
the complete open inventory. Native rules cover Rust; this scan does not
establish vendor C/C++ or dependency security qualification. Computation was
local, without GitHub Actions.
