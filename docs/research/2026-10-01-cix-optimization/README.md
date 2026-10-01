# CIX Rust optimization R&D

This is an active local R&D checkpoint for the Rust CIX implementation, not a completed codec tournament or qualification. It preserves the Python encoder as the executable reference and limits local data-size comparisons to the already verified Silesia Dickens member. Squash rows are used for codec-method inventory and exact published settings coverage only; their historical CPU figures are not compared to local timing.

## Current verified milestone

- Squash's Dickens ZPAQ level-5 count reproduced locally with both the source-pinned ZPAQ 7.05 and requested 7.15 libzpaq versions: 2,142,935 bytes and identical stream hash.
- Rust BEST CIXG1 produced a complete 3,506,980-byte archive. Its 5,304 candidate trials selected PPM on all 156 blocks. Rust `uncix` and the frozen Python CIXG1 decoder independently restored Dickens exactly.
- A CIXG1 outer-wrapped ZPAQ 7.15 trial was a verified negative: the complete archive grew by 431 bytes, while nested ZPAQ and Rust decoding still restored the original.
- Rust candidate search now uses a bounded dynamic worker queue. A one/four-worker FAST smoke produced identical bytes and observed 1.45× wall-time speedup. BEST used 1.64 cores average, but no valid one-thread BEST run completed, so a BEST speedup claim is not available.
- Rust BEST is still 25.27% larger than the frozen Python CIX `size` archive and 63.65% larger than direct ZPAQ on this input. Those are same-input outcomes with different encoders/settings, not matched causal ablations.
- BEST now compares PPM orders 1, 2 and 3, bounded by the frozen Python decoder's accepted range. A four-core Dickens trial added 312 candidates but produced the identical 3,506,980-byte archive; fresh Rust and Python decoders verified exact restoration. Orders above 3 were rejected for compatibility and the failed smoke is retained.

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

The highest-priority technical gap is now explicit: current Rust BEST picks fixed order-3 PPM everywhere, yet still loses materially in complete archive bytes and spends about 332 seconds searching. Work should focus on measured native-model/representation opportunities, not relabeling the external ZPAQ result as CIX.
