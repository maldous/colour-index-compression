# Fixed PubChem 2-D molecular transfer batch

This is a separate raw source dataset from the 3-D batch, using the same
predeclared CID order: 1983, 2244, 2519, 3672, 5793, 5950, 681 and 702. All
eight official PubChem PUG-REST 2-D SDF responses returned and were retained as
raw bytes. No coordinate conversion, SDF reserialization, or artificial
hydrogen generation occurred.

Literal concatenation in the declared order is 29,088 bytes with SHA-256
`a337dc43a915618cb2e57ef7e419eb9466ed292deccb3ec875e9049f07c50d1e`.
The complete `hydrogen_slots_v1` frame is 25,968 bytes and archive-only
decoding restores the exact source hash. Eight V2000 records (166 atoms) are
parsed; the terminal empty record remains a paid literal exception.

This supplied 2-D layout gives 81 predicted atoms and 27 candidate-order
choices. The current representation-0 choice stream occupies 27 bytes, while
the fixed candidate product has an ideal 32.850-bit combinatorial description.
That difference is only a theoretical representation question. PAQ may already
share the relevant coding capacity after receiving the full frame, so no forced
rank variant was added for a two-byte-scale hypothesis.

The original 2-D batch and complete fixed frame will be compared separately
from the 3-D batch using the same future pinned PAQv216 `-4` AVX2 invocation.
That execution has not run. Per-CID response hashes, URLs, preparation and
frame accounting are in
[`molecular-pubchem-2d-batch.json`](molecular-pubchem-2d-batch.json).
