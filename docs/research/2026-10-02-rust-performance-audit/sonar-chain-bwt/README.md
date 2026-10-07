# Chain and legacy BWT helper verification

Independent review approves the helper control flow and pre-shift Rice
overflow guards. `packetraw/` preserves parent/candidate direct chain fixture
logs, candidate TSVs, payload/source hashes and executable identities;
byte equality and native restoration are correctness evidence. The explicit
CIXM6 mode 4 archive comparison and reciprocal restore hashes are retained.
The earlier CIXG1 BWT case exercises the separate main encoder and is only
an integration control for these modules.

Resource values are NOT QUALIFIED per native child: service peak/swap
records do not bind the direct parent/candidate child membership and limit
readbacks, and DSO capture is candidate-only. No throughput, peak-memory
improvement or scaling claim is made from these checks. The combined
optimized suite remains due after all reviewed helper changes are merged.
