# Conventional lag-2 lead: existing native capability check

The isolated theory screen found no promotable new-theory result. Its only
positive control is a 1 MiB sample encoded with lag-2 byte subtraction and
static order-0 rANS. **CIX already implements the same byte transform.** No new
transform, codec route, benchmark or production change follows from this note.

## Exact observation and corrected attribution

- Source: canonical x-ray bytes `[262144, 1310720)`, 1,048,576 bytes.
- Sample SHA-256: `43cf1b6c3b0fa20b14d293321d591815892b1ba50f9fae9fbb42a02a6ba63fd8`.
- Hard-selection research archive: 596,846 bytes, including model/framing costs.
- Matched raw + Zstd level 9 research archive: 649,304 bytes.
- Difference: 52,458 bytes, 8.0791124% of the matched Zstd archive.
- Bits-back research archive: 597,963 bytes, 1,117 bytes worse than hard selection.
- All 256 blocks selected the same lag-2 transform. Thus the observation does
  not demonstrate a benefit from switching models or combining predictions.

The full file, current CIX and a fixed-single-model physical ablation were not
compared for this positive sample result. The corpus has prior exposure. This
is neither a CIX improvement nor a record nor a pristine held-out qualification.
The separate report and all 55 physical research archives remain in
`/home/user/src/cix-theory-screen-2026-10-04`; its source/plan/result hashes are
bound in `conventional-lead.json` here. The main release benchmark stays stopped.

## Actual source mapping

| Mechanism | Existing native code | Consequence |
| --- | --- | --- |
| Lag-2 byte subtraction modulo 256, first two bytes literal | `transform.rs`, transform ID 25, `ByteDelta(2)`, name `byte-sub-2`; `apply_byte_delta` | Matches research mode 3 for the same input block. A new transform would duplicate existing semantics. |
| Eligibility and selection | ID 25 is in `TRANSFORM_IDS`; `transform::encode` profiles eligible transforms, then encodes only the effort-limited beam | Presence does not prove this candidate was selected on the sample. |
| Ordinary encoder admission | `cli.rs::m6_try_legacy_candidates`, mode 5: input >=4 bytes, effort >=2, available reservation >=64 times input bytes | Admission also depends on the outer route/policy and available resources. No claim that every FAST/DEFAULT/BEST invocation runs it. |
| Entropy coding after transform | `rank::encode_type_class`: paid block counts; exact rank or remaining-count range coding | Different from the research codec's shared development-trained static order-0 rANS tables. Backend/model reuse costs remain confounded. |
| Transform-chain compatibility | `chain.rs` recognizes ID 25 and reverses byte-lag subtraction | Decoder coverage alone does not prove encoder shortlist admission. |

The word transforms labelled `delta2` elsewhere are second differences of
multi-byte words. Those names are not evidence of this byte-lag mechanism;
ID 25 and its actual arithmetic establish the match.

The research codec resets the transform every 4,096 bytes and shares frozen
frequency tables learned on its development prefix. CIX's selected block
boundaries, model state and complete framing costs must be aligned before an
operational comparison can isolate any remaining information or cost advantage.
No claim is made that range coding versus rANS alone explains the difference.

## Disposition and one next action

Retain this as an **existing-method marginal-value check**, not a new-theory
opportunity. At a later authorized comparison gate, compare the admitted native
ID-25 path and the fixed lag-2 control using identical sample bytes, block resets,
complete model/framing charges and exact independent decoding. Until then,
implement no duplicate transform and infer no achievable CIX saving from the
Zstd-only comparison. This note does not authorize that comparison or change
any closed research branch or release-readiness requirement.
