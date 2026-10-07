# Graph completion: SDF hydrogen

Native ownership is `rust/cix-native/src/full_engine/graph_residuals.rs`.

The retained reference is `runtime/cix_runtime/legacy/sdf_hydrogen.py` from the
frozen integrated source.  Native `SDFH\x01` now accepts all historical model
and choice pairs: models 0, 1, and 2 with representations 0, 1, 2, and 3.
`encode_hydrogen` remains the compatibility model-0/representation-0 entry;
`encode_hydrogen_with_options(data, model, representation, radius)` exposes
the complete reference matrix for full-engine callers.

Models 1 and 2 retain the reference topology restrictions, integer CORDIC
angle/direction arithmetic, candidate ordering, consumed hydrogen-slot state,
nearest-candidate tie break, mixed-radix little-endian rank, and static or
adaptive arithmetic choice state.  Parsing failures still retain that source
record literally, matching the Python fallback.  The decoder rejects invalid
models, noncanonical/truncated framing, bad choice symbols, unused rank/digit
state, malformed skeletons, output-limit violations, and coordinate overflow.

The in-module candidate fixture is generated source data, not corpus material.
It has two interchangeable hydrogen slots, so model 2 exercises literal,
rank, static-arithmetic, and adaptive-arithmetic choices.  Its Python reference
choice payloads are `30`, `00`, `0320`, and `0320` for representations 0–3.
The focused test covers all 12 model/representation combinations, exact choice
payload parity for that nontrivial model-2 vector, round-trip restoration, and
the pre-existing model-0 signed-zero/fallback/bounds checks.  Root owns the
scheduled Rust compilation and test execution.
