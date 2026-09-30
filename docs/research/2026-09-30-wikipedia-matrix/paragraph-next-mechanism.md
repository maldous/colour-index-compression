# Paragraph-unit follow-up: conditional decimal holes

This note is a read-only next-mechanism recommendation. It is not a claim that
the paragraph representation compresses better, and it authorizes no corpus
run.

## Current evidence

The three fixed 4 MiB development profiles in
[`unit-eligibility.json`](unit-eligibility.json) show a trade-off between the
alternative segmentations:

| Shared eligibility rule | Families | Members | Selected source bytes | Dictionary literal bytes before encoding | Hole slots before encoding |
|---|---:|---:|---:|---:|---:|
| paragraph, blank-line, <=16,384 bytes | 57 | 533 | 299,531 | 5,016 | 1,426 |
| newline-terminated line, <=4,096 bytes | 373 | 3,122 | 332,353 | 14,733 | 1,191 |

Paragraphs select fewer source bytes than the 4,096-byte line view. They select
only 1,627 bytes more than the previous 512-byte line rule (297,904 bytes),
while requiring far fewer families and dictionary literals. These are
eligibility measurements only; they imply no compression gain.

The targeted 4 MiB census range at `520093696` has completed encoding only.
The frozen original-byte PAQ archive is 158,796 bytes (payload 158,732), while
the paragraph representation is 166,476 bytes (payload 166,412): an encoded
gap of +7,680 bytes before either pending independent decode can qualify the
comparison. The paragraph transform selected 74 families, 6,737 members and
2,852,634 source bytes, so this target is not an opportunity-absent case. Its
own descriptor is 2,447,184 bytes, dictionary 26,317, rules 120, framing 10,
literal payload 1,341,670 and raw hole payload 961,795 bytes before PAQ. These
figures come from the immutable encoder logs under
[`runs/units-b2c44e27547dae66f8a879f7`](runs/units-b2c44e27547dae66f8a879f7)
and
[`runs/units-fbe31e95ef72db0bc181a57b`](runs/units-fbe31e95ef72db0bc181a57b).

The existing unit codec only recognizes exact LINK, URL and NUMBER lexical
holes, stores every hole raw with its length, and rearranges literals,
descriptors and holes before PAQ. Therefore the current deficit cannot be
attributed to a lack of selected paragraphs. It is consistent with paid frame
overhead and PAQ losing useful byte-neighbour context after the split. The
numbers above do not isolate those causes.

Existing successful numerical work is narrower. The MyISAM experiment used
canonical fixed-record fields and transmitted its dictionaries and occupancy
counts; the grid work also found that representation/backend interaction was
the main contribution. Neither result transfers a numerical grammar to
free-form Wikipedia paragraphs.

## Recommended bounded ablation

Test **causal same-slot decimal deltas**, only inside already selected
paragraph families. This is distinct from the current arrangement transform:

1. Preserve the existing family dictionary, selection thresholds, descriptor
   order, all LINK/URL holes, and all literal exceptions exactly.
2. For a `NUMBER` hole, define its causal context as
   `(family id, hole slot, lexical sign/leading-zero/decimal-point form)`.
   Only canonical base-10 integers that fit a declared signed range can enter
   the numerical subrule. Every other number remains the existing raw packed
   hole.
3. For each eligible context with at least three occurrences, transmit a
   context declaration and its first integer raw. Encode later values as
   signed zig-zag deltas from that context's previously decoded value. Keep
   the delta representation in descriptor occurrence order; do not create a
   global numeric side stream.
4. Charge the context declarations, representation flags, first values, sign
   and width exceptions, and every delta. Decoder state starts empty and is
   reconstructed only from the frame.

The matched control must be the same updated frame with an explicit
`raw-number` flag for every number. This measures typed-number syntax and
causal same-slot prediction without confusing it with the much larger
paragraph split or with a different PAQ context order.

## Promotion criteria and interpretation

Start on the existing long-paragraph synthetic fixture, then the same census
range only after its original and paragraph decodes both pass. Report complete
physical archives, exact decode hashes, rule/flag/context/first-value/delta
costs, raw-number costs, and PAQ payload. A gain only in the typed form over
its same-frame raw-number control establishes the proposed numerical mechanism.
A gain over original PAQ is a separate, stricter result. If typed deltas lose
against the same-frame raw-number control, retain the negative result and do
not attribute the current paragraph deficit to combinatorial coding.

No filename, offset, corpus hash, external dictionary, trained model, or
untransmitted parser state may select the mechanism.
