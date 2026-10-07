# CIX Rust optimization R&D

This is an active local R&D checkpoint for the Rust CIX implementation, not a completed codec tournament or qualification. Rust is the implementation under optimization; Python is used only as a compatibility decoder where needed, not to select or tune candidates. Local data-size comparisons use only the already verified Silesia Dickens member. Squash rows are used for codec-method inventory and exact published settings coverage only; their historical CPU figures are not compared to local timing.

## Current verified milestone

- Squash's Dickens ZPAQ level-5 count reproduced locally with both the source-pinned ZPAQ 7.05 and requested 7.15 libzpaq versions: 2,142,935 bytes and identical stream hash.
- The historical fixed-order-3 Rust BEST CIXG1 run produced a complete 3,506,980-byte archive. Its 5,304 candidate trials selected PPM on all 156 blocks. This is historical evidence, not the current normal CIX policy or a current profile result.
- A CIXG1 outer-wrapped ZPAQ 7.15 trial was a verified negative: the complete archive grew by 431 bytes, while nested ZPAQ and Rust decoding still restored the original.
- The completed automatic-profile screen used the ordinary CIX interface on the same verified 1 MiB Dickens development range, with two fresh exact-decoded repetitions each: FAST selected LZ at 476,034 bytes, DEFAULT selected BWT at 407,643 bytes, and BEST selected PPM at 354,023 bytes. FAST/DEFAULT wrote CIXG1 and BEST wrote CIXG2 in this frozen build. These are local development measurements, not the Canterbury/Calgary/Artificial gate or a renewed Silesia qualification.
- The 2b default-model qualification replicated a PPM-admission change on development and a distinct Dickens replication range. It changed the automatic DEFAULT result from BWT to PPM: 407,643→381,955 bytes on development and 423,660→397,078 bytes on replication, with fresh exact decode in every paired run. This is a versioned, input-specific result rather than a universal model claim.
- Independent CIXG block parallelism is implemented. An eight-cell forced-PPM 1 MiB qualification retained the identical 354,023-byte archive hash in every cell. Four block workers encoded in 2.56–2.57 s versus 8.10–8.16 s for one worker, with 138,292–138,304 KiB peak RSS versus 38,612–40,312 KiB. Four candidate workers took 3.38–3.41 s and 104,080–113,492 KiB. The route, CIXG2 format, block size and CPU lease were explicit implementation controls.
- The fixed-mix recurrence payload now has a corrected causal v3 encoding while v2 keeps its legacy decoder semantics. The recurrence route is not yet admitted to automatic selection. CIXG2 coder 7 is deterministic canonical Huffman; neither is a measured automatic-selection win.
- Fixed-mix scratch state was changed to fixed-size arrays and checked in a four-cell forced-mixture CIXG2 qualification on the first 128 KiB Dickens range. All archives were 52,400 bytes with the same SHA-256 and all matching decodes. Candidate encode walls (1.43, 1.50 s) overlap controls (1.45, 1.45 s); this establishes compatibility and bounded resource evidence, not a throughput win.

These are separate immutable snapshots: the profile and parallel screens use
the frozen 90e build, the DEFAULT model study uses the 2b candidate revision,
and the fixed-mix array study compares its frozen control with candidate
revision 08711c49659ddddb73e5f19b34bf29d50845e3d2. Do not compare their wall
times as one same-build tournament.

## Evidence map

- [Coverage matrix](coverage-matrix.md): all required Squash codecs, additional inventory methods, principle-level status and current selector blind spots.
- [Exact Squash settings inventory](squash-settings-inventory.json): all plugin/codec/level combinations recorded in the pinned published CSV, plus omitted-setting caveat.
- [Verified results and experiment queue](results.md): sizes, hashes, timing, memory, interpretation limits and next R&D priorities.
- [Experiment queue](experiment-queue.md): frozen hypotheses, matching controls, budgets and promotion gates.
- [Machine-readable results ledger](results-ledger.json): canonical trial IDs/statuses with links to immutable manifests and runner receipts.
- `runs/`: predeclared inputs/settings and immutable local run artifacts, including interrupted or failed cells clearly labeled as such.

## Frozen identities and constraints

- Python CIXG1 selector reference: `80b95427725ecf59d626b2982d50f6349abd56e1`.
- Python cross-decoder checkout: `0d835c98040a197e37b7432f2ec7a8688116dae6`, with package source SHA-256s frozen in the cross-decode manifest.
- Published Squash data: `quixdb/squash-benchmark-web` commit `fed6ea3374155184672b71928d2b805463d156f0`.
- Squash plugin interface docs inspected at v0.7.0; not assumed to identify every historical benchmark dependency build.
- Only Dickens from the existing verified Silesia set is used for local result comparisons in this checkpoint. No new data acquisition, dataset searches, external publication, GitHub Actions, or Silesia qualification is initiated here.
- Benchmark jobs go through the existing `WaveScheduler`, which enforces at most four physical cores, 12 GB aggregate memory, 4 GB temporary space, and no swap. Completed additions are committed by the root agent; Actions remain disabled.

The highest-priority technical gaps are automatic CIXG1/CIXG2/CIXM6 packaging and segmentation/history selection, bounded transform and parameter search, and qualified native model gains. BEST is a bounded native search, not an exhaustive argmin over every legal CIX encoding or an external-codec tournament.

Current follow-up: source `ee6b4396df760d19005c4e0800783fef58d52334` adds implicit
stdin workflows, dash-prefixed names, output contradiction rejection and a
64-opportunity minimum for DEFAULT PPM admission. All 178 final release tests
passed. The corrected ABBA DEFAULT v2 run verified eight cells and retained
the exact 6.30%/6.27% complete-size improvements on the two exposed ranges;
see [current evidence](adversarial-parallel-results.md). This does not close
the broad model/transform/coder, PGO or corpus-qualification queue.
