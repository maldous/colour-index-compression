# Molecular forward-transfer: PubChem caffeine SDF

This checks the existing SDF geometry/hydrogen-slot representation on one
independent authoritative input. It is not a PAQ result: neither the original
bytes nor the structural frame has been compressed by a backend.

The fixed asset is the official PubChem PUG-REST 3-D SDF response for caffeine,
CID 2519, downloaded on 2026-09-30 without reformatting. It is 3,950 bytes with
SHA-256 `ce51a07a9d3197bb7e1a82b38a5ff4b598eb2b6f21bcbfc3a0e89d17f932dc92`.
The source URL and durable local asset path appear in
[`molecular-forward-transfer.json`](molecular-forward-transfer.json).

`hydrogen_slots_v1` uses the already winning fixed policy: model 2,
representation 0, radius 6,200, and empty state per supplied input. It accepted
one strict canonical V2000 molecule (24 atoms) and retained the terminal empty
record literally. Frame-only decoding restored the exact asset SHA-256.

| Paid component | Bytes / bits |
| --- | ---: |
| Complete structural frame | 3,627 bytes |
| Header | 7 bytes |
| Radius + record-count varints | 3 bytes |
| Record flags | 1 byte; 6 padding bits |
| Skeleton length + skeleton | 2 + 3,254 bytes |
| Choice length + choices | 1 + 0 bytes |
| Coordinate residual payload | 359 bytes |

All listed byte components sum to the 3,627-byte frame. Record separators and
the trailing empty record remain in the paid skeleton. Unsupported V2000
records or noncanonical coordinate formatting take the literal record path.

There were zero hydrogen candidate-order choices for this molecule’s supplied
atom order. Consequently there is no concrete choice-rank packing slack to
ablate; adding a packing variant would measure empty overhead rather than the
winning constraint mechanism. The 6 flag padding bits and zero choice-rank
padding are recorded explicitly.

PAQ’s possible sharing remains separate from the structural transform. The
future matched control must compress the original PubChem response, while the
candidate compresses the complete 3,627-byte frame, both with the same pinned
PAQv216 `-4` AVX2 configuration. The adapter embeds no molecule dictionary or
learned state; PAQ, if later authorized, receives all skeleton and residual
bytes after the frame is complete.
