# Wikipedia structure inventory — 30 September 2026

This inventory is read-only. It identifies reusable local mechanisms before a
new bounded structure experiment; it makes no compression claim.

## Existing reusable pieces

| component | reusable interface | constraint for this work |
| --- | --- | --- |
| `benchmarks/competitive_codec.py` | `encode_paq(data, 'v215', options)` and `decode(frame)` | Candidate selection is by completed physical frame length; PAQ remains a backend, not a CIX model claim. |
| `benchmarks/markup_columns.py` | `encode_stack(data)` / `decode_stack(blob)` | Byte-exact closing-tag stack transform: expected closes become markers; NUL is escaped; unmatched closing tags remain literal. |
| `benchmarks/markup_prose.py` | `transform` / `inverse` | Dictionary/skeleton rearrangement, useful separately but does not retain original byte order. Not selected for the first structure predictor test. |
| `benchmarks/hutter_fx2_transform.py` | full reference transform preparation | A verified full external transform-only artifact; it is not a CIX/PAQ compressed result and needs a separate native build budget. |
| `cix.multinomial` portfolio | physical frame decoders and transform portfolio | Native CIX modes select finished frames; no entropy estimate should decide a claim. |

## Prior negative constraints

- Track A showed exact conditional ranks lose to a shared-framing matched range
  control. New structure work must not imply a rank advantage without that
  control.
- Paid count feedback saved locally against its weak causal range control but
  is much larger than strong general-purpose baselines and its relative gain
  contracts on 8 MiB. It is not an incumbent replacement.
- Chunked PAQ profiles are separate compression experiments, not a parallel
  speedup for the serial PAQ model.

## Interfaces for parallel tracks

- **Track B:** use a self-contained outer frame carrying source length, CRC,
  selection byte and a complete PAQ payload; decoder calls PAQ then exact
  transform inverse. Compare raw and transformed finished frames with the same
  PAQ version/options.
- **Track C:** immutable receipts should retain source/frame/dependency SHA-256,
  timing, RSS and every component's full physical bytes. The test command must
  be run in the declared CPU/RAM/swap cgroup.
- **Track A:** retain same-information range controls whenever a transform
  changes candidate uncertainty; a changed PAQ input is a representational
  predictor experiment, not evidence that CIX rank is better.

The first bounded B hypothesis is deliberately narrow: on locally recognized
balanced markup fragments, removing only stack-predicted closing-tag identities
may give the unchanged PAQ backend an easier byte stream. The inverse emits the
original bytes exactly; unmatched or incomplete fragments remain literal.
