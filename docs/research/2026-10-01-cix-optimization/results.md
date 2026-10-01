# Verified results and rejected attempts

## Current native review and optimization checkpoint

See [adversarial parallel results](adversarial-parallel-results.md) for source
90/2b/087/ee6 identities, all fresh-decoder evidence and tradeoffs. The fixed PPM
control achieved an observed 3.16x encoding speedup with four ordered block
workers, identical 354,023-byte archives, and higher CPU work/RSS. Actual DEFAULT
v2 improved complete size by 6.30% and 6.27% on two exposed 1 MiB ranges;
interleaved local replication observed 12.9–13.9% faster encoding and 52.6–55.1%
faster decoding. Fixed-mix allocation removal preserved exact bytes but showed
no reliable throughput improvement. Final native release rerun: 178 tests passed.
Native callback ABI passed; Squash shim still needs the local SDK.
These are bounded development results, not full Silesia qualification or ranks.

All input-specific numbers below use the existing official Silesia Dickens file only (10,192,446 bytes; SHA-256 `b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a`). This is a targeted screening comparison, not renewed Silesia qualification. No Squash CPU times are ranked against these local measurements.

## ZPAQ lead reproduction

The pinned Squash data import reports **2,142,935 bytes** for `zpaq/zpaq` level 5 on Dickens. Squash v0.7.0's plugin passes the level string to `libzpaq::compress()`; its source pins libzpaq 7.05. The local stream harness reproduced that size exactly with method `"5"` and a fresh archive-only decoder. ZPAQ 7.15 produced the identical stream bytes and SHA-256.

| Local method | Complete output bytes | SHA-256 | Encode wall / CPU | Decode wall / CPU | Max RSS | Verification |
|---|---:|---|---:|---:|---:|---|
| libzpaq 7.05, method 5 | 2,142,935 | `8d01934319b0938aa2e40a760d27647c2e287efadc8fbe37649a7650cb4e66e6` | 19.21s / 19.20s | 18.34s / 18.34s | 282,880 KiB enc / 272,896 KiB dec | Fresh decoder restored the exact 10,192,446 bytes and source SHA. |
| libzpaq 7.15, method 5 | 2,142,935 | same SHA as 7.05 | 17.59s / 17.58s | 18.28s / 18.26s | 282,880 KiB enc / 272,896 KiB dec | Exact restoration; the version change did not explain the reported size gap. |

The local harnesses invoke libzpaq's stream `compress`/`decompress` API with method string `5`, retain the library's default stream flags, and run in fresh one-core processes. Upstream published times are from different hardware and are not used here. Complete commands, source identities, timers and archives are under [`runs/zpaq-dickens-v1`](runs/zpaq-dickens-v1/).

### ZPAQ on a frozen Rust representation

ZPAQ 7.15 method 5 was then applied to the complete, already verified Rust CIXG1 BEST archive. The ZPAQ output was **3,507,411 bytes**, a 431-byte expansion over the 3,506,980-byte CIX archive. Fresh ZPAQ decode restored the exact frozen CIX archive SHA-256; fresh Rust `uncix` then restored Dickens exactly. Encode took 11.50s wall / 9.93s CPU; the full ZPAQ-plus-CIX decode took 17.73s wall / 15.38s CPU. Sampled cgroup high-water was about 138 MiB for both phases. This rejects adding ZPAQ as an outer wrapper for this already-compressed representation on this input. It does not reject ZPAQ on raw input (which won at 2,142,935 bytes) or on a different reversible representation.

## Rust CIXG1 BEST and cross-decoding

The release Rust command was `cix --best --route auto --threads 4 --memory 2GiB`, using default BEST 65,536-byte CIXG1 blocks. The selector evaluated 5,304 candidates over 156 blocks, recorded zero memory skips, and selected PPM for every source byte.

