# Matched representation attribution

Parentc4cdad4d1;59new complete ZSC1v2 archives with fresh native SHA-256 restores.
Existing seven native/matched archives are hash-checked and reused, not rerun.
All ZSC arms use the identical libZstd1.5.5 level19 executable and21B wrapper.
Literal at the native-inferred width is exactly the fixed BSS arm, so it is one cell.

| Input | Original Zstd | Literal at native width | All residual | Selective residual | Native | Best fixed BSS |
|---|---:|---:|---:|---:|---:|---:|
|development-A-B-A|779|779|779|779|874|774|
|development-interleaved-noise|1140|1109|1065|605|685|1109|
|held-out-interleaved-noise|1148|1109|1065|605|685|1109|
|new-held-out-absent|1522|1522|1522|1522|1517|1522|
|fresh-held-mask-width3|1106|1053|1051|597|710|1053|
|fresh-held-mask-width4|1094|1172|826|484|640|1094|
|fresh-held-mask-width5|1013|1244|692|416|622|1013|

## Attribution and retained negatives

BSS alone saves53B at freshwidth3 but loses78/231B at nativewidth4/5.
All-residual recovers2/346/552B; independently selected residuals add454/342/276B
over that all-residual representation. Thus selective transformation, not byte
separation alone, explains the larger gains on these cases. These differences
are sequential matched interventions, not universally additive mechanisms.

Native-to-Zstd total changes include wrapper savings: native metadata is
17+9w bytes; ZSC is21B. At widths3/4/5, net113/156/206B consists of
90/124/165B payload difference and23/32/41B outer-metadata difference.
Coder-internal descriptions remain in their payloads. No native modelling
credit is claimed for backend or framing differences.

Absent structure: every ZSC mapping ties1522B and native1517B is5Bsmaller.
A-B-A: native geometry remainswidth1, while ordinary width2BSS achieves774B
vs779Boriginal; native874B loses. Geometry inferred for native is therefore
not necessarily best for Zstd. Plain CLI controls in the prior checkpoint
have different frame/integrity overhead and are not matched-arm substitutes.

This bank reuses exposed inputs; it is attribution, not new held-out replication.
No global mask/Zstd optimum is claimed. New frozen joint search must evaluate
representation/backend pairs; concatenated Zstd costs are not lane-separable.

## Local one-observation resources

CPU8quota1,2GiB,swap0,64MiB via WaveScheduler; scheduled ceiling180s.
See raw/cix-attribution-v1.result.json for batch wall/CPU and sampled aggregate
memory/temp; per-cell GNU time logs give encoder/decode wall/CPU/peakRSS.
The encoder is bounded whole-input4096B; no streaming latency claim.
