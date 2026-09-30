# Wikipedia body-relation opportunity profile

This is an observation-only map for the next Hutter-specific representation
experiment.  It is not a compression result, an entropy estimate, or a PAQ
comparison.  No archive was produced and `metadata_cost` and
`incremental_paq_gain` are both **NOT_MEASURED**.

The profiler read exactly three fixed, disjoint 4 MiB development regions of
the canonical local `enwik9` byte stream: offsets 0, 100,000,000 and
400,000,000.  It did not read either structural holdout (600M or 900M), did
not invoke PAQ, and retained the original bytes as opaque byte strings.  It
ran in 1.584 seconds with affinity to logical CPUs 16 and 18; its declared
wall-clock budget was 30 seconds.

| Offset | SHA-256 | Complete pages / article-text values | D2 page skeletons / slots |
| ---: | --- | ---: | ---: |
| 0 | `5ba647fec2ba51b0383cbe7147e15a478d85613245b7131c41764dbdd5062f77` | 506 / 506 | 12 / 271 |
| 100,000,000 | `fd30602741222df957545a821556c8428bb8c3e4ed45634367ae8470d901c6ec` | 377 / 377 | 9 / 203 |
| 400,000,000 | `a07035d4de761fc30cee70f4528156e8128abf7430222cfd63c2311168ea7f17` | 1,190 / 1,190 | 9 / 201 |

The following totals span the three regions.  Coverage is the number of
article-text field occurrences that the bounded detector encountered; it is
not a saving and categories overlap.  `Distinct` is meaningful only where the
detector collects byte values or normalized forms.

| Opportunity | Coverage | Occurrences | Distinct | What was observed | Candidate reversible representation |
| --- | ---: | ---: | ---: | --- | --- |
| Repeated normalized lines | 2,073 | 57,224 in repeated families | 50,273 forms; 3,965 repeated families | Lines at most 512 bytes, normalizing only bounded links, URLs and decimal tokens | Exact line-skeleton dictionary, substitution payloads and raw escapes |
| Repeated normalized paragraphs | 2,072 | 4,357 in repeated families | 19,347 forms; 437 repeated families | Paragraphs at most 1,024 bytes with the same bounded substitutions | Paragraph skeleton references with explicit boundaries and escapes |
| Infobox fields | 78 | 2,044 | 746 field-name bytes | `{{Infobox` prefix plus bounded newline `|key=value` lines | Field-name/layout columns; literal fallback for unknown or nested forms |
| Wikitable markers | 323 | 323 | — | Raw lines beginning `{|` or `|-` | Validated row/cell columns, otherwise literal |
| Numeric fields | 168 | 2,019 | 746 field-name bytes | Bounded fields containing a decimal-like token | Canonical-number validation then causal delta/error payload with spelling escapes |
| Templates | 967 | 4,795 | — | Single-line non-nested `{{...}}` spans only | Terminal/field layout with raw nested or multiline escapes |
| Category/interlanguage links | 1,319 | 27,486 | — | Literal bounded `[[Category:...]]` and language-prefix links | Prefix/terminal stream plus full raw link escapes |
| URL/citation layouts | 805 | 5,921 | 4,095 domains | HTTP(S) domain bytes and bounded `<ref>` spans | Domain/layout columns plus raw URL/citation payloads |
| Redirects | 771 | 771 | — | Case-insensitive `#REDIRECT [[` line prefix | Redirect target field with literal fallback |
| XML/wikitext topology | 2,073 | 2,073 | 30 skeleton layouts | D2's exact page skeleton and field-slot observations | Condition field coding on the paid skeleton/slot descriptor |
| Title reuse | page-column scope | 0 repeats | — | D2 short title columns | No evidence for reuse in these regions |
| Contributor pairs | page-column scope | 2,073 paired positions | — | First title/contributor positions within a skeleton | Test only against the same raw columns and explicit exceptions |

The union of the body-detector categories covers all 2,073 extracted
article-text occurrences because bounded line detection is intentionally broad.
It must not be added to the rows above: for example, category/interlanguage
and URL/citation detections overlap heavily, and templates, tables and infobox
fields commonly occur in the same body.  Title reuse and contributor pairs
have a page-column universe, so they are excluded from that union.  The raw
per-region overlap matrix and detector definitions are in
[`body-opportunities.json`](body-opportunities.json).

The first concrete missing mechanism should be a **bounded exact body-line
family frame**.  It would scan an article-text value causally, admit only lines
whose syntax can be split exactly into a normalized skeleton plus ordered raw
link/URL/number substitutions, and put every other line in a literal stream.
The frame must carry the skeleton dictionary, member order, every substitution,
line boundary and selection decision.  This directly tests the 3,965 repeated
bounded forms seen on development data while preserving every original byte.
It is deliberately separate from D2's XML page/value columns and from a static
XML token dictionary.  A matched PAQ experiment may be promoted only after the
frame has an independent decoder, exact SHA-256 round trip, and physical
accounting for all those components.  The infobox/table field-column mechanism
is the next bounded candidate; its lower coverage but much denser field layout
is a distinct mechanism, not an inferred gain from this profile.

The detector definitions, proposed mechanisms, input hashes, topology counts,
per-region results and all overlap counts are machine-readable in
[`body-opportunities.json`](body-opportunities.json).  The profile deliberately
does not parse or reserialize XML/wikitext, recognize known pages, use external
dictionaries, or claim any Hutter score or improvement.