| Metric | Verified value |
|---|---:|
| Complete CIXG1 archive, including all frames/footer | **3,506,980 bytes** |
| Archive SHA-256 | `4e02d23f43c48ef2812138a945d650bf9093b42e80cabfd8151258cbe23741d8` |
| Encode wall / CPU | **331.56s / 546.02s** |
| Decode wall / CPU (fresh Rust `uncix`) | **5.34s / 5.32s** |
| GNU `time` max RSS | **41.5 MiB encode / 5.8 MiB decode** |
| Sampled cgroup high-water | 40.4 MiB encode / 13.0 MiB decode (lower bound) |
| Exact restore | 10,192,446 bytes; source SHA-256 matched |
| Python cross-decode | Passed using frozen Python reference checkout commit `0d835c98040a197e37b7432f2ec7a8688116dae6`; all CIX Python module hashes are in the cross-decode manifest. |

The separate verbose repeat produced the same archive size and SHA. Its selector counters were 5,304 candidates, 555.970 candidate-seconds summed across workers, 330.983 seconds total search, 0.113 seconds profiling, and 3,506,980 complete archive bytes. The candidate-seconds sum exceeds wall time because candidate evaluations overlap. The output is deterministic across those two BEST runs.

An evidence audit found that an older version of this summary mixed v3
wall-time with v4 encode CPU and RSS. The figures above now use v3's own
GNU `time` artifacts (CPU 540.01+6.01s; max RSS 42,496 KiB encode and
5,976 KiB decode); scheduler receipt CPU/wall and sampled cgroup values are
reported separately in the immutable receipt and ledger. The manifest also
contains an erroneous 32 KiB block-size field despite omitting that option;
the actual frozen default was 65,536 bytes. See [evidence errata](evidence-errata.md).

### PPM order parameter search (no size gain)

The frozen Python decoder accepts PPM payload orders 0 through 3. An initial 256 KiB interoperability smoke using the Rust encoder's higher orders was rejected: Python raised `ValueError("unbounded PPM order")`. That archive, source sample and encoder log are retained in [`runs/ppm-order-search-dickens-v1/rejected-unsupported-ppm-orders`](runs/ppm-order-search-dickens-v1/rejected-unsupported-ppm-orders/). Automatic exploration is now restricted to orders 1, 2 and the original order 3.

This paragraph describes the historical CIXG1 trial only. The later CIXG2
compatibility extension supports PPM orders 0–8 in Rust and the Python
decoder; orders 4–8 have correctness support but no Dickens size/performance
qualification yet.

On the same Dickens bytes, CIXG1 BEST evaluated 5,616 candidates (312 more than the matched fixed-order run), with zero memory/search-budget skips. It emitted **3,506,980 bytes**, exactly the control size and archive SHA-256, so neither order 1 nor 2 changed any selected encoded bytes on this input. Encode took 327.95s wall / 548.22s CPU; GNU `time` peak RSS was 43,744 KiB. A fresh Rust `uncix` restored the exact source in 5.23s wall / 5.22s CPU at 5,972 KiB max RSS. The frozen Python decoder independently restored the same hash in 98.69s. The runner's equal-size gate marked the attempt `SIZE_REJECTED_UNVERIFIED` and skipped its own decode phase; both decoder checks were then performed manually and verified. The immutable manifest, scheduler claim/terminal, output and cross-decoder artifacts are in [`runs/ppm-order-search-dickens-v1`](runs/ppm-order-search-dickens-v1/).

The order-4+ failure was an implementation gate in the frozen Python
`route_decode()` wrapper, not a limitation of the PPM payload syntax: the
underlying frozen `decode_ppm()` accepts orders through 8, matching Rust's
decoder. An isolated Python compatibility branch now removes that narrower
wrapper gate. Maximum-effort Rust search is being widened to orders 1–8 and
will use the versioned CIXG2 magic; the former trial remains valid historical
evidence for orders 1/2 only. No extended-order Dickens benchmark has run.

### Four-worker dispatch-order experiment (not promoted)

