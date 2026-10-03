# Same state space, alternative model descriptions — v2 checkpoint

## Verdict

**The proposed sharing advantage does not survive the packed-metadata control.**
Shared selector references save 1 byte on two-way examples and 3 bytes on
three-way examples versus naive flat records. Ordinary packing is respectively
1 byte smaller or ties sharing. No selected archive needs the shared form.
This is a useful negative result: do not promote ordinary deduplication into a
new structural-description theory.

The instrument does discover heterogeneous constraints automatically and
produces four complete synthetic archives smaller than the declared reference
set, with frozen held-out replication. Those wins demonstrate practical
input-derived bounded-count/parity/endpoint models in this tiny universe;
**they do not demonstrate a new model-description capability**. The controls
are zstd, xz, bzip2, gzip and frozen production CIX, not all possible compressors.

Production CIX is unchanged. These standalone Rust binaries are research
instruments, not a production format, release, streaming implementation, or
FAST/DEFAULT/BEST policy.

## Identity and reproduction

Experiment `model-description-comparison-v2`, parent revision
`8d20b5519aecf8f102462ec7ef20f1f9048aac9e`. Exact executed sources, input
recipes, native binaries and reference settings are bound by `freeze.json`,
`input-freeze.json` and `artifact-binding.json`. The initial compile-only v1
failed with E0282 on RLE vector inference; its complete packet remains in
`failed-v1/`. v2 adds the explicit vector type and is a distinct identity.

Reproduction entry point from the repository root, after reviewing the frozen
budget and existing artifact paths:

```
python3 docs/research/2026-10-03-constraint-space/model-evidence/schedule.py
```

This runs the existing global WaveScheduler lease and cgroup checks. Do not
rerun completed cells merely for averages. The two native programs are:

```
benchmark-work/model-descriptions/build/models
benchmark-work/model-descriptions/build/mdc
```

`models discover INPUT ARCHIVE` accepts no supplied model. `models decode
ARCHIVE OUTPUT` reconstructs from the archive alone. The forced `encode KIND
MODEL INPUT ARCHIVE` path isolates representation cost and is explicitly
**not** automatic discovery. Python supplies generators, orchestration and an
independent truth-set/integer oracle; there is no Python runtime codec.

## Fixed-space measurement

Nine binary-record state spaces are represented by seven distinct model
languages: combinadic subset, occupancy bitset, run list, ordered reduced BDD,
flat predicates, packed predicates and interned shared-selector predicates.
Every representation is independently checked against the exact same sorted
truth set. All use the same ordering and dense mixed-radix sequence rank.
The rank bytes are identical for a given space. Raw is an additional fallback;
Auto chooses the smallest actual complete archive, not an estimate.

| State space | Subset model B | Bitset B | RLE B | BDD B | Flat B | Packed B | Shared B |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev-six | 7 | 8 | 26 | 74 | 9 | 7 | 10 |
| dev-eight | 19 | 32 | 90 | 119 | 9 | 7 | 10 |
| dev-four | 3 | 2 | 10 | 39 | 13 | 10 | 14 |
| held-six | 7 | 8 | 26 | 74 | 9 | 7 | 10 |
| held-ten | 66 | 128 | 330 | 174 | 9 | 7 | 10 |
| upper-parity-dev | 28 | 32 | 190 | 119 | 9 | 7 | 8 |
| upper-parity-held | 106 | 128 | 746 | 174 | 9 | 7 | 8 |
| three-way-dev | 19 | 32 | 130 | 149 | 13 | 10 | 10 |
| three-way-held | 71 | 128 | 514 | 249 | 13 | 10 | 10 |

These are physical model bytes, not source size or in-memory node counts.
MSL1 adds 19 bytes common framing, including source length, alphabet, width,
model length, representation ID and CRC; plus the complete rank payload.
BDD variable order is fixed by the versioned grammar and all nodes/root/edges
are paid. No per-input dictionary, model, or reconstruction instruction is
outside the archive. Generic shared decoder software is excluded consistently
with conventional compression; no source-specific decoder assets are used.

The old specialized ERC1 wire remains an important loss control: generic Auto
uses 794/969/405/698/1116 bytes versus old ERC1
792/967/408/696/1114. Generic language overhead loses 2 bytes on four cases;
a direct bitset saves 3 bytes on dev-four. Against the learned direct dictionary,
the corresponding differences are -2/+10/-1/-2/+57 bytes saved. Do not claim
that a richer front end always produces shorter descriptions.

## Automatically discovered models and complete input controls

The discovery bank scans aligned widths 2–12, inferring count equality or an
upper bound, constant parity, endpoint XOR, and adjacent XOR relations.
Semantically redundant atoms are removed by exact truth-set equality.
All applicable representation encodings are materialized; all rejected trials
are included in observed encoding time. There is no filename, source identity,
MIME, corpus hash or prescribed model in this path. This is a finite primitive
bank, not unrestricted program synthesis or exhaustive constraint discovery.

All nine strong cases independently recover the prescribed truth set, although
some equivalent predicates differ. For instance odd parity plus count <=4 is
equivalent to odd parity plus count <=3. The old dev-four space is found using
three XOR relations instead of the supplied equality/count description.

| New frozen input | Model B | Rank B | Complete B | Smallest declared reference | Reference B | Saved B | Saved % |
|---|---:|---:|---:|---|---:|---:|---:|
| upper-parity-dev | 7 | 1152 | 1178 | CIX d3a2 BEST | 1441 | 263 | 18.25 |
| upper-parity-held | 7 | 1280 | 1306 | CIX d3a2 BEST | 1539 | 233 | 15.14 |
| three-way-dev | 10 | 960 | 989 | CIX d3a2 BEST | 1370 | 381 | 27.81 |
| three-way-held | 10 | 1120 | 1149 | CIX d3a2 BEST | 1554 | 405 | 26.06 |

