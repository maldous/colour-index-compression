# Control revision and timing-order erratum

Frozen manifests and receipts are retained unchanged. Binary SHA-256 identities
are authoritative for the executed programs. The original paired experiment
harnesses recorded a candidate revision even in control manifests and hashed
current source files for both cells. Those source fields describe the harness
snapshot, not the older control encoder source.

## Recovered immutable build identities

| Experiment | Control source | Control encoder SHA-256 | Candidate source |
|---|---|---|---|
| DEFAULT PPM probe v1 | `90e457277dcb80b1ff713413b07a8c904bb660df` | `529e1471518e63a4afe1d059bf4e06ff4b9fe21cf90189aa74c8c5d4d723bec0` | `2b26cc074370c4db9c13c4dd0471a2f37f16443e` |
| Mixer stack scratch v1 | `2b26cc074370c4db9c13c4dd0471a2f37f16443e` | `b66bc271a7a91347266a31bd859318997616a80178926397c68f3a5490174974` | `08711c49659ddddb73e5f19b34bf29d50845e3d2` |

The DEFAULT control binary is the same immutable binary recorded by the
[parallel control build identity](cix-parallel-qualification/runs/cix-parallel-ppm-t1-blocks-r1/b59dc326ba4c1bdba2bbad12f41f8b88805648b67cc652132e0f05465541a626/identity.json).
The mixer's control pair is copied from the earlier DEFAULT native candidate
[build identity](cix-default-model-qualification/runs/default-ppm-probe-v1-native-2b26cc074370c4db9c13c4dd0471a2f37f16443e-development-native-candidate-r1/1638a319e6949e2f190beca980863c5a8b4c63e3eae764d4526168973958efbe/identity.json).
The control `uncix` SHA there is
`cfab572135912e9af955672822b223d870a6a48fb2f5bee7a70558fb77759711`.
DEFAULT v1 used that same candidate decoder for both encoders, as declared;
the mixer comparison used matching old/new decoder pairs.

## Measurement limits

The original order was control/control/candidate/candidate. Input cache and
other host activity were uncontrolled. The timings are local observations,
not isolated causal speed estimates. Identical archives and exact fresh
restoration remain valid evidence. The mixer timings overlap: no throughput
win is claimed. DEFAULT's size improvement is exact; its timing improvement
must be read with this order limitation until the corrected ABBA run.

Future paired harnesses require an explicit recovered control revision and
its immutable build receipt, validate encoder/decoder hashes, distinguish
implementation source from current harness source, check complete archive
sizes, and use a predeclared control/candidate/candidate/control order.
