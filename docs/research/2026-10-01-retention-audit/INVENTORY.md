# Retention and backend coverage inventory

Baseline: private commit `1302bd7bec130c3105181e6a23ee82c6f2a04838`.
The precise pipeline hash, presets and limits are in `inventory.json`.
The new integration completed 120 verified screening cells, including
three independently decoded repetitions per cell. Historical specialized
implementations remain preserved. See REPORT.md and independent readback receipts.

## Implementations and eligibility

| Family | Available representations / presets | Scope of this round |
|---|---|---|
| CIXG1 | raw, runs, composition, lz, predictor, bwt, stride, phrases, ppm, mixture, deflate; fast/balanced/maximum | Frozen baseline, all eleven forced routes in every profile |
| CIXG1 stream coders | raw, RLE, bounded exact CIX rank, raw DEFLATE, adaptive range, paid-count range | Matched original-byte controls and compatible transformed streams |
| CIXM6 | 21 block modes; CLI levels 1–9 and extreme | Available standalone, not integrated or measured by this six-slice round |
| Historical competitive portfolios | Molecular, database, spatial, numerical, executable and PAQ wrappers | Separate format-specific evidence; not generic CIXG1 routes |
| New CIXB1 portfolio | Exact eligible reference codec payload plus 47-byte envelope, or unchanged CIXG1 archive | Measured original, fresh 16 KiB and reserved 64 KiB comparisons; all 144 portfolio minimum checks passed |
| Optional CIXR1 experiment | One native encoding pass over a completed CIXG1 archive, including outer framing/hash | Separate candidate; retain original if total result grows |

CIXM6 modes are raw, multinomial, context, LZ, BWT, transform, bitplane,
chain, numeric, reference/dedup, adaptive, sparse, runs, persistent adaptive,
record, periodic, PPM, expert mix, wavelet, fixed mix and histogram/count-vector.
Its preset beams, history and state differ from CIXG1. Availability is not
evidence that these presets have been evaluated or retained inside CIXG1.

## Exact reference presets and integration plan

| Reference | Speed | Current | Size | Integration / decoder closure |
|---|---|---|---|---|
| gzip | 1 | 9 | 9 | Exact Python gzip payload, mtime=0; gzip decoder |
| bzip2 | 1 | 9 | 9 | Exact Python bz2 payload; bzip2 decoder; speed shortlist excludes it |
| XZ/LZMA2 | 0 | 6 | 9 extreme | Exact Python lzma payload; XZ decoder; speed shortlist excludes it |
| zstd | fast=131072 | 3 | 22 ultra | Same pinned single-thread, no-asyncio binary; Zstandard decoder |
| Brotli | 0 | 6 | 11 | Quality 0 eligible with pinned 1.2.0 dictionary-free path; 6/11 policy excluded |
| paq8px | v216 -1 | v216 -8 | v216 -12L, five LSTM layers | Not generic-policy eligible: content-specific models; maximum also exceeds aggregate RAM limit |

PAQ's AVX2 execution option alone is not a content-specific model and is not
the reason for exclusion. Its actual specialized prediction/transform paths
conflict with the generic policy. Brotli's fixed word dictionary conflicts
with the input-derived-dictionary requirement; its audited quality-0 path is
treated separately. Excluded exact presets remain visible external references.
They are never silently replaced by weaker presets and ranked as equivalent.

The CIXB1 payload is the exact reference archive, not an approximation to its
coder. The additional 47 bytes identify the backend/profile, input/payload
lengths and SHA-256. Decoder programs/runtimes are separately identified;
there is no hidden per-input dictionary or external data. CIXB1 has a deliberate
16 MiB adapter input bound. ZPAQ is not among the six ranked references and is
not implemented inside this portfolio.

## Frozen selector scope

CIXG1 uses bounded observable-byte profiling to shortlist routes. It compares
materialized payload lengths, including representation metadata. Common block
framing adds the same cost to each alternative. Raw is retained and replacement
requires a strictly smaller complete block. The whole single-block archive
adds 95 bytes relative to raw input. Forced-route trials are diagnostic and
may expand; they do not demonstrate a selector regression by themselves.

Fast: 32 KiB blocks, 2 KiB profile sample, four shortlisted candidates,
0.75-second search, 0.30-second route cap, 256 MiB worker cap.
Balanced: 32 KiB blocks, 4 KiB sample, seven candidates, three-second search,
one-second route cap, 384 MiB worker cap.
Maximum: 64 KiB blocks, 8 KiB sample, ten candidates, twelve-second search,
four-second route cap, 512 MiB worker cap.

The entropy gate can avoid attempting exact-rank stream coding; profile
shortlists and search deadlines can exclude a better route. Estimates cannot
win selection, but pruning narrows the guarantee. The guarantee is restricted
to completed eligible candidates actually evaluated, not all installed methods.
An additional encoding pass is acceptable only if its complete archive is smaller.

`composition` always uses exact CIX streams; `deflate` always uses DEFLATE;
PPM and mixture ignore the stream-backend switch. Hybrid compares raw, RLE,
entropy-gated exact rank and DEFLATE on each stream. Range and paid-count range
are stream-coder alternatives, not new structural representations. Compare
coding claims only with identical transformed data and paid predictive information.

The new maximum portfolio schedules all policy-compatible direct reference
routes before adaptive/forced CIXG1 alternatives. Its declared search budget is
60 seconds; fast/current retain 0.75/3-second search budgets. Independent
candidate validation time is additional measured audit work and is included
in full invocation time, not hidden as production search time.

## Six input labels

| Slice | Exact source member | Offset | Bytes |
|---|---|---:|---:|
| fcbench-msg | msg_bt_f64 | 0 | 16,384 |
| fcbench-mhd | astro_mhd_f64 | 0 | 16,384 |
| golf | compression-golf/data.json | 0 | 16,384 |
| fcbench-pt-heldout | astro_pt_f64 | 8,388,608 | 16,384 |
| fcbench-rsim-heldout | rsim_f32 | 1,048,576 | 16,384 |
| golf-heldout | compression-golf/data.json | 1,048,576 | 16,384 |

Golf and GitHub events identify the same downloaded asset. The two slices are
distinct offsets, not independent datasets. These original `heldout` slices
were previously evaluated and are exposed. New content-blind ranges, selected
before compression, have separate frozen hashes/exposure records. The nearly
constant RSim slice cannot support a general conclusion about numerical data.

## Evidence and restrictions

Frozen prior evidence: `../2026-09-30-generic-pipeline/`,
`../2026-09-30-codec-profiles/`, `../2026-09-30-representation-coverage/`,
`../2026-09-30-representation-benefits/`.
New baseline: `../2026-10-01-retention-round-v2/`.
Implementation: `cix/pipeline.py`, `cix/multinomial.py`, `cix/cli.py`,
`cix/backend_portfolio.py`, `benchmarks/retention_round.py`.

Four physical cores, decimal 12 GB RAM and decimal 4 GB temporary-space cap
are shared across the wave. Jobs cannot swap. No acquisition, Actions,
full-enwik9 qualification or publication of private source is authorized.
The user authorized one evidence update on the existing public Site after
this round, with all exclusions, failures and missing measurements visible.
