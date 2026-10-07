# Stage5 v1: lanes plus uniform residual operator — completed, not promoted

Frozen standalone sources: NCSL `ed55556f427658f7f3f5d751923b0e558242959a2b033b3caf01b1dd96922200`,
matched ZSC control `8bd1414a4d7ac1bc0d581417ebee93a2ca09db25c53889cc9b1374fe1b7aa44d`.
103 new physical archives across22 inputs restored exactly in fresh native
processes. Fourteen malformed checks rejected, including oversized embedded
Huffman length, Zstd extra-frame bytes, mapping/length/ID/CRC and no-argument CLI.
The source and all settings were frozen before new held-input generation.

## Paid decomposition

NCSL pays17global bytes including source length/CRC/stride/operator/lane count,
then9perlane including route/decoded length/payload length plus actual native
payloads. Whole is a legal stride1 control with exactly the previous native
whole cost; ordinary shuffle is a separate constrained search. Auto materializes
up to15 complete alternatives: whole, stride2..8 shuffle or same-row adjacent
column modular residual on every nonfirst column. Original-byte order is
recovered from stride/offset; no value-dependent assignment mask is free.

ZSC1 is an established same-transform control: paid21B header plus native
Zstd1.5.5 level19 on concatenated transformed lanes. Decoder construction,
parameters and exact one-frame/output bounds are paid/measured. It uses the
native selector's chosen mapping explicitly; no automatic Zstd mapping-search
or matched encoding-time claim is made. This is a backend control, not a new
native CIX model.

## Discriminating outcomes

| Input | Whole native | Shuffle search | Native auto | Matched transformed Zstd | Current CIX BEST |
|---|---:|---:|---:|---:|---:|
| Development interleaved/noisy |1081|1081|1081|1140|898|
| Frozen held-seed interleaved/noisy |1094|1094|1094|1148|903|
| New held stride4 + partial row |1002|1002|948|837|775|
| New held stride5 + partial row |938|938|861|**700**|716|
| New held absent opportunity |1517|1517|1517|1522|1511|

Native whole costs match the previous archived controls exactly. Native auto
beats whole by54/77B on the two genuinely new held widths, but stronger controls
beat those native results. The 700B backend-control archive beats the declared
original-input controls (smallest716B CIXBEST) by16B; this is reversible
representation + existing Zstd, not evidence of a new coder or model language.
New widths/seeds still belong to one synthetic generator family; no broad
real-data generalisation. All losses/ties are in results.json.

The stride3 fixture exposes a concrete blind spot: subtracting the previous
column helps its correlated second column but harms the already-cheap third
column. A single all-columns operator cannot retain both opportunities. This
explanation is source/structure grounded, not a completed per-column ablation.
The v1 loss is immutable; an optional paid per-column mask requires a new
version and experiment identity, not tuning/replacing this screen.

## Cost, runtime and limits

Batch wall49.097s/CPU47.810s; native per-cell GNU peak RSS<=7,176,192B.
Sampled aggregate cgroup high-water121,896,960B is a sampled lower bound;
active-work high-water9,831,112B. CPU8/quota1,2GiB,swap0,64MiB enforced by
existing global scheduler. Per-cell encode/decode wall/CPU/RSS and rejected
candidate search traces are stored. One observation/configuration, no averages.

The independent parser verifies every lane offset/count/route/length/cost and
selected candidate cost against physical bytes. Decoder checks lengths before
allocation; partial rows restore exactly. No opaque input-dependent mapping,
external asset or reconstruction search is hidden in the interpreter.

Offline full-source<=4096B lookahead remains explicit. This is not a streaming
encoder/deployment change. Shared template libraries, hierarchy and cache-state
optimisation are not implemented. No production CIX, Sites, Actions, acquisition,
external computation or Hutter work changed.

## Closest equivalence and next bounded step

Shuffle, modular residuals, heterogeneous substream entropy coding and exact
finite candidate selection are established techniques. The strongest claim is
an isolated measured implementation; no theoretical novelty is claimed.

One evidence-selected refinement: a paid one-byte per-column residual mask.
Under reset coding, independent per-column mode/route costs and a fixed-size
mask let exact local minima replace exhaustive mask combinations. Compare it
with v1/shuffle/whole and the same transformed Zstd control, with genuinely new
held seeds frozen first. Do not launch another decomposition family.
