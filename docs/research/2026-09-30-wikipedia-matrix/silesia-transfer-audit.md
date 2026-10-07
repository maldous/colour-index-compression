# Portfolio 25 to Wikipedia transfer audit

## Scope

This is a code-path audit of the frozen **Portfolio 25** Silesia result, not a
Wikipedia compression result. The controlling contribution record reports
25,502,494 bytes, 3,301,285 bytes below its complete locally measured v216 -8
controls. Its separate historical comparison uses the author-reported paq8px
v215 -12L leader total of 27,825,511 bytes. The historical source revision is
`f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6`; source archive SHA-256 is
`82057df6eb217602cbb3e5b10538f00e30acedd791c88dbe9cef2f81b9e7414e`.

All twelve selected streams have recorded byte-exact restoration. That is
evidence for those frozen Silesia streams only: it is not an enwik9 result,
Hutter qualification, or a claim that any feature transfers to Wikipedia.

## Actual selections and backend boundary

| Member | Selected stream | CIX bytes | local v216 -8 control | Difference |
| --- | --- | ---: | ---: | ---: |
| dickens | native v216 -8 | 1,902,345 | 1,902,345 | 0 |
| mozilla | section constraints + v215 -8 | 5,834,880 | 6,477,226 | -642,346 |
| mr | volume `0/3/10` | 1,671,101 | 1,820,661 | -149,560 |
| nci | geometry/hydrogen slots + v215 -8 | 447,748 | 809,461 | -361,713 |
| ooffice | native v216 -8 | 1,267,529 | 1,267,529 | 0 |
| osdb | database remaining-count + v215 -8 | 1,698,992 | 2,018,086 | -319,094 |
| reymont | native v216 -8 | 746,894 | 746,894 | 0 |
| samba | native v216 -8 | 1,625,132 | 1,625,132 | 0 |
| sao | grouped corrections + v215 -8 | 2,105,875 | 3,730,635 | -1,624,760 |
| webster | native v215 -9L | 4,423,086 | 4,626,898 | -203,812 |
| x-ray | native v216 -8 | 3,531,428 | 3,531,428 | 0 |
| xml | native v216 -8 | 247,484 | 247,484 | 0 |

The v216 column is the local completed control, never the author v215 -12L
result. Six selections are native v216 -8. Mozilla, NCI, OSDB and SAO use
structural v215 -8 paths; Webster uses v215 -9L; the MR volume stream is not
treated here as a PAQ version comparison. Row differences therefore do not
establish an isolated v215/v216 or entropy-coder advantage.

## OSDB: dictionaries and remaining counts

The selected OSDB path is
`database-remaining-count-paq-v215-8`, implemented by
`benchmarks/mysql_record_constraints.py`
(SHA-256 `ce79f2845f422c03d886e57fe1a521a123bf4a8f130da8ccf6948af678e03a1b`).
`split()` recognises only a canonical MyISAM layout. Unsupported or
noncanonical records and tails remain literal. `transform()` emits flags,
literal exceptions, then nine parsed columns. `column_encode()` sends each
observed dictionary and all counts; numeric dictionaries use deltas. No hidden
dictionary, corpus bytes or generator state is required.

The winner is `mode=3`: `order_encode()` arithmetic-codes a dictionary ID
against the currently remaining counts and decrements its Fenwick tree. It is
not a rank stream. Rank is separate `mode=4`: exact multinomial rank for
`n <= 4096`, conditional Lehmer rank for all-distinct permutations, otherwise
the remaining-count arithmetic fallback. The historical full OSDB measurement
is 1,698,992 bytes for remaining-count versus 1,723,002 for dictionary IDs on
the same v215 -8 backend. That is source-specific record evidence, not an
established Wikipedia field result.

A field dictionary requires decoder-available boundaries and a demonstrated
relation. A weak count signal does not qualify. This source has no generic wiki
markup/template/prose parser or generic cross-field learner. Its historical
OSDB note measured only 0.070--0.074 estimated pairwise mutual information in
the examined columns and explicitly rejected inventing a joint constraint.

