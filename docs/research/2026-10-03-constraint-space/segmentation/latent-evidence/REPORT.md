# Six follow-on: latent byte geometry and joint representation/backend selection

## Verdict and scope

The frozen generic LLT1 prototype discovers byte width/phase and selects paid
literal/delta/XOR representations and five-route lane/global coding by actual
complete cost. It passed exact inverse, independent tiny reference and malformed
input checks. It improves on opaque bytes and literal BSS on bounded synthetic
cases. Strong ordinary mask/uniform controls explain almost every synthetic
win. One changing-correlation case gains2B beyond these controls.

A frozen numeric4096Bprefix gains20B over the smallest non-CIX declared control
(bzip2), and280B over the exact ordinary mask control. Incumbent CIX BEST is
still126Bsmaller. Other real prefixes lose to their strongest controls. The
candidate is a measured size/time/memory tradeoff, not durable superiority,
new compression theory, a recovered schema, or a production-ready stream.
Production remains unchanged. No Actions, Sites, Hutter, acquisition or external
computation was used. Agents prepared/reviewed disjoint files; root alone ran
all codecs under the existing scheduler and privately checkpoints evidence.

## 1. Queued metadata result and prior-art boundary

The queued support investigation completed first atc4cdad4d1. Twelve existing
archives reconcile exactly; NCSL already pays one global stride/mask. No repeated
support table exists to factor. Packed/compressed metadata/diagram trials were
not fabricated for a nonexistent model. This is an applicability closure,
not an experimentally demonstrated optimality result about all future sharing.
See ../support-evidence/REPORT.md. Earlier byte-scale/packed-control negatives
and original12/59B model-description wins remain immutable.

../latent-prior-art.md reviews primary Parquet/Arrow BSS, Lance statistics and
configuration material, and CAST repository/source/paper. BSS and independent
column transforms are established; CAST challenges schema-free structural text
preprocessing. Our arbitrary-byte stride/phase mapping does not infer CAST
skeletons or semantic fields. No fair already-installed CAST executable/control
was available in this bounded investigation; no CAST performance superiority
is claimed. Lance sources reviewed provide positional entropy signals but do
not establish the asserted deployed automatic-BSS policy; the note preserves
this read limit rather than claiming global absence.

## 2. Missing attribution matrix, now physical

../attribution-evidence/REPORT.md contains59new archives on identical exposed
bytes with one matched native libZstd1.5.5level19 ZSC1 wrapper (21B). Every
literal inferred-width arm reuses its identical fixed BSS cell. Existing
native-selected and same-mask-Zstd archives are hash-checked and reused.

| Existing exposed width | Original Zstd | Literal BSS | All residual | Selective residual | Old native |
|---|---:|---:|---:|---:|---:|
| 3 |1106|1053|1051|597|710|
| 4 |1094|1172|826|484|640|
| 5 |1013|1244|692|416|622|

Separation alone saves53B atwidth3 and loses78/231B atwidth4/5. Selection after
all-residual adds454/342/276B. Native-to-Zstd net113/156/206B includes
23/32/41Bouter-framing saving and90/124/165Bpayload/backend saving. No native
model credit is assigned to backend gains. ABA's nativewidth1 also misses a
width2BSS/Zstd5Bsaving: geometry is not backend-independent.

## 3. Frozen finite joint search and exact reference

Source8611d8ef10279025d4b878d0340358b6b4c50f7317a15e63a08d55ace19e52b8,
experiment latent-layout-joint-v1-buildfix1. The initial compiler-only E0382
failure is retained with source/freeze/logs; computing byte lengths before moves
fixed it before any input generation or archive cell. No cell was repeated.

Geometry: width1..8, phase0..w-1, suffix atsource[phase..], literal raw prefix,
partial row lengths derived exactly. Tiny n<=12 uses widths<=3 in every policy;
wire-valid and search-admitted geometry are distinguished. Input<=4096B,
archive<=32768B, one canonical empty header. No width/schema/label from fixture
metadata reaches the encoder. Exact predictor bytes are identity, previous-row
subtraction/XOR, or previous-column subtraction/XOR. First suffix row is literal.
All violations remain exact residual bytes, not a free exception map.

Paid H18 header includes n/CRC/width/phase/kind/count/prefix length; prefix bytes
are paid. Lane records pay10B(op,route,decoded_len,payload_len) each. Global
Zstd pays w operator bytes and4Bframe length. All codec-internal metadata,
termination/padding remains in payload. No search/model/certificate is needed
by the decoder. The original/global-raw alternatives are always available.

