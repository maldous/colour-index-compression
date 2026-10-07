# Generic adaptive CIX — completed implementation checkpoint

Acquisition is closed at **2026-09-30T11:04:27Z**. A runnable versioned
encoder/decoder, bounded feature selector, paid stream representations,
effort profiles, format description and reproducible local evidence are
delivered. No downloads, full Silesia/enwik9/Hutter compression, Actions or
external publication occurred in this implementation phase.

## Coverage and continuity

The usable acquisition subset is **12 Silesia originals, 25 declared-size
FCBench members and Compression Golf's supplied training corpus**. The Golf
gzip and extracted JSONL are two artifacts of one dataset. Silesia publisher
MD5 values pass; all usable artifacts were completely reread for local
SHA-256 identity at cutoff. FCBench/Golf do not gain publisher verification
from those calculated hashes. Collection coverage remains FCBench PARTIAL,
Golf evaluation PARTIAL, RAI BLOCKED and GDCC BLOCKED. Exact identities and
gaps remain in `acquisition-cutoff.json` and the preserved preparation report.

The old implementation/evidence is recoverable at
`research-before-generic-pipeline-20260930` (`19b822c8e82f59e26c9e33fc6600ad74c7eded32`)
and the external baseline TAR. No replication jobs were active at the initial
process audit. All historical molecular/numerical archives and verified
replication results remain untouched. Historical Silesia gains came from
structural constraints, field/group prediction and backend changes; none is
represented here as a universal CIX ordering-coder victory.

The frozen selector source SHA-256 is
`4ee5b59cafddb285223f0a5c6ddac88e2404295ef7238a1568a703c210def2b5`.
Source was delivered at `f585b22`; the core has not changed during or after
held-out evaluation. An initial scheduling preflight found that old CPU0/2/4/6
assignments were unavailable; before any experiment claim the declarations
were updated to available distinct physical CPUs16–19. That correction did
not change the codec or selector. One additional explicitly declared coder
audit removed substream eligibility differences without modifying production.

## Primary comparisons — each input is exactly 16,384 bytes

All below passed independent archive-only decode, SHA-256 and subsequent
full byte-for-byte comparison. New sizes include all dictionaries, rules,
stream descriptors, count tables, payload, block/whole-stream checksums and
framing. Old CIX is the unchanged generic `config_for_level(1)` stream, with
its existing CRC/framing rather than the new SHA-256 framing. Timings include
launch, input/output and every discarded encoder trial.

| Fixed input / role | Frozen CIX B | Balanced CIX B | Change B | Saving vs baseline | Baseline E/D s | New E/D s | Winning representation |
|---|---:|---:|---:|---:|---:|---:|---|
| FCBench msg prefix / development | 14,432 | 12,746 | -1,686 | 11.6824% | 10.53 / 0.89 | 0.49 / 0.06 | Input-derived two-byte phrases |
| FCBench MHD prefix / development | 618 | 500 | -118 | 19.0939% | 2.41 / 0.11 | 0.34 / 0.07 | LZ separated streams |
| Golf prefix / development | 2,810 | 2,853 | +43 | -1.5302% | 2.71 / 0.13 | 0.45 / 0.06 | Original-byte DEFLATE |
| FCBench PT, 8 MiB offset / held out | 13,361 | 12,749 | -612 | 4.5805% | 4.74 / 0.27 | 0.37 / 0.06 | Generic XOR/shuffled byte planes |
| FCBench rsim, 1 MiB offset / held out | 29 | 103 | +74 | -255.1724% | 0.68 / 0.07 | 0.30 / 0.06 | Runs |
| Golf, 1 MiB offset / held out | 2,740 | 2,770 | +30 | -1.0949% | 2.52 / 0.12 | 0.44 / 0.06 | Original-byte DEFLATE |

The rsim slice contains **16,383 zero bytes and one byte 64**, so it is a
near-constant correctness/control case, not representative evidence for a
whole numerical corpus. Earlier progress shorthand called it all-zero; this
is its exact measured composition. New checksum framing dominates its size.
No replacement holdout was selected after exposure. These small slices do
not establish whole-file scaling, full-corpus performance or a leaderboard.

