# SMC1 composition evidence review

Date: 2026-10-04. This was a read-only review of completed evidence. The
reviewer did not build the wrapper, extract input, run a codec, decode an
archive or start a benchmark.

## Decision

**Approved for a private checkpoint with conclusion A: close this bounded
numeric composition branch and retain the unchanged incumbent.** No material
correctness, accounting, identity, resource or governance blocker remains.
The conditional replication trigger is false, so not running the reserved
2 MiB replication slice follows the frozen gate.

This approval is limited to the frozen 4,096-byte qualification slice and the
predeclared 15-description family. It is evidence for a retained negative, not
production readiness, a general selector result or a speed ranking.

## Reviewed identities

| Artifact | SHA-256 |
|---|---|
| successful wrapper source | `6bfe34a88e8622281a95e0a67830826f5c7cb6cbca4ab9ad6f066a706c39e2ce` |
| `REPORT.md` | `bb7b25e25b9a47b87bb21b0bc9a695785e9e7aac5f92f1842000e56b3acb8381` |
| `results.json` | `419e44f2ddaf1a3cd209b42df50889757732d0b42e1b7f23f5e74c7675be93ca` |
| `analysis.json` | `7f0d7d4b464afb26f107170b9518d41326c3fac4728f6df63964eaa3bfa1d80c` |
| `metrics.json` | `422b8c3d188746b657be6261e8a450741214ab4d526ef5ba81fe4868a9e16f2c` |
| `check-results.json` | `936e8a4af65fbf475275badfae62d3315b8e0663f2e6d6507eca6f0dc8d11ec0` |
| matrix artifact binding | `d806f672f72843dae1929e24dbb453d2705b2f5b5e06c4485b170ef5f74211c3` |
| check artifact binding | `6ec95fa9ce8634407680386ffd35aec5a42d2a77123e10cb3eef3aea3cab251e` |
| input freeze | `5618aac3f4fea608e5797be3c4d59dbeea32ab2923dede5c1a7a498df50b38aa` |
| build-fix experiment freeze | `4834e75beb4be30d0a57dd184e0ce8c60bd2d1fa43e9f788d6f1102ea1eb3848` |
| independent-check freeze | `c9a5c1f4378bc4aea8cfeda94b0794db31f4bbc78b7215aca756bd0f767bf02b` |
| replication gate | `a4646610324dd43e3862ff370ff40dbf575cb48ea194755f8e217893c4e74cc3` |
| environment receipt | `56510eebe28de51a08c9e44f77660a85910ec65675787285240de00ea7fcbc24` |
| post-run tool binding | `34a3cbd7dde606b4a80307294c8f5b80b463eb6d8254290ab8721388eb5195b4` |

The freeze binds production revision
`d3a2cd416e49f93403d1dbd348a3e9a45db66ec6`, sealed CIX executable
`f9b8262086be9704d8d9425ccbf5cbf5274096ae88334ea1501aa4773034fac3`
and native rlib
`3db8b676ec03a2d0a5358f87d72af13ad6161a46b32467f4ea0dd34b8d5c475c`.
The qualification slice is 4,096 bytes at offset 1,048,576, SHA-256
`d9b5b011beef2e414cbb55b6167a875c8b19dacbc0d139ea7ab4cad3920dd765`,
from the frozen whole-source identity. Settings and version receipts were
recorded before the run: Zstd 1.5.5, XZ Utils 5.4.5, gzip 1.12 and bzip2
1.0.8. `tool-bindings.json` accurately labels its executable, compiler,
shared-library and static-library hashes as post-run readbacks, rather than
prelaunch enforcement. All eight match the prior latent checkpoint identities.

## Accounting and outcome

The evidence contains 15 descriptions and three paid wrapper backends, hence
45 complete SMC1 archives. Every row satisfies
`complete_bytes = 25 + width + backend_body_bytes`; the identity diagnostic
pays 26 bytes, width-three pays 28 bytes and every width-four candidate pays
29 bytes. Recorded archive sizes equal parsed complete sizes for all 45 rows.

The 48 compression trials reconcile as 15 unique CIXM6 bodies, 15 unique Zstd
bodies, 15 native proxy encodings and three additional external controls. The
bare original M6 and Zstd bodies are reused only after exact transformed-byte
identity; their wrapped diagnostic archives still pay and materialize their
descriptors. No other transformed-byte aliases are reported.

The decisive costs reconcile:

- bare original CIXM6: 1,393 bytes;
- frozen E plus CIXM6: 1,418 bytes;
- bare inner M6 payload/framing: `1,373 + 20 = 1,393` bytes;
- E inner M6 payload/framing: `1,369 + 20 = 1,389` bytes;
- E front description: 29 bytes;
- net: a 4-byte inner saving minus 29 paid bytes, a 25-byte loss.

Both decisive M6 archives contain one mode-3 frame for all 4,096 source bytes,
use a 1 MiB history limit and pay 20 bytes of inner framing. Therefore the
reported result does not hide a frame/reset-count difference. The smallest
ordinary mask is 1,536 bytes, and no measured description beats the 1,393-byte
bare fallback. `replication-gate.json` consequently records `triggered:false`.

## Restoration, malformed input and artifact binding

The matrix run records successful fresh restoration for all 45 SMC1 archives
and five bare controls. Its artifact binding contains 50 restored files; each
is 4,096 bytes with the qualification slice hash. The independent check then
freshly decodes all 45 SMC1 archives again: 15 per backend, all exit zero and
all restore the same hash.

Thirty independent tiny cases cover source lengths 1 through 32, widths 1
through 8, phase zero and each nonzero maximum phase, partial rows and operator
IDs 0 through 4. All transform, native encode and fresh decode subprocesses
exit zero. The 37 malformed or unsupported cases all exit one with empty
stdout, including canonical M6 varint and bound failures, Zstd frame/content/
window failures, native route and length failures, and the oversized embedded
Huffman output length.

All 145 matrix-bound artifacts and all 346 independent-check-bound artifacts
currently match their recorded byte lengths and SHA-256 values. The build-v2,
matrix-v2 and checks-v1 phase receipts each record exit zero, CPU affinity 8,
a 2 GiB cgroup memory limit, zero swap and a one-CPU quota. The matrix receipt
records 152.227 seconds elapsed, 151.545 CPU seconds, sampled cgroup high-water
49,684,480 bytes and temporary high-water 5,577,456 bytes. These remain within
the frozen bounds. The failed build-v1 receipt is preserved separately and is
the only nonzero phase receipt; it predates input extraction and archive work.

## Governance and limits

The reserved replication slice is absent from the experiment input directory.
Only the qualification slice and its 15 complete transforms exist there. The
whole-source read used to verify its frozen identity does not constitute a
second representation trial.

Input, transformed, archive, restored and executable bytes remain under the
locally excluded `benchmark-work/` tree; Git tracks no file below that tree.
The evidence directory contains textual receipts, hashes and reports. Its only
nontext files are ignored Python bytecode caches, which are not checkpoint
content. Thus the private checkpoint need not commit source or archive bytes.

The validation did not inject a misbehaving child to exercise the decoder's
stdout-overrun branch. Aggregate cgroup high-water is sampled and explicitly a
lower bound. Each timing cell is a single observation and short subprocess
times include launch overhead. These stated limits do not affect the complete
byte comparison or the failed promotion gate.

`REPORT.md` has one conclusion and one next action: conclusion A, checkpoint
and close the branch with production unchanged. That conclusion is supported
by the paid complete-archive evidence and does not imply a wider rejection of
representation composition.
