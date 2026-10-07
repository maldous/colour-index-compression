# CIX rank history and first full enwik9 baseline — 29 September 2026

The preserved Silesia result is **1st equivalent**, not 24th. No winning result
was discarded by the Hutter transition. These are local numerical equivalents,
not official leaderboard listings or Hutter Prize scores.

| Complete Silesia result | Physical bytes | Equivalent rank | Evidence commit |
| --- | ---: | ---: | --- |
| Portfolio 19 | 31,175,135 | 24 | historical Site a04ebba |
| Portfolio 20 | 26,402,526 | 1 | 6e704a3ae38a8438c3db441f3b1e212d8f089464 |
| Portfolio 26 | 25,481,891 | 1 | 77615c7e4f3aeadf84c0a7397436acc420df91f3 |

Portfolio 20 was committed at 2026-09-29 00:24:48 UTC; portfolio 26 at
05:47:04 UTC. Both follow the 24th-place milestone. All 12 selected Silesia
streams have retained exact reconstruction evidence. The comparison leader
was 27,825,511 bytes; portfolio 26 was 2,343,620 bytes smaller.

The older rank audit's “no earlier result better than 24th” finding refers to
the history **before portfolio 20**. Its wording is not a claim about today's
preserved best result. No full-enwik9 or Hutter-winning result was found.
The available context-memory search was rechecked and returned
`initialized: false, results: []`; it provides no additional historical evidence.
The unavailable original mobile session cannot be reconstructed from that service.

## Full current-CIX baseline now running

The unchanged uncached portfolio-26 CLI is now executing on all
1,000,000,000 canonical enwik9 bytes, starting 2026-09-29 11:33:07 UTC.
Frozen source: `ea0d4e4ebd8d14dea4bb7a422f858c87bfa514fc`.
Codec revision: `77615c7e4f3aeadf84c0a7397436acc420df91f3`.
The source change at the frozen revision adds measurement instrumentation only.

The runner records normal read/write wall time, GNU CPU/RSS measurements,
sampled combined process-tree RSS, temporary space, phase commands, and hashes.
It uses one CPU (8), a 10,000,000,000-byte memory cgroup with swap disabled,
no network, and an exclusive measurement lock. No other CIX heavy experiment is
queued. A 72-hour per-phase timeout is an operational cap, not proof of the
Hutter time requirement; Geekbench calibration remains outstanding.
The current encode CLI includes an internal full decode before saving the
archive. A separate fresh-process decode then restores the complete file and
verifies SHA-256. Both times and the internal verification overhead will be
reported separately. The archive is not published as verified until that passes.

This measurement keeps the existing CIX candidate policy. It does not silently
substitute the stdlib draft, a prefix, the winner transform, or pure PAQ for CIX.
The archive size and complete Hutter package total are separate quantities.
The current dependency inventory is not a finished, licensed, publicly released
submission; no official qualification follows from starting this run.

Canonical input SHA-256:
`159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`.
