# Addendum delta: noisy models, paid controls and exact bounded decoding

## 1. What changed

The addendum was applied at the completed same-space model checkpoint,
privately pushed as `d38e81b9df833cf45bcd102835074c4dff23e14c`. No useful job was
interrupted. Prior12/59B model-description wins remain valid; RNC1's256B model
allowance remains a diagnostic, not a practical size claim. Identical ordered
spaces still have identical uniform rank payloads. Complete-size gain, model
saving and corrected rank surplus are separate quantities.

New isolated Rust REX1 retains a discovered model despite violations, paying
for exception positions and original exceptional information. RHC1 supplies
same-dictionary uniform and paid-histogram controls, plus a separate automatic
histogram portfolio. No production CIX changes, acquisition, corpus benchmark,
Hutter, Actions or public Site update occurred. One observation per cell.

Completed earlier fixed-space comparisons are in
[model-evidence/REPORT.md](../model-evidence/REPORT.md): shared selectors save
1–3B against naive flat syntax, but packed syntax beats/ties them. Legitimate
metadata savings do not constitute new entropy theory; this negative stronger
control does not invalidate the original specialized model-cost savings.

## 2. Closest prior-art equivalences

[Specific method-level review](../addendum-prior-art.md) records reading limits
and the requested comparators. No cited system is counted as implemented.

| Surviving idea | Closest established explanation / boundary |
|---|---|
| Exact exception-position and sequence ranks | Cover enumerative/two-part coding; combinadic subset and finite-set rank, not new theory. |
| Paid record-use histogram | Type-class/multinomial coding; a narrower whole-sequence set, not the same M^r experiment. |
| Probabilities on constrained support | PSDDs / probabilistic circuits; parameters/model transmission must be paid. No PC implementation or neural training here. |
| Automatically reused syntax/templates | CSE, grammars, Stitch library learning; serialized definitions/references differ from AST/token objectives. |
| Shift-aware reuse | VS-SDD's specified variable substitutions; arbitrary permutations are not covered by that guarantee. Not executed here. |
| Parameterised constraint transfer | GenCon; acquired proposals do not by themselves define a physical exact rank codec. |
| Compilation/count/index tradeoff | Knowledge compilation and Cover; query tractability does not imply cheap compilation. |
| Large circuit resource efficiency | Monarch PC architecture; throughput experiments do not establish paid model-description gains. |
| Exactly indexable relaxed superset | Standard model-cost versus rank-expansion tradeoff; no approximate counts inserted into ranks. |

URPILS has an MDL discovery objective with heuristic difficult-count/error
estimates, not a verified archive/rank decoder. PSDD/PC descriptions and
parameters are not free decoder knowledge. The related patent document
US12456231B2 has a separate claim-text review; it supports no inference of
infringement, clearance or compression novelty. No production legal conclusion
is made by this experiment.

## 3. Noise mechanism and physical break-even

REX1 discovers from bytes alone: aligned widths2..12, top observed equality
masks, majority/individual equalities and modal/upper-bound counts, capped40
models per width. It receives no generator rule, width, map, corruption rate or
source identity. All considered models are scored by their exact physical
length before expensive member-rank construction. The strict smallest complete
candidate wins, including raw. The decoder rebuilds its local table from the
paid predicate, never repeats discovery.

For r records, b binary symbols per record, e exceptions and M compliant words:

```
w(N) = bit_length(N-1), for N>=1
L_REX = 35
      + ceil(w(choose(r,e))/8)
      + ceil(w(M^(r-e))/8)
      + ceil(b*e/8)
```

35B is header+CRC, split into5B model and30B other fields, **not35+5**.
The three rank/literal fields are separately byte aligned. The sorted source
alphabet maps each source byte to one bit; an exceptional b-byte record takes
b bits here, not8b. Combinadic positions, dense compliant rank and packed exact
exception words are independently checked. Exceptions must be outside the
stored model; original alphabet, length, r/e, mask/count and field lengths are
paid. Local enumeration is at most4096words, source <=16384B, archive <=30000B.

The existing weak-six input/archive receipts were rehashed before reuse:
RDIC1049B, exact-only Auto12312B. REX discovers b6,M8,r2048,e121:

```
30 framing + 5 model + 83 positions + 723 compliant rank + 91 exceptions = 932B
```

Its117B advantage over RDIC is retained structural information after paying
exceptions. It is not raw fallback. However paid histogram925B beats REX by7B.

For this fixed r2048,b6,M8 model, solving the actual byte formula against a
**1049B byte budget** gives e<=269 for a strict win: e269→1048B and e270→1049B.
Two native physical forced-model archives confirm these lengths and fresh
restoration. This is an accounting boundary, **not a claim that the1049B RDIC
result remains constant on other inputs**. The separate controls on each input
are the proper matched compression comparisons.

Empty is an explicit35B raw frame. Native forced-model boundary fixtures prove
e0, e=r, first-position and last-position escapes. At e=r both ranks cost0bits
and all original mapped exception words remain paid. A raw alternative normally
omits the unused model. Empty local models are inapplicable, not 0^0 codes.
There are no cross-record adaptive contexts in this instrument; no claim is
made about context-dependent exception reconstruction.

## 4. Measured grid and controls

| Input | e | Exact-only B | REX B | RDIC B | Uniform dictionary B | Paid histogram B | Best declared control B | REX gain B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original dev-six | 0 | 792 | 803 | 792 | 803 | 815 | 792 | -11 |
| Original weak-six | 121 | 12312 | 932 | 1049 | 1075 | 925 | 925 | -7 |
| Absent structure | — | 12312 | 12323 | 12307 | — | — | 12302 | -21 |
| Dev b6 clean | 0 | 600 | 611 | 600 | 611 | 623 | 600 | -11 |
| Dev b6 single | 1 | 1080 | 614 | 633 | 646 | 628 | 628 | +14 |
| Dev b6 sparse | 16 | 9240 | 633 | 697 | 800 | 664 | 664 | +31 |
| Held b8 clean | 0 | 967 | 978 | 979 | 1022 | 1064 | 967 | -11 |
| Held b8 single | 1 | 12312 | 980 | 988 | 1033 | 1069 | 988 | +8 |
| Held b8 sparse | 16 | 12312 | 1000 | 1082 | 1147 | 1127 | 1082 | +82 |

Best declared control includes exact-only, RDIC, matched/automatic RHC1,
zstd1.5.5 -19 -T1, xz5.4.5 -9e -T1, bzip2 1.0.8 -9, gzip1.12 -n -9, and
sealed Rust CIX d3a2 BEST/thread1/1536MiB. The ordinary zstd LZ+entropy route
is a generic dictionary/residual explanation; no new dedicated optimized
structural dictionary/escape competitor is implemented. That missing closer
control limits any algorithmic innovation claim.

Held-out seeds, width, parameters and alphabet were frozen before execution;
discovery receives none. All six selected generator-width/escape-count gates
pass, so the observed savings retain the intended model rather than a fallback.
These are variants of one binary-record generator family, not unrelated real
corpora. All losses and ties remain in results. The clean11B penalty is the
extra REX framing; a mature selector would retain the old exact wire, but no
production integration is authorized.

## 5. Ordinary usage modelling explains additional gains

Forced histogram and uniform controls share width, sorted observed dictionary
and alphabet. **They do not share the REX compliant support**: the observed
dictionary includes exception words. Thus REX versus RHC changes both model
and support, while H versus U isolates paid usage modelling.

On weak-six, both RHC variants use16 observed b6 words. Uniform costs1075B.
Histogram costs925B:19framing+32dictionary+32histogram+842payload. The uniform
payload is1024B: ordinary usage modelling saves182payload bytes and spends32
histogram bytes, net150B. This is a known frequency benefit, not structural
language innovation. On clean uniform-use controls the histogram loses12B
(b6) or42B (b8) versus its matched uniform dictionary. Description costs are
not silently waived.

Histogram cardinality is r!/product n_j!, ranked lexicographically with exact
BigUint ratios. The distribution over sequences is uniform conditional on
those paid counts; it is not a paid i.i.d./adaptive probability-model control.
That separate stronger control remains unimplemented. No weights/pretrained
assets are hidden. Independent counts, cardinalities and rank integers agree.