The new controls all restored exactly: zstd 1.5.5 -19 -T1, xz -9e with one
thread, bzip2 1.0.8 -9, gzip -n -9, and sealed CIX revision
`d3a2cd416e49f93403d1dbd348a3e9a45db66ec6` BEST/thread1/1536MiB.
Exact executable hashes and commands are in the freeze/ledger. Prior five-case
controls are immutable reused evidence, not newly timed observations.

The two-way and three-way families share Hamming-count/parity primitives;
they are distinct combinations, **not evidence of generalisation to unrelated
real-world structures**. Held-out seeds, width, alphabet and parameters were
frozen before development execution. More distant relational/permutation/
hierarchical families remain pending.

Empty, monochrome and arbitrary-byte controls select raw at 19/4115/4115 bytes.
The monochrome fallback is a deliberate limitation of the two-symbol structural
instrument, not a good compressor policy. These controls test correctness and
inapplicability, not a claim to beat established compressors on absent cases.

## Ordinary metadata compression control

54 additional complete MDC1 archives apply zstd19 or bzip2-9 to flat, shared
and BDD model bytes, retaining the same original rank. Extraction, native
backend decode, MSL reconstruction and a fresh native semantic decoder all
restore exactly. MDC1 overhead is 31 bytes plus compressed model plus rank.
The codec ID is serialized; exact measured codec versions/settings are in the
freeze and ledger, not a per-file executable or a model asset.

None beats the selected native MSL1 archive. Best complete metadata controls for the
nine cases are 821/996/441/725/1143/1204/1332/1014/1174 bytes,
respectively. On tiny metadata, codec framing outweighs byte redundancy. This
is not a claim that metadata compression is ineffective on large models.

## Exactness and resource evidence

- 87 candidate archives, 12 automatic-discovery archives, 54 metadata archives
  and 20 new input-control archives: **173 new successful archives**, each
  reconstructed in fresh corresponding decoder processes and SHA-256 checked.
- Independent integer/truth-set oracles check local cardinality, canonical
  state membership and rank values; no truncation to fixed-width ranks.
- Nine malformed cases reject with nonzero exit and no output: truncation,
  CRC, unknown representation, invalid model length, invalid count, invalid
  mask, cyclic BDD, noncanonical bitset padding and invalid shared reference.
- Root read-back verifies all **599 physical artifact sizes/hashes**. Original
  dataset/source bytes remain outside Git.
- One-core CPU8 lease/quota; 2GiB memory limit; swap disabled; 64MiB monitored
  active-work limit. Batch wall 330.412s, cgroup CPU329.411s, GNU user325.65s +
  system3.71s; GNU maximum RSS108228KiB. Sampled cgroup high-water131076096B is
  a lower-bound measurement, not an exact peak. Active temporary peak11754345B.
  Evidence logs outside the monitored active-work directory are disclosed.

Discovery end-to-end wall times on new inputs are 1.0680/0.03174/1.0667/0.03171s;
fresh decoding 0.00369/0.00372/0.00379/0.00367s, respectively. Selected model
compile/cardinality/rank kernels are far cheaper than expensive rejected
portfolio candidates. Do not substitute those kernel timings for search cost.
One observation per cell; no statistical speed superiority is claimed. CPU/RSS
for every child and phase timings are preserved in `raw/`; `summary.csv` gives
complete sizes and selected discovery timing.

COUNT/RANK/UNRANK are practical only within this instrument's declared bounds:
2–12 bits per local record, at most4096 local assignments, source <=16384B,
model <=21000B, archive <=40000B and at most32 atoms. Enumeration compiles each
model to the canonical local table, then exact arbitrary-precision M^r ranks.
This proves bounded exactness, **not polynomial general CSP intersection**.

## Formal cost result and novelty boundary

For N atoms using S distinct masks, the implemented serializations cost:

```
flat         = 1 + 4N
packed-flat  = 1 + 3N
shared       = 2 + 2S + 2N
```

Thus shared beats flat iff N>S+1/2, but beats packed iff N>2S+1.
Proof is subtraction of fully paid field lengths; it says nothing about an
unimplemented optimal language. Two atoms on one scope save1B over flat but
lose1B to packed. Three on one scope save3B over flat but tie packed. References
can pay only after sufficiently many uses. This elementary wire-cost bound
falsifies the tempting naive interpretation of the experiment.

A same-space decision-diagram/count model followed by canonical dense rank
cannot get a fundamental rank advantage over another description of that set.
It can win by model bytes, decoding resources, or discovery cost. Hash-consing,
shared DAGs, grammar descriptions, knowledge compilation, MDL and compiled
indexing remain established prior art. Our measured results are Level0 packing
and Level1 automatic deduplication; no Level2–5 novelty is established.

The current failures also rule out claiming that shared SDL automatically
beats BDDs, factor graphs or grammars as a class. The serialized BDD used here
is one fixed-order five-byte-node control. Unmeasured optimized BDD encodings,
SDD/d-DNNF/ZDD and recursive grammar descriptions may do better.

## Next decision

Retain the instrument and negative results. Do not integrate its methods into
production. Continue only with the predeclared queue in `QUEUE.md`: stronger
same-space established encodings and structurally unrelated sharing cases
before any broad language expansion. The promising question remains cheaper
model description; this checkpoint does not answer it affirmatively beyond
ordinary metadata packing/deduplication.