Lane choices use raw,Huffman,adaptive order0model_limit1,legacyLZeffort1,Zstd19.
This is the restricted sealed native bank, not the complete incumbent CIX BEST
portfolio. For fixed geometry all predictors refer to original reconstructed
bytes, so actual lane costs are additive: independent minimization is exact
within that bank. It does not prove separability of arbitrary learned dependency
DAGs or shared/path-dependent models. Native-vector/per-lane names include Zstd;
they are not native-only modelling results.

Concatenated-Zstd costs are nonseparable. Auto materializes literal, four uniform
vectors, and the best independent-lane vector per geometry; this is a declared
heuristic shortlist, not an exhaustive wide operator search. The strong
mask-control enumerates all2^(w-1) identity/previous-column-delta masks per
geometry (1793full width/phase vectors). Tiny oracle adds every global operator
vector,3*5^(w-1), plus the same exact per-lane family. An independent native
libZstd-driven exhaustive oracle checks serialized global costs, not entropy.
Lengths0..8 have zero observed regret. Raw wins these tiny cases, so zero regret
is weak evidence of shortlist adequacy on useful larger structures.

No entropy pruning, model lower-bound pruning, cache or symmetry pruning is
claimed. Invalid geometries are excluded exactly; lane separability is proved.
Repeated streams are recompressed and that work is measured. A full36-geometry
auto evaluates253retained entries;4956backend calls including raw materialisation
can be derived from5(5w-2)lane choices+6global trials per geometry. Retained
entry counts and logical oracle/mask-vector counts are not mislabeled unique
physical encodings. Serial dependency-limited search has no extra worker pool.

## 4. Frozen adversarial outcomes

All rows below are held-out synthetic cases from a new predeclared generator
bank. Labels/rules/offsets/violation maps are diagnostics only. Same generator
family replication is not broad real-data generalisation.

| Case | Whole | BSS | Uniform transforms | Exact ordinary mask | Auto | CIX BEST |
|---|---:|---:|---:|---:|---:|---:|
|alias-3-6|620|567|344|333|333|530|
|shift-prefix|585|611|290|282|282|407|
|partial-width5|568|631|263|246|246|369|
|subset-correlations|796|796|688|688|688|738|
|changing-correlation|672|576|468|465|463|565|
|alignment-edits|583|619|327|381|327|411|
|mixed-local|749|685|573|573|573|681|
|separated-ABA|498|449|377|449|377|449|
|cross-row-dependencies|702|299|299|299|299|382|
|absent-random|795|795|795|795|795|787|

Auto ties the stronger ordinary controls except changing-correlation463B vs465B.
Alignment edits and separated ABA select ordinary previous-row delta rather
than the independent lane-vector suggestion. Mixed-local selects phase0 despite
the structured part starting atoffset181; the cheapest global layout need not
recover the generator's boundary. Width3/6alias and partial trailing rows restore.
Random input selects raw-whole795B; its new container is larger than the781B
ordinary Zstd archive. No false geometry increases bytes relative to admitted
whole fallback; that does not eliminate external-container overhead regression.

## 5. Backend/packaging-aware transform choices

backend-aware-comparisons.json records candidate costs at identical geometry.
For alignment-edits, independent per-lane Zstd prefers[0,2,2,0] at468B, while
one global Zstd frame prefers[1,1,1,1] at327B. For ABA the corresponding
[0,2,0]/617B vs[1,1,1]/377B also differs. These are packaging/context-scope as
well as backend effects, not proof of stronger native probabilities. Cross-row
has a tied global literal solution; tie ordering is not a transform advantage.
The encoder selects by full costs, not a backend-independent entropy estimate.

## 6. Frozen existing-real-prefix transfer screen

REAL-GATE.md was written before results. Whole source identities are checked
against existing authorised inventories; unedited offset0first4096Bprefixes were
then extracted and hashed. No manual byte inspection supplies geometry. This
is not complete-file/corpus or untouched-source qualification. Canterbury text,
Calgary binary and prior Artificial controls precede any Silesia; no Silesia
was run. Strong declared complete controls include incumbent CIX BEST and
originalZstd/xz/bzip2/gzip alongside same-container BSS/uniform/exact masks.

| Prefix | Auto | Whole | BSS | Uniform | Exact mask | Smallest non-CIX control | CIX BEST | Auto-minus-best |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|numeric-prefix|1357|1655|1655|1655|1637|1377|1231|+126|
|text-prefix|1998|1998|2004|1998|1998|1934|1647|+351|
|binary-prefix|41|41|41|41|41|22|22|+19|
|compressed-prefix|4009|4009|4009|4009|4009|3990|3937|+72|

