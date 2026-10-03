# Numeric representation × incumbent CIXM6 composition

## Decision

**A — composition opportunity rejected within the frozen numeric slice and
finite neighbourhood.** Original CIXM6 is **1,393 B**. The frozen discovered
representation is **1,418 B**, a **25 B / 1.79% loss** after its required
29-byte description. No nearby representation produces a smaller complete
archive than original CIXM6. Production remains unchanged.

Experiment: `composition-m6-citytemp-v1-buildfix1`.
Parent checkpoint: `0de785c44f58c681386131fbcfa4d67417351814`.
Incumbent production revision: `d3a2cd416e49f93403d1dbd348a3e9a45db66ec6`.
The successful wrapper source hash is
`6bfe34a88e8622281a95e0a67830826f5c7cb6cbca4ab9ad6f066a706c39e2ce`.
The initial compiler-only failure, source and freeze remain in failed-build/
and raw/; no input or archive trial ran before the compile-only repair.

## 1. Frozen input, settings and accounting

The authorised local source is `citytemp_f32`, 11,625,304 B, whole SHA-256
`3f8ba1a80684edea13185934a2ec4a612715f1942f81e94d76c60e00b568ba7f`.
The predeclared new slice is offset **1,048,576**, length **4,096 B**, SHA-256
`d9b5b011beef2e414cbb55b6167a875c8b19dacbc0d139ea7ab4cad3920dd765`.
EXPOSURE-REVIEW.md records disjointness from documented algorithm exposure;
this is not an absolute claim about undocumented historical reads. Source
identity/offset choose an experiment input, never an encoder route.

Frozen E: width4, phase0, operators `[0,2,1,0]`: identity, previous-original-
column modular subtraction, previous-original-row modular subtraction,
identity. First suffix rows are literal. Prefix/tail reconstruction derives
from paid length/geometry. Prefix bytes stay inside the backend stream.
No new transformation, geometry search, segmentation or learned dependency was
added. The finite 15-description bank was fixed before extraction.

All CIXM6 bodies use the sealed d3a2 native executable:
`--best --format cixm6 --threads 1 --memory 1536MiB --block-size 16KiB -c`.
This explicitly tests incumbent M6, not the broader automatic packaging
portfolio. All Zstd bodies use local Zstd1.5.5 `-q -19 -T1 -c`.
Original controls also include gzip1.12 `-n -9`, bzip2 1.0.8 `-9`, and
XZ5.4.5 `-9e -T1`; settings were frozen and pre-run version receipts recorded. Post-run executable
hash readbacks match the prior latent checkpoint; tool-bindings.json distinguishes
that readback from prelaunch enforcement.

SMC1 pays fixed25B plus one operator byte per lane: source/transformed lengths,
CRC32, width/phase/operator count/vector, backend, body length, magic/version.
The entire backend archive is inside the paid body. There are no external
models, source constants, free alignment, dictionaries or decoder search.
Decoder-generated model work is CPU/memory, not invented wire bytes.
**Original M6/Zstd baselines are bare archives without SMC1 tax.** Wrapped
identity is only a diagnostic control. FORMAT.md specifies every field.

## 2. Complete same-data factorial matrix

| Arm | Representation/backend | Complete B | Difference from A |
|---|---|---:|---:|
| A | Original → CIXM6 BEST |1393|0|
| B | Fixed BSS `[0,0,0,0]` → CIXM6 |1745|+352|
| C | All previous-column residual `[0,2,2,2]` → CIXM6 |2524|+1131|
| D | Best exact ordinary mask `[0,2,0,0]` → CIXM6 |1536|+143|
| E | Frozen discovered `[0,2,1,0]` → CIXM6 |1418|+25|
| F | Same frozen representation → Zstd19 |1655|+262|
| G | Original → Zstd19 |1804|+411|
| H | Original → XZ9e |1720|+327|
| H | Original → bzip2-9 |1808|+415|
| H | Original → gzip-9 |2147|+754|

The frozen representation beats the declared non-CIX controls, and the
ordinary masked M6 controls, but **does not beat incumbent original M6**.
These new bytes/settings are not the old prefix; historical1231B is not
reused as a baseline for this slice.

