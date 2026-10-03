# CIXM6 idle-input flushing: verified scoped fix

Source `4af606b54ff076c401547ffff5f13a7ea16c4994`, branch
`research/silesia-competitive`. Independent static review approved the change.
Portable all-feature locked/offline release-lto build succeeded on this host.

## Change

M6 now uses the existing bounded poll/block reader with an explicit EOF flag.
An idle partial block is emitted and flushed as a normal frame; it no longer
terminates the stream. History, recent references, adaptive state, CRC and
length updates remain in causal order across frames. The portfolio wrapper
retains fd−1/no-timeout behavior. There is no format or decoder change. M6
remains serial and retains existing resource/flag validation. Polling and an
unused count scan add possible overhead; no throughput improvement is claimed
for this feature fix.

## Single-run checks

| Check | Result |
|---|---|
| Actual non-seekable idle M6 pipe, two 256-byte writes | First 256 reconstructed at 53.84 ms while producer and both processes remained open; final 512-byte hash exact |
| Complete idle archive | 27 bytes, old frozen BD2 Rust decoder exit zero after footer |
| Empty timed M6 encode and old decoder | 14-byte archive, zero restored bytes, both exit zero |
| No-timeout 1024-byte encode | Byte identical to retained 93 archive, 27 bytes |
| New Rust decoder on retained 93 archive | 1024 bytes exact |
| Truncated footer | Old decoder exit 2 |
| Corrupt footer | Old decoder exit 2 |

Aggregate cgroup high water including additional checks: 17,793,024 bytes;
512 MiB hard memory bound, swap zero, CPUs8/10 with 200% quota, no memory events.
This is a small synthetic correctness/latency test, not sustained throughput
or arbitrary-length memory qualification. The no-timeout reference archive
was post-run checked against committed 93 evidence; it was not independently
preasserted by the new runner. Reference hashes are recorded separately.

Both corrupt/truncated streams emitted reconstructed bytes before returning
nonzero: callers must inspect the final exit status. Whole-stream integrity
is confirmed only after the footer is verified. Flush timing is best effort,
including encoding and downstream delays; the input interval starts after the
first byte. No unframed flush bytes or model resets are inserted.

## Artifacts and remaining scope

`freeze.json`, `raw/`, `m6-idle-result.json`, source/scripts and `SHA256SUMS`
retain reproducible commands and actual child/cgroup/time receipts. Build
emitted existing compiler warnings; no warning-free/new Sonar claim follows.
The current-host binaries are sealed under
`benchmark-work/m6-idle-4af6/final/` with hashes in `native-release.json`.

CIXF1 uses the same timed implementation, but its filename-wrapper idle
workflow was not separately exercised. Full suites, held-out gates, large
stream scaling, slow-consumer/interruption tests and general production cache
speed measurements remain outstanding. The cache's two focused tests passed
at source93; the later M6-only change was checked through CLI workflows here.
No corpus benchmark, Hutter run, acquisition, Actions or Site publication.