To address the measured 1.65–1.67 CPU utilization despite four leased cores, I compared FIFO candidate dispatch with a coarse cost-priority schedule. Both priority runs emitted the identical 3,506,980-byte archive and passed fresh Rust restoration; the exact archive SHA had already passed a fresh Python decode in the preceding trial. The FIFO encode control was 327.95s wall / 548.22s CPU. Priority runs were 317.13s / 531.88s and 334.21s / 551.91s, averaging 325.67 seconds—only 0.7% faster than the single FIFO measurement, with one replicate slower. CPU utilization remained 165–167%. This does not establish a speedup, so I removed cost-priority dispatch and retained the simpler FIFO queue with four bounded workers. Full manifests, progress, receipts and both outputs are in [`runs/ppm-dispatch-priority-dickens-v1`](runs/ppm-dispatch-priority-dickens-v1/).

## Bounded candidate parallelism

Rust `--threads` now accepts 1–4 for CIXG1 selection. Each frame uses at most the declared number of workers; they draw from one atomic candidate queue so idle workers take the next candidate. The final size reduction is deterministic: smaller complete payload wins, and equal-size candidates retain original selector order. Candidate temporary memory is limited by dividing `--memory` evenly across workers; CIX frames still emit in source order and no block queue is created.

A Dickens FAST smoke with one and four workers produced byte-identical archives (SHA-256 `455ff83d59ff87eb5d4c440801ea12825cccdd59b7f16d9f0bd98c58200475d8`) and exact fresh Rust restoration. Informal local timing was 16.93s wall / 16.87s CPU / 5.5 MiB max RSS for one worker and 11.66s wall / 16.38s CPU / 9.6 MiB max RSS for four workers, or **1.45× wall-time speedup**. It was a functionality/performance smoke, not a scheduler-capped benchmark. The bounded BEST run averaged 164% CPU over 331.56 seconds (1.64 cores), showing real parallel execution but also substantial serial/imbalanced work; no valid single-thread BEST run completed, so no BEST speedup factor is claimed.

## Size context (not a matched algorithm ablation)

| Encoding | Complete bytes | Relative to Rust BEST CIX |
|---|---:|---:|
| ZPAQ 7.05/7.15 method 5 stream | 2,142,935 | Rust is 63.65% larger |
| ZPAQ 7.15 method 5 over complete Rust CIXG1 | 3,507,411 | 431 bytes larger than the unwrapped Rust archive |
| Frozen Python CIX `size` portfolio screening result | 2,799,567 | Rust is 25.27% larger |
| Rust CIXG1 BEST | 3,506,980 | reference |

The Python CIX row is a previously verified, one-core CIX adaptive portfolio result on the same input hash: size profile, maximum effort, direct-backend candidates when eligible followed by adaptive/native routes; archive SHA-256 `b4b0e195209b593a3cf7ee047a1addc2556c70035a3fc037b64a44ef3d45c955`. It is useful evidence that the Rust path has not reached Python size parity, but the selectors and route plans differ, so this is not a single-factor causal test. The ZPAQ stream is not a CIX archive. Its smaller size establishes a backend opportunity, not a native CIX model gain.

## Failed, interrupted, and incomplete cells

| Cell | Outcome | Handling |
|---|---|---|
| First one-worker Rust BEST attempt | Explicitly interrupted at user request to use multiple CPUs | Partial bytes retained in `runs/zpaq-dickens-v1/rust-cix-best.cix`; not a valid archive, size, or decode result. |
| First four-CPU attempt | Runner made immutable copied executables non-executable; process exited 126 before codec code | Preserved terminal failure in `runs/zpaq-dickens-v2-parallel/`; no compression result. Runner now preserves executable mode in read-only snapshots. |
| Fixed-batch four-CPU BEST attempt | Reached its frozen 300-second encode limit with no complete archive | Preserved in `runs/zpaq-dickens-v2-parallel-fixed/`; its incomplete temporary file is not counted or decoded. This motivated the dynamic work queue and longer predeclared Dickens-only budget. |
| Unscheduled exploratory Python cross-decode attempt | Interrupted and excluded after detecting it was outside the bounded scheduler | Its partial `/tmp` output is not evidence. The later successful Python cross-decode ran through WaveScheduler with the source inaccessible. |

The longer successful dynamic-queue trial was predeclared with a 600-second total encode-plus-decode ceiling, four leased physical cores, 2 GB cgroup memory, 100 MB temporary-space ceiling, and zero swap. It finished in 337.28 seconds total including both phases.

