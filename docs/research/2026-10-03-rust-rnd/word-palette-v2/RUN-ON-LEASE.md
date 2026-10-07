# WPV2 run instructions

Do not compile or execute until root grants a WaveScheduler lease. The lease
cgroup encloses the WPV2 parent, GNU `time`, `prlimit`, `cix`, and `uncix`.
Its predeclared aggregate limits are one assigned CPU (`cpu.max=100000 100000`
and root-recorded affinity), 768 MiB `memory.max`, `memory.swap.max=0`, 2 MiB
temporary files, and 1,200 seconds wall for the complete six-row batch. Each
native child has a 180-second wall ceiling under the parent wrapper. This
prepared batch has an 8 KiB input cap, a 64 KiB represented-byte cap, a 64 KiB
nested-archive cap, and no repetitions.

1. Compile the frozen source with `rustc --edition=2021 -O` into a lease-owned
   temporary path and record its SHA-256.
2. Run `generate` once for each frozen strong, weak, and absent fixture, verify
   each SHA-256 against `freeze.json`, and retain inputs outside Git.
3. For each fixture, run exactly one `identity 8` CIXG1 FAST control and one
   `palette 8` trial using the two frozen native binaries. The result is exactly
   six rows, each measured once. Keep JSON reports, complete archives, the
   persisted native `*.wpv2.cixg1` candidates, GNU-time logs, source and binary
   hashes. Give every row a unique report filename: the driver creates a sibling
   `REPORT.wpv2.scratch/` directory, retaining each fixture's child receipts.
4. Compare `complete_cixg1_bytes`; raw fallback size is an integrity/safety
   result, never a substitute backend for that matched comparison.
5. Require both `native_candidate_fresh_archive_only_decode` and
   `selected_candidate_fresh_archive_only_decode`, then separately verify each
   restored SHA-256 equals its fixture hash. Stop on a verification or resource
   failure.
6. Record the parent cgroup `cpu.max`, assigned CPU affinity, `memory.max`,
   `memory.current`, `memory.peak`, `memory.swap.max`, `memory.events`, elapsed
   wall time, and temporary-directory high-water bytes. Retain the GNU-time RSS
   receipt for every native encode and decode child. The driver also reports its
   own bounded scratch bytes; the parent receipt is the aggregate authority.

No result expands width, input, fixture, or repetition scope.
