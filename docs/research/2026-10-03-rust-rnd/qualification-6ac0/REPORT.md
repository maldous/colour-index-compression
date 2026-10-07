# Large native streaming qualification — release 6ac05f8e9

Both successful rows use an incremental 32 MiB generated source with SHA-256
`a239757831a2d312604464149c66712824576734926f778d6dcec437b17c283a`.
The generator emits bytes once without a source file or whole-input buffer.
Exact live restoration and separate fresh current/old BD2 Rust decoding passed.

| Configuration | Complete bytes | Encoder nominal memory | Decoder nominal memory |
|---|---:|---:|---:|
| G1 FAST, two workers, independent blocks | 33,575,724 | 16 MiB | 16 MiB |
| M6 FAST, one worker, restricted candidates | 33,558,038 | 3,584 KiB | 16 MiB |

Both use 64 KiB blocks, 50 ms best-effort flush timing, actual pipes, irregular
writes and a slow consumer. During a 250 ms producer idle pause after 1,048,832
bytes, reconstructed data reached the pause boundary before EOF. Input and
output queues were bounded; maximum source queue was 65,536 bytes, and decoder
queue maxima were 12,288 bytes (G1) and 8,192 bytes (M6). No source spooling.
The current decoder rejects midpoint corruption and one-byte footer truncation with exit 2; reconstructed bytes
can precede final integrity failure. Whole-stream integrity is final only after
the footer. Empty inputs round-trip. SIGINT exits nonzero without SIGKILL;
M6 also emits the complete source while the archive pipe remains open, then
honours interruption while waiting for EOF.

These are different declared configurations, not a same-policy compression
ranking. Random data expanded after framing. Nominal CLI memory admission is
not a process RSS cap. Actual shared phase cgroups used CPUs 8,10, quota 2 CPUs,
256 MiB memory and no swap; sampled phase peaks were 86,315,008 bytes (G1) and
90,689,536 bytes (M6), including provider, consumer, decoder controls and cache.
Total harness wall time includes deliberate consumer delay and fresh controls;
it is not encoder-only sustained throughput. First-output latency was not
recorded as a standalone scalar in this large fixture.

Preserved attempts: G1 v1 stopped on a harness select-argument bug. G1 v2 passed
and was not repeated. M6 v2 at 16 MiB missed the 250 ms idle checkpoint while
trial compression was active; it is a timing negative, not qualified exact
restoration. M6 v3 explicitly reduces memory admission, omitting unfunded
expensive candidates; it passed. Flush deadlines remain best effort and include
candidate work/downstream delays. Freeze and driver amendment snapshots are
retained in raw/. These results do not qualify all routes or full-corpus speed.

The separate Docker Sonar attempt failed its cgroup identity check before scan;
there is no completed current-release Sonar result from that attempt.

## Independent evidence review corrections

execution-bindings.json binds each successful row to its actual driver and
scheduler; raw/schedule-v3.py preserves the exact M6 launcher previously outside
Git. G1 used v2; the later driver amendment changes M6 only. Original freezes
are retained. M6's declared one physical core differs from execution: one encoder
worker ran inside the two-core harness cgroup. This is not one-core qualification.
Queue maxima measure provider/application harness buffers, not native internal
queues or kernel pipe occupancy. Sampled cgroup peaks are lower bounds.
Failed M6-v2 progress fields marked processed_bytes/throughput use scheduler
nominal input size despite stopping at the 1,048,832-byte checkpoint; exclude
these fields from performance evidence. Malformed controls used current Rust
only; old BD2 compatibility applies to valid archives. Native stderr logs
are copied into raw/ for durable candidate-omission and error diagnostics.