## Next experiments, ordered by expected value

1. **Matched ZPAQ representations:** feed original bytes and each frozen Rust-native reversible CIX representation to the same ZPAQ 7.15 method-5 stream, then decode ZPAQ followed by the representation decoder. Charge all representation-generation time/bytes, metadata and decoder steps. Attribute any gain to represented input plus ZPAQ, never to a native CIX model. Python is a decoder validator only.
2. **Native lightweight prediction:** add one small order-0/1/2 adaptive bit/byte model and recurrence/periodic probes as independently framed CIX candidates; first compare against the same raw, composition, PPM and DEFLATE blocks. Avoid importing PAQ/ZPAQ model complexity until an incremental win is measured.
3. **PPM cost/profile:** break out encode cost inside the CIX PPM route and compare CIXG2 orders 0–8 under exact complete-frame cost. The historical CIXG1 order-1/2 search did not improve Dickens over order 3. Orders 4–8 now have decoder compatibility but remain unqualified.
4. **Coder ablations:** hold frozen representations fixed and compare CIX exact-rank, adaptive range, count/rank, DEFLATE, implemented CIXG2 canonical Huffman, and a native FSE/ANS implementation where its dependency/build is available. Include all coder and route identifiers in measured cost.
5. **Transform combinations and parsing:** measure both orders for BWT/MTF/run coding, stride/residual and prediction; compare lazy/cost-aware LZ parse decisions against the current bounded hash chain. Use small blocks plus an exact exhaustive oracle before any larger trial.
6. **Selection scoring:** record shortlist omissions against the finite exhaustive oracle on small blocks; repair route feature misses separately from cost estimator errors. Do not call the present BEST search exhaustive.

Promote a method only after a frozen candidate setting restores exactly in a fresh native process, includes complete framing, and survives disjoint replication. Retain historical Python compatibility validation for existing formats; it is not a runtime or new-format research gate. No broader source acquisition or non-Silesia local result comparison is authorized by this programme.

## ZPAQ 7.15 method-5 model audit

Local source inspection confirmed that method 5 is a dynamically generated model,
not just a fixed higher-order PPM. In
`/home/user/src/cix-baseline-tools/zpaq715/libzpaq.cpp`, the method-5 path
builds the base configuration `w1i1,c256ci1,1,1,1,1,1,2a`, scans the input for
last-occurrence positions and a 4,096-bin recurrence-gap histogram, chooses up
to two periodic models under its score threshold, then appends contexts and
mixers including `c0,2`, `c0,3`, `c0,4`, `mm16`, `ts19`, and `t0`. Since the
Dickens invocation is method 5 (`type=512`), it does not take the text-specific
`w2...` branch.

The resulting model graph uses adaptive CM/ICM, ISSE transforms, a rotating
history MATCH model, MIX/MIX2 adaptive probability mixing, and SSE calibration.
`libzpaq.h` documents ordinary/masked history, periodic offsets, and distance
since last byte occurrence as context features. The dynamic context generator,
context hashing, ISSE chains, and MATCH model are implemented around
`libzpaq.cpp` lines 7394–7499; the level-5 selection path is around lines
7646–7705. Source versions and complete model behavior are not inferred from
Squash timing rows.

Rust overlap is partial and distinct: `adaptive.rs` codes bytes with
multinomial context buckets; `fixedmix.rs` is a bitwise adaptive mixer with
fixed lags and a bounded four-byte exact-match predictor; `expertmix.rs` selects
byte-context count tables; `stateful.rs` carries selected count-model state.
None reproduces ZPAQ's dynamic recurrence scan, ISSE chain, rotating MATCH,
MIX/MIX2 graph, or SSE calibration. The next native hypotheses are therefore
(1) bounded recurrence-distance context features, (2) up to two input-selected
periods, (3) an ISSE-like fixed-point chain, (4) a bounded rolling MATCH
predictor, and (5) post-mixer calibration, each added and ablated separately.
These are proposed native models, not a port or a ZPAQ backend result.