## Unmodified same-hardware references

| Input | gzip-9 B | bzip2-9 B | XZ-6 B | Brotli-6 B | Balanced CIX B |
|---|---:|---:|---:|---:|---:|
| msg development | 14,745 | 15,201 | 13,344 | 14,752 | 12,746 |
| MHD development | 474 | 649 | 472 | 367 | 500 |
| Golf development | 2,745 | 2,834 | 2,572 | 2,619 | 2,853 |
| PT held out | 15,674 | 16,453 | 13,684 | 15,292 | 12,749 |
| rsim held out | 56 | 52 | 124 | 19 | 103 |
| Golf held out | 2,658 | 2,777 | 2,496 | 2,532 | 2,770 |

The reference codecs are substantially faster on these small inputs. New
CIX is smaller than all four references only on the two shown msg/PT slices;
it is not the best compressor across this set. Zstandard is absent from the
current runtime and is an explicit reference-coverage gap, not a fabricated
measurement. PAQ is not imported into this generic pipeline because its
specialized models would violate the requested policy. Historical matched
PAQ receipts remain a separate evidence source.

## Attribution and ablations

The msg winner carries a 65-byte dictionary, 28 bytes of stream descriptors,
12,558 coded bytes, a 41-byte block frame and 54 bytes of header/end framing.
Its stream coders are DEFLATE/raw/DEFLATE. Removing the phrase route raises
the complete archive from **12,746 to 13,074 bytes**; the next winner is a
stride transform. This demonstrates representation plus hybrid selection,
not a rank-coder gain. Its search/launch overhead was 0.363 seconds.

MHD's LZ winner uses CIX exact ranks for tags/literals and raw length/distance
streams. Its 500-byte total comprises 80 paid count bytes, 42 stream/tile
descriptor bytes, 283 coded bytes, 41 block-frame bytes and 54 global bytes.
This is a complete LZ-plus-CIX result; the larger difference from the old
baseline is not attributable solely to rank ordering. The PT heldout winner
uses mixed raw, DEFLATE and CIX plane coding. Its paid count tables are 20
bytes; its transform marker and descriptors are 78 bytes.

The initial `cix`/`count-range` portfolio controls can differ in their eligibility
gates. They are retained in the full table, but only the additional **forced
ordering** audit supports a pure coder comparison: no raw/run fallback or
entropy gate, identical transforms, stream contents, counts and boundaries.
Independent readback confirms equality of those decoded transformed streams.

| Representation | msg exact / range B | MHD exact / range B | Golf exact / range B |
|---|---:|---:|---:|
| LZ streams | 15,169 / 15,221 | 506 / 511 | 3,045 / 3,060 |
| Predictor residual | 15,786 / 15,821 | 2,408 / 2,440 | 7,363 / 7,395 |
| BWT/MTF/run streams | 15,407 / 15,470 | 595 / 601 | 3,165 / 3,187 |
| Stride/plane streams | 14,014 / 14,048 | 1,661 / 1,695 | 13,160 / 13,192 |

Exact ranks save **5–63 bytes** in these paid identical-count comparisons.
The modeled possibility space is identical; this is a bounded ordering,
finite-precision/termination and framing effect, not evidence of eliminating
more uncertainty. Count-table costs range from 97 to 1,830 bytes in the
forced audit. Many complete transformed streams remain worse than the best
generic/reference route. Range-control construction also computes the exact
rank; its encode timing is not a native range-only speed comparison.

The bounded rank microprofile (`rank-cost.json`) verifies 128/512/1024-byte
tiles across the three development inputs, with three individual timings.
The maximum median rank/unrank times observed were **0.002754 / 0.003972 s**.
All hot-path exact integers remain at most 8,192 bits. No file-sized factorial
or rank is built by this pipeline.

