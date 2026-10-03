# State-space synergy under equal paid model cost

## Result and correction

The prior interpretation needed two separate reference points. ERC E/C/EC
already paid the same24-byte model/framing cost, so their archive differences
were rank-payload differences. Only EC versus the direct dictionary was a
metadata-only gain. A dictionary for the same joint set is not a single
component model: it already contains the interaction.

This new native diagnostic physically equalises the model cost for ERC and
RDIC, adds a paid uniform two-symbol control, and verifies45complete frames
through fresh archive-only native decoding. Five malformed outer frames
reject without output. It uses unchanged frozen inputs, models and original
baselines; no broad codec benchmark was rerun.

## Exact rank widths: all model costs held equal

Every diagnostic frame pays270bytes:10outerheader +256modelarea +4CRC.
Rank payloads are separately byte-aligned; all parameters and dictionary ranks
are inside the paid model area. Padding is explicit artificial diagnostic
overhead, not a suggested compression format or a gain against original sizes.

| Frozen input | RU bits | RE bits | RC bits | REC bits | Best-component rank gain | Rounded bit surplus | Same-space dictionary rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev-six | 12288 | 10240 | 8852 | 6144 | 2708 | 660 | 6144 |
| dev-eight | 12288 | 10752 | 9415 | 7537 | 1878 | 342 | 7537 |
| dev-four | 12288 | 6144 | 7942 | 3072 | 3072 | -1274 | 3072 |
| held-six | 10752 | 8960 | 7745 | 5376 | 2369 | 577 | 5376 |
| held-ten | 12800 | 11520 | 10211 | 8714 | 1497 | 217 | 8714 |

Define `marginal=min(RE,RC)-REC`. This is ordinary set shrinkage. Define
`surplus=RE+RC-RU-REC`; this subtracts the additive reductions from the same
paid uniform universe. These integer values include each rank-width ceiling.
They are not claims about mutual information/PID or a Shannon limit.

## Complete physical constant-fee archives

| Frozen input | Uniform | Equality | Counts | Intersection | Direct dictionary | vs best component | vs dictionary |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev-six | 1806 | 1550 | 1377 | 1038 | 1038 | 339 | 0 |
| dev-eight | 1806 | 1614 | 1447 | 1213 | 1213 | 234 | 0 |
| dev-four | 1806 | 1038 | 1263 | 654 | 654 | 384 | 0 |
| held-six | 1614 | 1390 | 1239 | 942 | 942 | 297 | 0 |
| held-ten | 1870 | 1710 | 1547 | 1360 | 1360 | 187 | 0 |

The development and held-out emergence cases retain234B/187B advantage over
the best component under constant fees. Beyond additive rank reduction, they
have42B/27B of byte-rounded surplus. Their direct dictionary comparisons
both become exact ties. The four-position case has **negative** surplus even
though its joint rank is smaller than either component: marginal shrinkage
alone does not prove beyond-additive synergy.

E at width2 on the four-position input is checked explicitly at the common
width4: its repeated equality rule yields mask5. The harness enumerates
local E and C sets and proves their intersection is the stored EC table. It
also proves the global count-derived widths agree. No mismatched-width
cardinality product is assumed.

## Why a positive state-space surplus exists: elementary proof

For even b≥4, fix E to first-pair equality and C to exactly b/2 ones. Then

    U = 2^b
    NE = 2^(b-1)
    NC = binomial(b,b/2)
    NEC = 2 binomial(b-2,b/2).

The two EC terms correspond to equal-zero and equal-one first pairs. Their
binomial counts coincide by complement symmetry. Therefore

    sigma = log2(NE NC / (U NEC))
          = log2((b-1)/(b-2)) > 0.

For r independent records, the ideal surplus is r sigma. Exact archive
comparison uses arbitrary-precision counts and rank-width/byte rounding.
This is a proved binomial/hypergeometric identity, **not a novel theorem**.
For the actual selected width-four model, discovery adds a second implied
equality, so the fixed-mask formula does not describe its Auto-E ablation.
The harness records its actual cardinalities and negative surplus instead.
See [the mathematical distinction](../state-space-distinction.md).

## Strong-control boundary: the harsher test does not win

When two models denote the identical ordered space of N outcomes, both use
uniform dense ranks of width bit_length(N-1), and they pay identical total
model/framing costs, their complete fixed-rank lengths are equal. This follows
immediately from the coding construction; no experiment can produce a strict
advantage without changing at least one premise.

The experiment independently verifies EC/RDIC source length, alphabet, record
width, exact vocabulary and byte-identical sequence ranks. This is why the
previous12B/59B wins vanish after model-cost normalisation. A probabilistic
completion-count coder can represent the same joint set at the same ideal
rank cost. Different nonuniform probability models or additional constraints
could change the space/cost; this statement does not rule those out.

Consequently:

* **State-space synergy versus the individual models is demonstrated**, including
  held-out replication and positive beyond-additive surplus.
* **A rank-only win versus the strongest measured same-space structural control
  is not demonstrated**: every equal-fee comparison ties.
* Neither finding establishes a new theory. This remains known enumerative/
  constrained coding with a useful accounting distinction.

## Resources and qualification

`freeze.json` binds source, runners, original evidence, native decoder binaries
and exact build dependencies before execution. The zero-mask uniform control is
encoded natively with paid sorted alphabet and nbit BigUint rank. Python
independently verifies that rank and local E/C/EC sets; it is not a codec.

For the39 wrapped pre-existing frames, native unpack reconstructs a
byte-identical original archive (including its regenerated CRC). The6native
Uniform frames create new ERC inner archives, checked by an independent rank
oracle. A fresh native decoder restores the input in all45cases.
The adapter only validates framing-critical native fields, so native decoding
is mandatory for the complete semantics. Original archive/source hashes and
all new artifacts are retained in `artifact-binding.json`.

One existing WaveScheduler CPU8 lease; one-core quota,2GiB ceiling, swap0,
64MiB active temporary cap. Build/batch each120s, perchild10s; one observation
per cell. Aggregate phases deliberately have no fabricated processed-byte
denominator. Active build/frame/inner/restoration artifacts are in the bounded work
directory. Small raw logs, receipts and result documents are stored separately
in the evidence directory, outside that temporary-footprint monitor.

GNU batch wall0.36s, CPU0.20s user +0.04s system; aggregate maximum
RSS23,044KiB. These include45pack/unpack/decode pipelines, uniform probes
and five negative tests. Tiny per-command times often fall below0.01s;
no speed/throughput improvement claim is made. Raw logs/receipts include
the sampled cgroup memory and work-directory footprint; these are not precise
allocation/peak-RSS substitutes.

## Research consequence

The next substantive target requires additional input-derived relationships
that shrink a control's admissible space, or a better discovery/compilation
algorithm with a precise prior-art distinction. Encoding an existing joint
vocabulary more cheaply is not evidence of a new rank-space capability.
Model-count approximation is unnecessary for this bounded family; arbitrary
tractable heterogeneous closure and useful real-data discovery remain open.

No production selector, streaming format, ordinary optimisation, Sites page,
dataset acquisition or GitHub Actions was changed. Original unnormalised sizes
remain the only results usable for compressor rankings.