### All measured descriptions and retained losses

All entries below include their paid SMC1 descriptions, including the identity
diagnostic (26B). Native is the four-route lane proxy, not incumbent CIX BEST.

| Description | Width/phase/operators | M6 B | Zstd B | Native proxy B |
|---|---|---:|---:|---:|
|original|1/0/[0]|1419|1830|2028|
|mask0|4/0/[0, 0, 0, 0]|1745|2049|1848|
|mask1|4/0/[0, 2, 0, 0]|1536|1814|1716|
|mask2|4/0/[0, 0, 2, 0]|1760|2043|1856|
|mask3|4/0/[0, 2, 2, 0]|1585|1811|1724|
|mask4|4/0/[0, 0, 0, 2]|2548|3034|2762|
|mask5|4/0/[0, 2, 0, 2]|2337|2756|2630|
|mask6|4/0/[0, 0, 2, 2]|2699|3048|2770|
|mask7|4/0/[0, 2, 2, 2]|2524|2773|2638|
|E|4/0/[0, 2, 1, 0]|1418|1655|1544|
|drop-prevcol|4/0/[0, 0, 1, 0]|1593|1930|1676|
|row-xor|4/0/[0, 2, 4, 0]|1464|1684|1594|
|last-residual|4/0/[0, 2, 1, 2]|2315|2692|2458|
|phase-one|4/1/[0, 2, 1, 0]|1784|1997|1861|
|width-three|3/0/[0, 2, 1]|2739|3325|2996|

Thirty unique backend encodings (15 M6,15 Zstd),15 native proxy encodings and
three external controls were measured:48 compression trials. Original M6/Zstd
bodies are reused by the wrapped identity arms after exact transformed-byte
comparison; descriptors and fresh decodes remain paid. There were no accidental
same-byte aliases among other descriptions. Every cost uses physical archives.

## 3. Representation/backend interaction

Positive gain means fewer complete bytes:

- Paid M6 representation gain: `1393 - 1418 = -25 B`.
- Paid Zstd representation gain: `1804 - 1655 = +149 B`.
- Original M6 backend gain against Zstd: `1804 - 1393 = +411 B`.
- Same-representation M6 backend gain against Zstd: `1655 - 1418 = +237 B`.
- Difference in differences: `(-25) - 149 = -174 B`.

Thus the representation helps Zstd but adds no complete-size value to the
stronger incumbent M6 on these bytes. Backend strength is not credited as a
new native model or structural theory improvement.

Loss decomposition: original M6 =1373B route payload +20B inner framing.
Transformed M6 =1369B route payload +20B inner framing +29B front descriptor.
The inner archive saves4B; the descriptor costs29B; net loss25B. Both select
one mode3 legacy-LZ frame, one initial/reset model state and the same history
limit1MiB. There is no additional frame/reset penalty here. The experiment
does not establish a causal loss from destroyed contexts; observed route,
payload and framing sizes provide the attribution that is actually supported.

## 4. Does incumbent M6 change the selected representation?

Within the15 *wrapped* candidates all three backends prefer E: native1544B,
Zstd1655B, M61418B. Cross-backend rankings differ (Spearman native/M6=0.8893,
Zstd/M6=0.9607; diagnostics only), but this slice demonstrates no change of
best represented geometry. Once the mandatory bare original alternative is
included, **M6 prefers no front-end representation:1393B**. The wrapped
identity costs1419B; a1B win against that artificially taxed diagnostic is not
a win against A. No broader backend-independence conclusion follows.

Native top-k shortlists k=1/2/3/5/15 all retain the best *wrapped* M6 candidate
E and have0B wrapped-bank regret. Omitting the bare fallback would still lose
25B against the deployable finite-family minimum. Keeping A always yields
1393B and0B total regret. analysis.json lists each shortlist and byte regret.
This small result does not justify proxy pruning on other inputs.

## 5. Encoder/decoder work and memory

