# Position-determined history: completed controlled stage4

Isolated source `e10fde8f9bdbbe4b004b93a6e654ee63c2ee8569436dfeaeb75ef63abbea5809`
was frozen with compiler, sealed native library and paid wire description.
116 complete archives restored in fresh native processes; eight malformed
archives rejected. Sixteen altered-H compatibility probes found thirteen
payloads genuinely dependent on history and three valid H0-compatible payloads;
the latter also restored exactly and are not mislabelled corrupt inputs.

## Mechanism and guarantee

NSCHv1 pays 19 global bytes, including H:u16, versus17 in the independent
control; each segment still pays9+actualpayload. Only legacy LZ receives the
last1024 exact decoded bytes. Raw, Huffman and order0 adaptive are reset.
The decoder derives history from original restored bytes, including raw
regions. It does not transfer incompatible coder state or rerun discovery.

The proof in ../history-proof.md establishes that this particular history
is a function of byte position, so endpoint/segment-count DP remains exact
within its admitted edges. This is an established optimal-substructure result,
not a guarantee for persistent adaptive models, recent-block or template caches.

## Results: history survives, but is not automatically profitable

Every H1024adaptive archive ties H0adaptive; both are2B larger than the previous
independent archive. Existing adaptive winners are Huffman/raw segments or
unsplit whole LZ; retained history has no winning contribution there.

| Matched frozen case | Independent fixed256 | H1024 fixed256 | Independent fixed1024 | H1024 fixed1024 | H1024 whole |
|---|---:|---:|---:|---:|---:|
| Development homogeneous |239|226|91|90|56|
| Development A–B–A |931|925|875|877|876|
| Development long dependency |1617|1167|1572|1091|1092|
| Held-seed homogeneous |260|247|91|90|56|
| Held-seed A–B–A |921|914|866|868|864|
| Held-seed long dependency |1630|1208|1585|1105|1106|

These are complete archive costs including the new2B fee. History prevents
large fixed-block reset losses on the crossing dependency, but its best fixed
result is still1B larger than the old independent whole archive. The adaptive
boundary bank omits the available1024 split, causing a measured1B miss against
that already-materialized same-H fixed candidate. This is a candidate-generation
omission, not a DP scoring error; no speculative estimator was used.

The low-alphabet A–B–A fixture does not gain with history-aware adaptive routing.
The frozen effort1 LZ parser's chain cap8 and minimum-match hash can obscure
long old matches amid repeated binary contexts; Huffman remains smaller among
actually materialized routes. This is a plausible code-grounded limitation,
not an ablation proving its causal contribution. Parser settings were not
changed because that would confound the fixed-portfolio comparison.

All losses/ties and per-cell native decode times/RSS are in results/metrics/raw.
Prior controls and exact inputs were rehashed. These inputs were already
exposed in stage3; they are controlled mechanism replication, not a new
untouched held-out programme or real-data generalisation.

## Resource and decoder evidence

Batch wall19.082s, CPU17.922s. Native per-cell GNU peak RSS<=8MiB;
sampled aggregate cgroup high-water36,601,856B is a sampled lower bound.
Active-work high-water5,332,325B. Root global scheduler enforced CPU8quota1,
2GiB/no swap/64MiB. Each configuration has one observation. Search/rejected
trials/internal validation are encoder work; fresh decoder/model construction
are separately measured. No encoder parallelism claim; one leased CPU.

Malformed limits, route IDs, CRC, lengths and truncation/trailing reject before
writing restored output. Source/trace IDs, positions and segment sizes are
crosschecked. Small references independently check partition selection over
the shared measured route-minimum edge matrix. Independent route-codec and
exact1024/1025-distance fixtures remain proposed hardening, not completed claims.

Full-source <=4096B lookahead and bounded archive reading remain offline.
This prototype does not establish an arbitrarily long streaming encoder or
incremental production decoder. Shared structural template libraries/cache-state
search remain unimplemented here; decoded-prefix LZ history is not that feature.

## Evidence-selected next stage

Interleaved noisy fields still need a cheaper explanation. Test one bounded
lane decomposition with paid mapping and adjacent-column modular residuals,
against ordinary deinterleave on the same native route set. No hierarchy/cache
branch is launched, and production remains unchanged.
