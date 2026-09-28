# Generic larger-window diagnostic

The canonical suffix-array LZ encoder caps its history at 128 KiB even when
stream configuration permits 1 MiB. The experimental hash-chain parser uses
1 MiB, chain 32, minimum match 4 and lazy matching uniformly. No labels reach
the encoder. These conditional 16 KiB block probes include block framing but
exclude already-supplied history and whole-stream framing; they are not corpus
scores or leaderboard estimates. Every experimental LZ payload restored exactly.

| Probe | Incumbent block bytes | Candidate block bytes | Selected |
|---|---:|---:|---:|
| Generated distant repetition | 16391 | 32 | 32 |
| Canterbury kennedy midpoint | 1191 | 1160 | 1160 |
| Calgary book1 midpoint | 5491 | 6265 | 5491 |
| Calgary obj2 midpoint | 4007 | 3982 | 3982 |

The book1 LZ-only gain disappears against the stronger PPM incumbent. The obj2
result also changes parser settings, so its gain cannot be attributed solely to
window size. Next step: a separately loaded experimental portfolio retaining
every incumbent, complete-stream round trips, then the full prerequisite gate.
Canonical codec source and ongoing Silesia policies remain frozen.

## Higher-effort complete-member diagnostic

Level 9 finished all four complete inputs and verified physical artifact hashes
and exact round trips: grammar 1122 → 1089; fields 2960 → 2822; Alice 43147 →
41481; Artificial random 75089 → 75090 bytes. Thus higher effort is not itself
zero-regret; exact selection with the incumbent is required. Timings and source
identities are retained in the accompanying JSON. This is not a full tier result.