Hardware: Intel Core i9-13900K,24 physical cores/32 logical CPUs; trial affinity
CPU8 and100% quota, one worker. Aggregate cgroup budget2GiB, swap0, temporary
budget64MiB. Rustc1.98.1, portable `rustc --edition=2021 -O` wrapper, frozen
release rlib and native libraries; commands/hashes are in freeze/environment
and the explicitly post-run tool-bindings readback.
One observation per cell, no averages or imported timing rankings.

| Cell | Encode wall s | Encode CPU s | Encode peak RSS KiB | Fresh decode wall s | Decode peak RSS KiB |
|---|---:|---:|---:|---:|---:|
| A original M6 |8.8792|8.86|23336|0.03443|9984|
| E transformed M6 body |8.5274|8.51|23556|0.00783|6480|
| E native proxy |0.01559|0.01|5440|0.00141|4608|
| F transformed Zstd body |0.00352|below0.01s receipt resolution|2816|0.00138|4608|

E also pays transform0.00142s and wrapper construction0.00144s; F construction
0.00139s. These short process timings include launch/measurement overhead and
cannot establish statistically reliable speed rankings. M6 fresh decode
includes the wrapper child and inverse transform. No external Python decoder
is used; Python is the scheduler/measurement and independent byte oracle only.

All15 M6 encodings consumed151.07s wall/150.55s CPU in total;15 native proxy
encodings0.3945s wall/0.20s CPU;15 Zstd encodings0.0324s wall with each CPU
receipt below coarse resolution. These totals include rejected candidates.
Entire matrix phase:152.227s elapsed,151.545s cgroup CPU. Peak process encode
RSS23804KiB. Sampled aggregate cgroup high-water49,684,480B is a **lower bound**,
not a claimed true aggregate peak; it includes orchestration. Temporary
high-water5,577,456B. Raw GNU-time/cgroup receipts and per-cell metrics remain.

Full BEST-in-the-loop layout enumeration would be expensive relative to the
proxy. This measurement is search-economics evidence only; the failed size
gate does not authorise developing a larger shortlist selector.

## 6. Exact reconstruction and rejection evidence

All45 SMC1 matrix archives plus five bare controls restored byte-for-byte in
fresh native decoder processes. An independent pass freshly decoded all45
SMC1 archives again and checked declared lengths/CRC. Thirty tiny native
archives independently compare Rust transform/inverse against a byte oracle
across n1..32, widths1..8, phases0/w-1, all five operators and partial tails.
The matrix additionally checks every frozen vector on the input and13B tail
example. check-results.json contains37 malformed/unsupported rejections:
outer fields/CRC/truncation, M6 canonical varints/overflow/mode/source/payload/
footer, Zstd concatenation/content/window, native route/length/trailing and
oversized Huffman embedded output length. Empty input is explicitly unsupported
by this bounded experimental wrapper, not silently accepted.

Preflight also bounds child stdout to n+1 and kills/waits on overrun/read error;
no independent injected child-overrun test was run. This is a stated validation
limit, not an inferred passed dynamic test. The wrapper caps input4096B and
archive32768B, buffers complete bounded input, lacks production atomic writes,
and is offline/non-streaming. No production-readiness claim follows.

## 7. Gate, retained negatives and next action

Replication gate failed. The2MiB reservation was **not extracted or used by a
codec**; receipt identity hashing of the whole source is not representation
profiling. No conditional-replication result is fabricated. No tuning followed
this slice. Wider strides/transforms, local segmentation, dependency DAGs and
model-language expansion remain gated. All earlier0de785c44 negatives and
historic12/59B metadata wins remain unchanged; this is not a novelty claim.

**Exactly one next action: checkpoint and close the numeric composition branch,
retaining unchanged incumbent CIX and its no-transform alternative.**

## Reproduce and inspect

The already-run matrix cannot be overwritten silently. A fresh replay requires
an explicit new identity and separate artifact/evidence paths. The frozen
commands are `python3 schedule.py` and `python3 schedule_checks.py` from this
evidence directory; their scripts use absolute repository paths and scheduler
leases. `python3 analyse.py` recomputes accounting/ordering from retained
receipts without new codec runs. All input/archive bytes stay in
`benchmark-work/constraint-composition-m6/`; artifact hashes/bindings are here.