Numeric discovers width4phase0,[0,2,1,0] with a mixed per-lane backend. It beats
ordinary preprocessing and bzip2 by20B but loses126B to incumbent CIXM6.
Text loses to bzip2/CIX; uniform binary prefix gains nothing and has paid wrapper
loss; compressed prefix selects unsplit Zstd and loses to incumbent CIXM6.
No tuning after qualification, no hypothetical losses silently replaced.

## 7. Measured work, memory and decoder evidence

One observation percell; timings are local wall/CPU, never compared to imported
Squash CPU. Each timing includes discovery/rejected candidates and selected
internal inverse plus file I/O. Decoder GNU-time covers model construction and
inverse in a fresh process; sub0.01s quantisation is not zero work.

| Prefix | Auto encode wall / CPU | Auto encode RSS KiB | CIX BEST wall / CPU | CIX BEST RSS KiB |
|---|---:|---:|---:|---:|
|numeric-prefix|4.66 / 4.65 s|7672|25.47 / 25.46 s|100072|
|text-prefix|5.70 / 5.70 s|12624|40.78 / 40.76 s|118280|
|binary-prefix|0.05 / 0.04 s|6400|0.32 / 0.32 s|98656|
|compressed-prefix|6.94 / 6.93 s|34904|43.31 / 43.28 s|100132|

metrics.json/real-evidence/metrics.json retain every encode/decode measurement
and complete byte count. Synthetic169trials took52.555s wall/51.113CPU including
1344constructed native inverse checks. Real40trials took129.868s; see receipt
for CPU and sampled aggregate memory/temp. GNU-time process RSS and sampled
cgroup high-water lower bounds are distinguished. CPU8quota100%,2GiB,swap0,
64MiBwork cap; library calls are single-threaded and globally leased. Build
cost and failed compiler attempt are separate; no performance average/rank.

169synthetic selected/control archives+40real+59attribution=268new compression
trial archives;1344separate constructed raw-lane mechanism archives all restore
in fresh native processes;20malformed/CLI/semantic cases reject without output.
CRC/length/operator/route/prefix/tail/empty/one-frame/window/Huffman allocation
checks passed. libZstd FrameHeader FFI layout is bound to the current host header
and library; parsed content size must match output and window<=4096 before
allocation/decode. No unchecked indexing was introduced. Current host only.

## 8. Decomposition, streaming and promotion boundary

The completed independent adaptive segmentation DP/history experiment is reused
as evidence, not rebuilt. This follow-on tests only whole bounded geometry.
It does not implement local region plans, paid distant template references,
shared model-cache search, arbitrary lane forests, constant-offset templates
or explicit exceptional-record escape in LLT. Exact residuals handle alignment
violations; they are not those additional mechanisms. These extensions remain
gated because the global candidate has no complete-size win over the strongest
incumbent on the real prefixes. Backend-global dictionary reuse is ordinary
Zstd state, not a new shared structural model library.

Input is buffered fully up to4096B, search finishes before any archive is written,
and decode buffers reconstructed lanes. Lookahead/first output are therefore
whole-input plus search, with no arbitrary-length or non-seekable streaming
claim. Per-lane reconstruction dependencies are explicit; independent stream
blocks would incur model/framing/reset costs that are not measured here.
Production streaming interfaces remain unchanged. No production promotion.

## Exactly one evidence-selected next action

Run one frozen same-representation ablation of the discovered numeric layout
with the incumbent CIXM6 coder on a new predeclared local numeric slice, retaining
matched unsplit and ordinary preprocessing controls. This tests whether the
remaining126B gap is backend/model strength before opening local segmentation.
It is queued, not run or claimed successful at this checkpoint.

## Reproduction

Working native binary: benchmark-work/latent-layout/build/layout. Example:

```sh
benchmark-work/latent-layout/build/layout encode --policy auto input.bin candidate.llt
benchmark-work/latent-layout/build/layout decode candidate.llt restored.bin
cmp input.bin restored.bin
```

freeze.json/failed-v1-freeze.json bind exact source/library/toolchain/commands;
FORMAT.md specifiespaidwire. Recipes refuse stale/mismatched hashes. Reproduce
under a new evidence/work identity; do not overwrite immutable cells. Archives,
source datasets and binaries stay outsideGit; raw receipts/hashes/generators
are private. LLT1 is an experimental format, not a production.cix alias.
