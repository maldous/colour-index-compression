# R1 lane/residual finite screen

Portable current native backend source `6ac05f8e9`, FAST, one thread, CIXG1; 16 fully encoded CIXG1 candidates plus one serialized raw literal fallback per 8 KiB generated control. One observation, no averages.

| Control | Identity complete bytes | Selected complete bytes | Selected program |
|---|---:|---:|---|
| strong | 278 | 129 | mod-delta-2 |
| weak | 526 | 232 | xor-2 |
| absent | 8316 | 8221 | literal |

Strong: −149 bytes (53.60% of matched identity frame). Weak: −294 bytes (55.89%). These include R1C1 instructions, nested CIX archive and CRC; they are experimental representation effects on synthetic controls, not a production selector or corpus claim. Random selected literal: 8,221 bytes, 29 bytes above original raw input, 95 below identity. Raw input is not a valid unframed R1C1 archive.

Each candidate native payload decoded in a fresh Rust process and reversed exactly; each selected outer archive decoded in a separate fresh outer process. CRC/opcode/truncation selected-frame malformed controls rejected without panic. All 51 candidate rows, losing transforms and native timings/RSS are retained in results.json.

CPU 8, quota 100000/100000, 1 GiB memory, no swap, 64 MiB active temporary cap verified in live cgroup receipts. Complete batch wall includes all trials, restoration and malformed controls; native times include GNU-time/timeout launch and 5 ms polling granularity and are unsuitable for sub-millisecond throughput claims. Sampled cgroup high-water is a lower bound, not exact peak RSS. Build phase nominal processed_bytes/throughput is scheduler input metadata, not compressed throughput. Input hashes were recorded in execution-binding.json before any codec calls.

R1 uses a declared shallow 17-program set, not exhaustive language optimisation. No production route edits or promotion occurred. Next prerequisite is a new, frozen CCA gate with a matched backend/control; no corpus baseline restarted.

Raw row binding.source_revision is the orchestrator checkout c5df6465f; it does not contain the then-untracked R1 driver and is not the backend revision. The driver source is hash-bound in freeze.json and executable/input/backend hashes in execution-binding.json. Backend source is 6ac05f8e9. Do not interpret the checkout revision as a committed experimental source identity.
