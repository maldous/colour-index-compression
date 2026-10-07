# Legacy CIXM6 helper extraction qualification

## Scope

This packet qualifies a semantics-preserving decomposition of `encode_uints`
in the legacy CIXM6 BWT encoder and sparse/run encoder. The exact three-file
review patch is [review/scoped-candidate.patch](review/scoped-candidate.patch);
its production-only subset is
[review/scoped-production.patch](review/scoped-production.patch).
The test-only archive constructor is retained at
[review/sonar_m6_routes.rs](review/sonar_m6_routes.rs). No production
container, arithmetic, combinatorial, tie-breaking, or candidate-order change
is included.

Candidate source started from `d172ce8b429adbbe26c01fa4c27545588e4b7f73`
with the uncommitted two-file production patch and test fixture in this
packet. `SHA256SUMS` binds both
changed sources, the fixture source, the release binaries and their retained
copies. The production patch SHA-256 is
`c58af269e35eaa93028b185fdb3f3c38e38477218d6e03cb17fe8abc10461edc`.

## Exact payload parity

The same test-only fixture was run in a clean baseline worktree at the source
revision above and in the candidate worktree. The three payloads and their
complete constructed CIXM6 archives compare byte-for-byte:

| Mode | Payload SHA-256 | Complete archive SHA-256 |
|---|---|---|
| 4 BWT | `ea1914d21dfb9d9d21a1b0854199cf9173f81faf3ee48a31b46b1a700e368613` | `8f19b6db2ecf70da3253382ea643762073e451b1d9e8c6aec3d8db3341860237` |
| 11 sparse | `af6f8eba711d3b266c59c504320b7bf79a03f8ba7c11404138b5df534d068505` | `9dda1b1a0fe7b8b33184b2bd5df76cb515de394e0779ab92cad00950c3e94ebf` |
| 12 runs | `99c4af55c83eab0ad1afafd76cfa067dbdd7c50593dc0b3cf3636c0f6b6cbb59` | `d49fa1eadd65777616eaed3de7fb8b2a326eb17aee8386500d6712b8b56e2b0c` |

The candidate fixture test completed 28 tests successfully. Its raw log and
resource readback are retained under `raw/candidate-fixture-v2/`.

## Fresh native decoder result

Each candidate archive was passed as the only input to a fresh release
`uncix` process. Source and restored hashes match in
`raw/candidate-fixture-v2/mode*.fresh.sha256`. The decoder child snapshots
show `Cpus_allowed_list: 22` and the transient cgroup path in
`mode*.decoder-cpus.txt` and `mode*.decoder-cgroup.txt`.

The transient cgroup used `MemoryMax=1073741824`, `MemorySwapMax=0`, and its
sampled peak was 4,374,528 bytes; see `decoder-identity.readback.txt`.
The retained release binary hashes and dynamic-linker listings are in
`SHA256SUMS` and `artifacts/`.

## Corruption result

Removing the final archive byte from each mode causes a nonzero decoder exit
with `cix: truncated archive`. The decoder may already have emitted all
reconstructed bytes before detecting the missing footer. These files prove
rejection only; they do not prove that corrupt or truncated input produces no
output.

## Separate automatic-selection observation

`raw/m6/` is retained separately from the direct-mode evidence. It used
automatic CIXM6 selection on three constructed inputs and selected modes 15,
1 and 16, respectively. It is a functional observation only and must not be
read as qualification of modes 4, 11 or 12.

## Packet contents

`raw/` contains complete unit logs, constructed sources, payloads, archives,
restored output, rejection output and readbacks copied from the run. The
`FILE-MANIFEST.tsv` records their paths and sizes. `commands.txt` and
`status.json` record the runner commands, unit completion states, binding and
claim boundaries.