The present Wikipedia D2 column experiment is deliberately more limited still:
`hutter_wikipedia_columns.column_frame()` applies remaining-count/rank order
coding only to fixed 1,024-value blocks of eligible **non-article-text** D2
columns. Article bodies remain outside that order codec. Consequently its count
model is metadata/structured-field coding before PAQ, not body-text
remaining-count coding. A read-only block-exact scan of the three exposed
4 MiB development regions found 194/10,899 eligible blocks/values at offset 0,
170/8,153 at offset 100,000,000, and 114/21,553 at offset 400,000,000. No
globally-over-256 palette became eligible merely by block splitting in these
three regions. This corrects the possible ambiguity of whole-column palette
screening without making any compression claim.

## SAO: grouping, raw correction IDs, then PAQ

The selected SAO path is `grouped-prediction-paq-v215-8`:
`benchmarks/grid_conditional_corrections.py`
(SHA-256 `59f0d271834198809a204a3bb6a8b50f1449e4f417a2371faf2341f079910465`)
through `benchmarks/grid_conditional_paq_probe.py`
(SHA-256 `81f72f68e34f0186f579a46100d5ee2c0da12c88f05d355490a08528da403871`).
`qualified_prediction_paq.qualify()` requires
`(context, coding, offset) == (3, 0, 0)`.

Those selected values are narrower than “conditional combinatorial coding.”
`groups(q, 3)` groups by the exact, already decoded quantized coordinate
`q`. `encode_corrections(..., coding=0)` writes palette IDs raw inside each
group. It does not transmit conditional compositions or use a type-class rank.
Codings 1 and 2 are unselected controls which call `grid.type_frame`.
The recorded full controls found paid counts/ranks did not beat raw grouped
corrections. The winning result demonstrates decoder-reconstructible numeric
grouping plus v215 PAQ, not that ranks beat PAQ for identical predictions.

## Prioritised bounded Wikipedia hypotheses

1. **Repeated body-long paragraph skeletons.** Use only reversible,
   stream-defined boundaries and a previously decoded skeleton. Encode unchanged
   runs, substitution positions/lengths, and literal or dictionary substitutions.
   Compare literal bodies, copy-plus-literal substitutions, dictionary IDs,
   remaining-count IDs and rank IDs. This is not implemented by the MyISAM path.
2. **Numeric joint corrections.** Only after a decoder-reconstructible baseline
   and grouping state is defined, test raw IDs, remaining-count arithmetic and
   ranks with the identical palette, counts, partitions and termination bytes.
   SAO makes exact-coordinate/coding-0 a control, not a reason to assume rank
   wins.
3. **Field dictionaries after a strong relation audit.** Require repeated values,
   stable reversible boundaries and a metadata-cost gate. Compare literal,
   static-ID and remaining-count-ID forms. Reject weak counts, unconstrained
   prose and speculative relations.

## Explicitly absent

Portfolio 25 contains no general Wikipedia parser, generic paragraph
skeleton/substitution representation, generic markup schema learner, generic
Wikipedia numeric-correction codec, whole-Wikipedia/enwik9 qualification, or
measurement that a CIX residual representation beats PAQ given the same text
predictions. The proposed bounded cells are new controlled experiments, not
already-qualified Portfolio 25 features.

## Primary source paths

- `docs/research/2026-09-29-portfolio25-contributions.json`
- `docs/research/2026-09-29-competitive-section-v25-milestone.json`
- `docs/research/2026-09-29-portfolio25-source-bundle.json`
- `benchmarks/mysql_record_constraints.py`: `split`, `column_encode`,
  `order_encode`, `order_decode`, `transform`, `inverse`, `encode`
- `benchmarks/grid_conditional_corrections.py`: `groups`,
  `encode_corrections`, `decode_corrections`, `transform`, `inverse`