All ten one-component balanced ablations and all forced candidates are in
`CANDIDATES.md` and CSV/JSON before portfolio selection. An absent effect in
an ablation means that configuration did not select the component, not that
the entire mechanism is disproven. Maximum/offline search matched balanced
sizes on all six fixed slices while adding roughly four seconds of mostly
unsuccessful mixture work. **Three forced mixture trials hit their four-second
deadline** and remain unqualified. The inherited systemd supervisor reported
zero phase codes even when GNU-time logs contained command failures; those
rows are rejected by missing complete-stream/verification evidence and the
raw failure logs are preserved. No partial archive is a qualified size.

## Bounded larger-input/context tradeoff

The same 131,072-byte Golf prefix was independently reconstructed for each
complete LZ/hybrid archive. These are controlled context/reset diagnostics,
not a full-file score.

| Block bytes | Decoded LZ history bytes | Complete B | Encode / decode s |
|---:|---:|---:|---:|
| 16,384 | 0 | 24,037 | 0.43 / 0.20 |
| 65,536 | 0 | 20,081 | 0.34 / 0.11 |
| 16,384 | 65,536 | 20,262 | 0.49 / 0.22 |
| 65,536 | 65,536 | 19,117 | 0.37 / 0.11 |

Retained history and larger blocks both helped on this input. They cost
cross-block dependence and extra retained memory; independently parallel
blocks cannot claim those same bytes without measurement. The actual CLI
remains serial by block, while independent research cells use four cores.

## Verification, resources and limitations

**187 complete archives verified, three budget failures**, including all 33
full local Canterbury/Calgary/Artificial files (6,362,278 original bytes;
1,865,744 compressed bytes with fast CIX). Every reported completed stream
was decoded in a separate cgroup with source paths inaccessible, SHA-256
matched, rehashed on readback and compared byte-for-byte against its input.
The audit compared 9,344,166 input bytes across repeated candidate cells.
The focused new/core/histogram test run passed **54 tests**.

The maximum measured encoder/decoder process RSS across the wave was
217,580 / 29,260 KiB. Balanced development/holdout runs used about 23 MiB
encoder RSS and 20–21 MiB decoder RSS. RSS is the largest measured process,
not a simultaneous tree total; cgroup measurements remain in the raw receipts.
Every trial used a no-swap memory cgroup and one CPU; the aggregate four-core
wave reserved eight GB RAM and one GB temporary space. Detailed time, CPU,
memory, temporary-space, source/configuration identities and all discarded
trial statuses are preserved. One timing repetition per cell, warm/uncontrolled
cache and a shared host limit speed conclusions.

The fixed heuristic is a first bounded production selector, not a learned
optimal policy. Worker startup and Python costs remain visible. PPM/mixture
escalation did not earn extra bytes within this budget; mixed zero/low-entropy
blocks expose framing losses. Header/frame expansion is explicitly bounded.
Synthetic high-entropy and repeated-high-entropy correctness tests confirm
that count entropy alone cannot veto repetition routes; no claim is made
that incompressible random data becomes small. Existing Artificial `random.txt`
is a historical asset, not a cryptographic-random guarantee.

Distribution program/runtime footprint is reported separately in `runtime.json`;
no minimal package, licence clearance, Hutter score or eligibility is claimed.
The next justified work is broader fixed real-byte coverage and cheaper
selection/escalation, followed by larger contiguous replication of successful
routes. These findings do not authorize resumed acquisition or qualification.

## Reproducibility and review

See `FORMAT.md` for the runnable encode/decode interface and complete format;
`PLAN.md`, `inputs.json`, manifests and `selector-freeze.json` for declarations;
`results.csv`/`results.json` and `CANDIDATES.md` for every candidate; `runs/` for
raw commands, timing/resource logs, failed attempts and verified receipts;
`independent-audit.json` for readback/byte-equality and ordering controls.
Archives, sources, restored inputs and immutable builds are retained locally
and untracked. Exact source snapshots are recoverable from the private commits.
Use `benchmarks.generic_research summarize` and `benchmarks.generic_report`
to regenerate and independently check the report inputs.
