# Lane extension v2: heterogeneous per-column residual choices

Preserve the completed v1 loss/tie evidence. New experiment/version, production
unchanged. A fixed paid mask byte independently selects identity or same-row
previous-original-column modular residual for each nonfirst lane. Each lane
also chooses among the same four reset native coders. Since all mask values
cost one byte and all choices use original source columns, route/mode costs
are separable; per-lane minima exactly solve every mask combination for a
fixed stride. Select stride1..8 by complete17+sum(9+payload) bytes. Whole/raw
remain legal. This is established factorised optimization, not new theory.

Tiny<=12 exhaustive mask combinations over cached measured route minima
validate factorization; not an independent coder implementation. Search computes
each route/mode once per stride; no unused residual trials for large forced
whole/shuffle. NCSL v2 and ZSC1 v2 mask field replace v1 all-column transform
flag; new decoders retain v1 interpretation and physically decode22v1auto+
22v1matchedZstd archives freshly without reencoding.

Reuse six focused existing mechanisms: development/held-seed stride3/noise,
previous newheldwidth4/5, previous absent, development A–B–A; plus tinyempty/one/
changing. These are exposed comparisons. Freeze three genuinely new synthetic
held controls width3/4/5, seeds1401/1403/1405, counts487/367/293, all-column
noise every23rd row, arithmeticcolumnstep5, finalcolumnzero, partialtailwidth−2.
Generator labels/rules/mappings never supplied to encoder. New cases get
zstd19/xz9e/bzip9/gzipn9/sealedCIXBEST1thread1536MiB. Same-transform nativeZstd
control pays21B plusactualoneframe, not a hidden asset or native-model claim.

Freshnative child decode/SHA, physical model/mask/route/cost trace checks,
malformedmapping/length/header/rank-free decoder checks, and v1compatibility.
Root globalWaveScheduler CPU8quota1/2GiB/swap0/64MiB, build120,generator40,
batch240/native30/CIX120. One observation/configuration. No production,
corpus acquisition/broad benchmarks, Actions, Sites, Hutter or externalcompute.
