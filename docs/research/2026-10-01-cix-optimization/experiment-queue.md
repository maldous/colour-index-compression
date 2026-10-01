# Prioritized experiment queue

Only the already available Dickens source is eligible for new local size comparisons in this checkpoint. No acquisition or benchmark expansion is authorized. Each new cell must be frozen as a WaveScheduler manifest before execution. The queue separates backend, representation, model, coder and selection effects.

| Priority | Hypothesis / experiment | Matched control | Budget and acceptance | Status |
|---:|---|---|---|---|
| 1 | Compare original Dickens and frozen native CIX representations under one ZPAQ 7.15 method-5 run; decode each representation independently. | Direct original→ZPAQ 7.15 method 5 is fixed at 2,142,935 bytes. Completed Rust CIXG1 archive is fixed at 3,506,980 bytes. | One CPU, 2 GB, 300 s; archive-only decode, exact representation and original hashes. | Rust CIXG1 wrapper completed and lost by 431 bytes. Additional Python-frozen representations remain. |
| 2 | Add a lightweight native byte/bit predictor (order 0–2, sparse contexts, calibrated blend) as a CIX candidate. | Same block, PPM order 3, current predictor/residual, fixed mixer and composition candidates; preserve exact frame and metadata cost. | First 1–5 minute synthetic unit trials; then fixed Dickens regions, predeclared within 10 MiB total input. Promote only on exact fresh Rust+Python decode and smaller complete encoded size without exceeding declared budget. | Queued; no implementation yet. |
| 3 | Add recurrence-distance and periodic candidate features informed by ZPAQ level-5 analysis. | Disable exactly one feature at a time; keep other model code and selector budget unchanged. | Start with 32–256 KiB blocks. Charge recurrence table/model metadata and decode state. Stop on memory/CPU ceiling, not temporary bytes. | Queued; need frozen ZPAQ model inventory with source-file/option citations. |
| 4 | Profile PPM route and compare Python-compatible orders 1–3 against fixed order 3. | Current route 8 / order 3, same representation and 65,536-byte block. | Reuse worker/memory cap; include route metadata and whole archive; collect per-order work. Require exact complete archive plus Python/Rust cross-decode. | Completed negative on Dickens: orders 1/2 added 312 trials; archive remained byte-identical. Orders 4+ are ineligible until Python decoder support is versioned. |
| 5 | Compare entropy coders on the same frozen substreams: exact composition/rank, adaptive range, count-range, DEFLATE, Huffman, ANS/FSE. | Freeze bytes and all side streams before coder trials. | Charge coder ID, dimensions, counts, lengths and complete frame; run a small exhaustive oracle before larger trials. | Queue; CIX lacks standalone Huffman and native ANS/FSE. |
| 6 | Evaluate transform combinations (BWT→MTF→zero-run, stride→residual, prediction→rank) in both valid orders. | Original block and each single transform independently; explicit metadata bytes. | Bounded beam selected before the trial; include transform cost and decoder. Reject whole-block BWT + one global multinomial rank as a presumed count reduction. | Queue; current BWT/MTF and stride routes are separate/narrow. |
| 7 | Improve LZ cost-aware parsing and reuse route buffers; measure native per-symbol costs and memory. | Current bounded 8-position hash-chain parser, same block/window. | Profile on the frozen Dickens input and small mechanism fixtures; preserve maximum memory cap and exact decoder. | Queue; selected route is PPM here, so not first. |
| 8 | Measure shortlist misses and scoring bugs against a small-block exhaustive oracle. | Exact legal candidate set under frozen format; compare actual frame sizes, not estimates. | Enumerate combinations only on small blocks; report omitted candidate winners separately from estimator ordering and selection tie bugs. | Queue; current selector has a finite shortlist; BEST is not exhaustive. |
| 9 | Reduce candidate search wall cost and expose effort budgets in actual selector enforcement. | Dynamic queue v1: 5,304 candidates, 555.970 summed trial-seconds, 330.983 search wall-seconds. | Add bounded time/memory/search policy and report all skipped candidates. Do not silently replace omitted methods; raw fallback remains. | Implemented and screened: per-worker memory, search and trial policies are enforced and omissions counted; v5/v6 Dickens runs had zero skips. |
| 10 | Reorder candidate dispatch by coarse estimated route cost to improve four-worker occupancy. | Same candidate list, block size, memory, profile and original-index winner tie-break; FIFO run on identical input. | Require replicated wall-time gain, same archive and exact restore on the shared four-core WaveScheduler allocation. | Rejected for production: priority runs averaged 325.67s versus one 327.95s FIFO control; one priority run was slower and utilization remained 165–167%. FIFO remains active. |

## Trial declaration requirements

Every dispatched cell must record:

- Hypothesis, mechanism, matched control, exact source offset/length/hash, and whether it is development or held-back evidence.
- Frozen code commit plus dirty-tree source/binary hashes, backend release/build identity, route/coder/transform parameters, block and history sizes.
- CPU set/physical-core lease, worker count, RSS/temp ceilings, wall ceiling, swap policy, memory allocator and stream/flush settings.
- Complete archive size/hash including all frames, headers, dictionaries, checksums and footers; encoding/decoding wall and CPU time; measured peak-memory source and its limits.
- Fresh decoder process, archive-only input, exact output byte count and SHA-256. Corrupt/truncated attempts remain failed evidence, never dropped rows.

## Promotion path

1. Verify unit-level inverse, malformed input, extreme integer and deterministic tie behavior.
2. Compare tiny, random, repetitive and mixed synthetic blocks only for correctness/mechanism diagnostics.
3. Run fixed, disjoint Dickens regions from the existing dataset for discovery; never tune against imported Squash timings.
4. Freeze candidate settings and compare a distinct held-back Dickens region; charge all framing and search cost.
5. Only after the controlling benchmark gates authorize it should the work move through Canterbury/Calgary/Artificial and later Silesia qualification. This checkpoint does not claim those gates.
