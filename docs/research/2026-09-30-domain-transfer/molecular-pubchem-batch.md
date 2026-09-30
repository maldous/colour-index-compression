# Fixed PubChem 3-D molecular transfer batch

This is a fixed, small cross-molecule transfer batch for a future matched PAQ
comparison. It is not representative molecular-domain evidence, a PAQ result,
or a compression claim. The original caffeine fixture remains a
**weak-opportunity correctness case** because its supplied 3-D atom order gave
zero hydrogen choices.

Before acquisition, the CID order was fixed as 1983, 2244, 2519, 3672, 5793,
5950, 681 and 702. All eight official PubChem PUG-REST 3-D SDF requests
returned successfully; none was replaced or omitted. Each response is retained
unmodified with its URL, byte count and SHA-256 in
[`molecular-pubchem-batch.json`](molecular-pubchem-batch.json). Their literal
concatenation in the declared order is 29,663 bytes with SHA-256
`3573383c76595b726b49f3e8fec1a87ba8f248f606c3ac1240af37c22ebc3ce3`.
No separator was added and no SDF was reserialized.

`hydrogen_slots_v1` decodes this complete batch from its 27,568-byte structural
frame alone. It accepted all eight returned molecules (166 atoms) and paid one
trailing empty record literally. The frame includes 7 header bytes, 3 bytes of
radius/count varints, 2 flag bytes with 7 padding bits, 3 bytes of skeleton
length, 24,849 skeleton bytes, 1 choice-length byte, 3 choice bytes, and 2,700
coordinate-residual bytes. These components sum exactly to the frame size.

The supplied 3-D batch has six atoms with reconstructible candidate slots and
three candidate-order choices. They account for 3.585 combinatorial bits in
the fixed policy, with a three-byte representation-0 choice payload. This is
enough to exercise the existing constraint path, but not enough to justify a
new packing ablation: the current byte-per-choice representation has no rank
padding slack. PAQ can only share structure after receiving the complete paid
frame; this adapter carries no separate dictionary or learned state.

For a bounded 2-D inspection only, PubChem CID 2519’s official 2-D SDF was
fetched separately. It has 24 supplied atoms, 10 predicted atoms and six
candidate choices under the same fixed adapter. It was not combined with the
3-D batch and no hydrogens were generated or inferred. The immutable inspection
asset, URL and hash are recorded in the JSON as a relevant separate future
input.

The future matched comparison remains unrun: original literal batch bytes and
the complete `hydrogen_slots_v1` frame must receive the same separately
declared PAQv216 `-4` AVX2 backend command. No unsupported record has been
dropped; unsupported formatting would take the paid literal-record path.
