# Wikipedia body-relation opportunity profile, v2

This supersedes neither the v1 artifact nor any compression evidence.  It is a
separate observation-only profile that corrects v1's title and contributor
proxies.  The profiler read exactly the three permitted 4 MiB development
regions of canonical local `enwik9` at offsets 0, 100,000,000 and 400,000,000.
It did not read structural holdouts 600M or 900M, did not invoke PAQ, and did
not produce a compressed archive.  The final run took 1.635 seconds on logical
CPUs 16 and 18 under its 30-second budget.  `metadata_cost` is
**NOT_MEASURED**, residual-token bytes are `null`, residual-token rules are
**NOT_MEASURED**, and incremental PAQ gain is **NOT_MEASURED**.

| Relation | Body values covered | Raw source bytes covered | Observed relation | Interpretation |
| --- | ---: | ---: | --- | --- |
| Bounded repeated line families | 2,045 | 1,866,619 | 2,644 normalized skeletons with at least two distinct raw lines; 46,905 variable-family members over 1,700,235 bytes; 13,189 exact-duplicate members over 237,043 bytes | The strongest bounded body relation; exact member bytes and variable-member bytes may overlap and must not be summed |
| Bounded repeated paragraph families | 1,960 | 541,677 | 288 variable skeletons / 3,579 members / 516,919 bytes; 1,112 exact duplicate members / 36,493 bytes | A smaller, separate candidate after line framing |
| Infobox fields | 78 | 111,947 | 2,122 bounded field-line spans and 746 distinct field-name byte strings | Sparse by article but structurally dense; test as field columns after body lines |
| Wikitable markers | 323 | 16,422 | 12,052 raw table-start or row-marker spans | Marker frequency alone does not demonstrate aligned cell values |
| Numeric fields | 168 | 129,030 | 2,019 bounded field spans with decimal-like tokens | No canonical-number or predictive relationship has been measured |
| Templates | 967 | 170,129 | 4,795 bounded non-nested single-line spans | Nested/multiline templates remain outside this detector |
| Category/interlanguage links | 1,319 | 661,353 | 27,486 bounded literal link spans | Highly overlapping with other body structures |
| URL/citation layouts | 805 | 145,316 | 5,921 URL-domain or bounded `<ref>` spans; 4,095 domains | Layout and domain reuse remain untested as a codec |
| Redirects | 771 | 9,243 | 771 redirect-prefix spans | Small exact field opportunity |
| Same-page title in article text | 1,204 | 15,161 | Exact decoded title bytes occur in 934 opening bodies and 1,204 whole bodies | This is true same-page body reuse, not title-column duplication; it is not part of the first body-line codec |
| Same-record contributor ID→name/IP | page-slot scope | 23,079 | 1,673 decoded pairs, 853 repeated exact pairs, one ID with multiple observed names | Pairs use only `page/revision/contributor/id`, `username` or `ip` slot paths; their bytes are contributor slots, not article-text bytes |

The non-topology relation union covers 2,303,360 article-text source bytes.
This is a merged raw-byte interval union, so it does not add overlapping rows.
XML/wikitext topology is deliberately excluded: its detector spans all
11,766,705 decoded article-text bytes and would make the union trivial.  The
machine-readable artifact records the complete per-region overlap matrix,
definitions, hashes, detector limits, full tag-path classification, and the
separate byte scopes.

The evidence supports one immediate, minimal reversible experiment: a
two-pass, global **bounded body-line family frame**.  It should accept only
complete `<text...>` body spans and complete 48–512 byte lines.  A candidate
line skeleton may replace only bounded decimal, link and URL tokens; it must
have at least 24 literal bytes, appear at least three times across at least two
body records, and have at least two distinct raw forms.  The fixed first pass
selects the dictionary before encoding.  The frame must store that dictionary,
original order descriptors, rules, every substitution, every length and every
reference; unsupported lines, boundaries and holes remain literal.  Its decoder
must reconstruct from the frame alone without XML serialization or source
input.  The next comparison must charge every component and use the same PAQ
backend around raw and transformed physical bytes.

The profile itself makes no claim that this frame beats PAQ, that the observed
relations are independent, or that any result is Hutter-qualifying.  The
previous v1 profile remains preserved at
[`body-opportunities.md`](body-opportunities.md) and
[`body-opportunities.json`](body-opportunities.json).
