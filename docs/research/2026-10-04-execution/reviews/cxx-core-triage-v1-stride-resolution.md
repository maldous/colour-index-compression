# C++ core triage v1 — spatial stride resolution

The CharLS 16-bit branch now forms its row stride through a CIX-owned checked
helper. A width above `UINT32_MAX / 2` returns
`CIX_SPATIAL_INVALID_ARGUMENT` before either CharLS path receives the stride.
The helper is used by both encode and decode; eight-bit rows retain their
one-byte-per-pixel stride.

The focused contract ran under its lease and passed. Its receipt is
`benchmark-work/native-rc-check-v1/spatial-stride-contract-v1/receipt.json`
(SHA-256 `c458a5f0f86b91e8deb8bb9739535100fecd5848b9c8a098594de7aca3a4481d`).
It built the frozen CIX spatial source copy, compiled the standalone contract
with warnings as errors, and executed it successfully. The receipt binds the
bridge source hash `700ce5c4a53f338ab98535672c6bcb7a368586a44af87fb5be02e4fe69748241`,
the contract source hash
`24c9ae3f967432b0a59b3eb3dba3c963a9119b4095e83b79f59539c03b807988`,
and the retained CharLS/OpenJPEG SDK library hashes.

The contract deliberately supplies one-byte input/output objects while
claiming the otherwise valid `size_t` byte count for `UINT32_MAX` by one
16-bit sample. Both CharLS encode and decode returned
`CIX_SPATIAL_INVALID_ARGUMENT`; small exact 8-bit and 16-bit CharLS round
trips also passed. This is focused bridge evidence only. It does not select a
distribution provider or make a final distribution claim.
