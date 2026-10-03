# Paid heterogeneous lane mask: completed evidence-driven refinement

## Frozen version and exact reconstruction

NCSL v2 source `9096d8f18e9bf8817f69730771d9a930de229b7341defc15395b5db5e5abc996`.
ZSC v2 control had a compile-only type-inference failure before input generation;
its old source/freeze/schedule/stderr are preserved. The sole fix typed the
inverse offset as usize; a new build identity reused the successful unchanged
native-mask binary. No archive cell was repeated or held-out input tuned.
See freeze.json for final exact source/compiler/backend hashes and commands.

63 new complete archives restored in fresh native processes. Forty-four old
v1 native/Zstd archives also restored through v2 decoders without reencoding.
Seventeen malformed/CLI cases rejected, including invalid high mask bits in
both formats and malformed v1 stride before any conversion shift. Three tiny
auto cases have zero gap to exhaustive mask costs over the measured route
minima. This is not an independent implementation of the entropy coders.

## Specific change and formal property

V1 residualized every nonfirst column. V2 pays the same one-byte field but
uses it as a mask: each column can independently remain literal or subtract
its previous **original** column modulo256. Decoder reconstruction proceeds
in column order, restoring that previous original before a dependent column.
No generator rule, alignment, constants or corruption map is passed to encoder.
The shared stride/offset rule and mask are paid once; each local coder/model
is paid in its actual lane payload. It is a shared positional operator, not a
learned template library or cache across different regions.

For fixed stride s, let `p[k,m,r]` be the actual payload bytes of mode m and
native route r, with m=0 only for column0. The complete cost is

    17 + sum_k (9 + p[k,m_k,r_k]).

Every legal mask occupies one byte; route choices/reset models are independent.
Therefore minimizing each lane term exactly minimizes the whole cost for
that stride. Exhaustively enumerating 2^(s−1) masks cannot do better. Selecting
the best stride1..8 then solves the declared finite family. This is a proven
separable optimization property, established mathematical machinery—not a
new lossless-compression theorem. Ordinary shuffle and unsplit/raw remain
explicit controls; identity wins exact local ties. Ranking a fixed admissible
set is not being changed or claimed to beat its entropy bound.

## Complete-byte results

| Input | Native whole/shuffle | Native mask auto | Current CIX BEST | Matched same-mask Zstd |
|---|---:|---:|---:|---:|
| Exposed development stride3/noise |1081|685|898|605|
| Exposed prior held stride3/noise |1094|685|903|605|
| Exposed v1 held stride4/partial |1002|661|775|500|
| Exposed v1 held stride5/partial |938|638|716|435|
| **Fresh held width3/partial** |1064|**710**|911|**597**|
| **Fresh held width4/partial** |986|**640**|772|**484**|
| **Fresh held width5/partial** |908|**622**|691|**416**|
| Absent opportunity |1517|1517|1511|1522|

The three fresh held inputs were generated only after frozen source/policy
settings. Their seed, width, period, lengths and hashes are stored; they still
belong to one synthetic family, not broad real-data replication. Native gains
versus CIXBEST are201/132/69B, but matched transformed Zstd remains113/156/206B
smaller than native. Matched-control gains versus smallest original-input
controls are314/288/275B. These last results are paid reversible representation
plus an established backend; they are not a native-coder or new-theory victory.
The native selector supplies its paid mask to this fixed-setting control;
Zstd mapping discovery/time was not independently optimized or fairly ranked.

A separately frozen baseline-fill supplement freshly encoded12 contiguous
controls on the exact same fresh inputs, without rerunning mask cells:

| Fresh width | Contiguous adaptive | Fixed64 | Fixed256 | Fixed1024 | Native mask |
|---|---:|---:|---:|---:|---:|
|3|1064|1620|1329|1171|710|
|4|986|1693|1429|1145|640|
|5|908|1692|1483|1094|622|

The absent case and A–B–A negative select unsplit; all ties/losses are retained.
V1 archives remain unchanged. Per-column choice is what enables keeping a
cheap third column while residualizing a correlated second one; shuffle alone
did not deliver these gains.

## Representative actual decomposition: fresh width3

| Input offset | Stride | Items | Operator | Coder | Metadata | Payload | Complete lane |
|---:|---:|---:|---|---|---:|---:|---:|
|0|3|488|identity|raw|9|488|497|
|1|3|487|previous-column modular residual|order0 adaptive|9|89|98|
|2|3|487|identity|order0 adaptive|9|89|98|

Global17 + 497 + 98 + 98 = **710B**. Mask=2; partial final row contains only
column0. The zero-like third lane is preserved instead of being residualized.
These choices were discovered from actual complete encoding costs, not labels.

## Work, storage and decoder bounds

Batch wall45.341s/CPU44.648s; native per-cell GNU peak RSS<=7,172,096B.
Sampled cgroup high-water119,128,064B is a lower bound, not a true peak;
active-work high-water9,785,448B. CPU8quota1/2GiB/swap0/64MiB enforced by the
existing scheduler. Discovery and rejected native trials are in encoder work;
fresh decode/model construction separately recorded. One observation/cell,
no averages or imported CPU-time rankings. Metrics explicitly exclude reused
v1 references even when archive basenames coincide with new files.

Source<=4096B; decoding checks version/mask/lengths before entropy calls,
retains v1 interpretation, rejects impossible mappings/overflow/trailing bytes,
and writes output only after exact length/CRC validation. Original byte order
and arbitrary partial rows are exact. Native route IDs/model payloads and all
counts/parameters/checksums are included once. Native Zstd uses bounded buffers,
one-pass exact-frame validation and no decoder-side compression/search.

Full-source offline lookahead remains explicit. No arbitrarily long streaming
encoder or incremental decoder result is inferred. No new platform claim,
production integration, broad corpus run, new downloads, Sites, Actions,
external computation or Hutter job occurred.

## Verdict / remaining gap / one next experiment

Established shuffle/residual coding plus measured automatic heterogeneous
selection is useful on this bounded imperfect family. It is not a new SDL,
new entropy bound, or proof of efficient arbitrary constraint compilation.
The six-part prospective new-method success gate is not met by native alone:
a strong same-representation established backend still beats it. Exact
same-state-space model-description comparisons remain the earlier separate
instrument; this experiment does not replace them.

One next bounded experiment: compare a shared-support description against
packed/compressed independent support metadata on **the same discovered lane
supports**, keeping payload order and code fixed. This targets model-description
savings rather than repeating rank or backend improvements. A template-cache
optimizer, hierarchy and broad real-data deployment remain unqualified/queued;
none is silently claimed completed or integrated.