Automatic RHC selection is separately measured once per input. It chooses the
same b/support for all eight binary cases, so it does not erase the four noisy
wins. On the absent case it chooses raw12307B. Do not confuse this portfolio
comparison with the forced same-support usage ablation.

## 6. Relaxed decoding and valid pruning

The candidate bank includes zero equality mask/no count: exactly indexable
binary superset T with2^n members. This is lossless, but no new physical
superset-versus-exact compilation comparison is justified here: all current
local models compile cheaply within4096words. A broader relaxation branch is
therefore gated, not opened. Estimated counts are never used for intervals.

For fixed model/r/e and this grammar, final_cost is an exact output length.
Pruning if it is >= the incumbent is sound; padding/CRC/all fields are included.
It does **not** prune a future intersection branch from the current surviving
set, assume singleton profitability or promise that new factors cannot help.
This elementary size identity is established accounting, not a new theorem.

## 7. Exactness, budgets and amendments

Main batch:67 new complete archives,21 reused receipt records,8 malformed
rejections. Seven additional forced-model boundary archives and nine automatic
histogram controls bring this checkpoint to **83 new archives**, each restored
in a fresh corresponding decoder process. SHA checks apply to all. Independent
small truth-set/integer oracles apply to25 main native frames,7 boundary frames
and9 automatic histogram frames; general codec internals are not independently
rank-checked. Final read-back verifies190 retained work-tree artifact sizes/hashes.

Malformed controls reject without output: truncation, CRC, e>r, impossible map
rank, impossible payload rank, exception length, mask and zero histogram count.
This is targeted qualification, not fuzzing/exhaustive hostile-input coverage.

Same global WaveScheduler CPU8 lease/quota1,2GiB, swap0,64MiB active-work cap.
Main batch wall242.663s/cgroup CPU242.198s, GNU user237.55s+system4.60s;
GNU maximum RSS108136KiB, sampled cgroup high-water123297792B (lower-bound
polling measurement, not exact peak), temporary peak10297108B. Supplements and
automatic controls have separate receipts; peak active work across them
17755644B. Evidence logs outside that footprint are disclosed. Child CPU/RSS receipts
and commands are retained in raw/; content hashes are retained in freezes,
results and bindings. One observation; no statistical speed
rankings or imported Squash-time comparisons.

REX encode wall on the noisy dev/held rows is ~15.6–15.7ms including all
inference/rejected candidates and process cost; weak-six31.7ms. Fresh decode
~1.45–3.66ms on the new grid, weak7.65ms. Individual COUNT/RANK/UNRANK phase
timings are not separately instrumented here; do not infer them from full
process timing. Recompiled table memory/time are decoder work, not archive
bytes. This is a bounded independent-record prototype, not arbitrary-length
streaming or a deployed resource policy.

Amendments to preserved preflight PLAN: freeze.json c5924baf is authoritative,
not its stale692e source note; r1536/new b6/b8 fit the input cap, whereas generic
b12 would not; RHC pairs share observed dictionary, not REX support. Physical
input hashes were recorded by the scheduled generator before coding; the
pre-dispatch freeze binds the exact generator/settings, not precomputed new
input hashes. These distinctions are preserved rather than rewritten away.

Native boundary build/test passed. First supplemental verifier looked for
relative output under the wrong directory and failed; raw failure and original
verifier remain preserved. Verification-only v2 fixes the path and passes;
no successful build/test/encoder was rerun. No average is manufactured.

## 8. Strongest claim and one next experiment

**Established techniques, implemented and qualified in a new isolated native
instrument.** Four complete noisy-input wins survive the declared control set
and frozen within-family replication. The weak-six collapse is repaired, but
a known histogram model wins that row. There is no new algorithm/theory claim,
no broad real-data generalisation and no production promotion.

**One next experiment:** discover and pay for an arithmetic-progression/gap
model of exception positions, comparing it with combinadic positions and
conventionally compressed gap bytes. Weak-six pays83B for positions that happen
to be periodic; the sparse grid pays16B. Discovery must use observed exception
positions alone, serialize every start/step/edit, retain an irregular-position
negative control and freeze before held-out replication. This is ordinary
structural metadata coding unless a specific stronger algorithmic result
survives the controls. Grammar/shift-aware full model synthesis and paid
probability controls remain coverage gaps, not deployed capabilities.
