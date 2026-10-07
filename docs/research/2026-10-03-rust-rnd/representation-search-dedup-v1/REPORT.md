# Exact transformed-byte reuse: single-run result

Status: VERIFIED_SINGLE_SCREEN, experimental implementation improvement. Uses the previous frozen screen as baseline; no baseline re-encoding. Same input, native binaries/settings, candidate order, cost accounting and frame format.

| Metric | Saved baseline | Exact reuse |
|---|---:|---:|
| Evaluated candidates | 12 | 12 |
| Actual native trials | 11 | 9 |
| Selected complete bytes | 2,487 | 2,487 |
| Batch runner elapsed | 0.303048 s | 0.244526 s |
| Supervisor CPU | 0.216139 s | 0.195796 s |
| Actual cgroup peak | 20,901,888 B | 20,946,944 B |

The two reused pairs are7→3 (residual1/delta1) and8→4 (residual4/delta4). Every candidate program, backend, payload/instruction/complete size and nested archive hash matches its baseline. Selected archive bytes and SHA match exactly; fresh archive-only decode restores the frozen input hash. Four malformed selected archives retain rejection behavior. Native reuse rows carry null timings/RSS and explicit reused_from, rather than fabricated zero-cost measurements.

The observed wall decrease is19.3%, supervisor CPU9.4%; each is a single screening observation, not a reproducible general speed claim. The rigorous improvement is18.2% fewer native trials with no output change in this declared finite set. Discovery, byte comparisons, cache copies, all rejected trials, selection, verification and malformed checks are included in batch/supervisor work. No isolated encode-only or decoder speed gain is claimed.

Cache lookup uses complete byte equality with no hash-only inference. It is scoped to one call with fixed backend/settings, retains key/payload/plaintext and candidate metadata, and stops admission at4MiB requested-storage accounting. This run charged195,002B. Allocation bookkeeping and stack headers are outside that counter; parent1GiB cgroup is the authoritative total-memory bound. One CPU20, quota100%, no swap,2MiBtemp; retained284,973B and no memory events.

No production wire format, decoder, profile, algorithm, history or block-boundary change. This prototype is not yet production selector integration. The production insertion audit is ../DEDUP-INTEGRATION.md: reuse inside one stateless mode7 chain call, pay current transform instructions separately, thread a reserved cache allowance from existing memory admission, and qualify cache0/admitted/full and cross-block behavior.
